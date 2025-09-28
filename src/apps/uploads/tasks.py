# src/apps/uploads/tasks.py

from celery import shared_task
from .models import FileUpload, DICOMStudy, Patient, DICOMInstance
import pydicom
import requests
from .dicom_utils import create_dicom_from_image
import datetime
from pydicom.uid import generate_uid
from io import BytesIO
import time

@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def process_upload_session(self, patient_id, uploads_data, session_id):
    if not uploads_data:
        return

    try:
        patient = Patient.objects.get(patient_id=patient_id)
        auth = ('mapdr', 'changestrongpassword')
        
        first_upload_content = uploads_data[0]['content']
        try:
            study_uid = pydicom.dcmread(BytesIO(first_upload_content), stop_before_pixels=True).StudyInstanceUID
        except pydicom.errors.InvalidDicomError:
            study_uid = generate_uid()

        print(f"Bắt đầu xử lý {len(uploads_data)} file cho Study UID: {study_uid}")

        orthanc_study_id = None
        study_obj = None
        series_uid = generate_uid()

        for i, data in enumerate(uploads_data):
            upload_obj = FileUpload.objects.get(upload_id=data['upload_id'])
            upload_obj.status = FileUpload.Status.PROCESSING # Sửa lỗi: FileUpload.Status (S viết hoa)
            upload_obj.save()

            dicom_content, dicom_dataset = None, None
            try:
                dicom_dataset = pydicom.dcmread(BytesIO(data['content']))
                dicom_content = data['content']
            except pydicom.errors.InvalidDicomError:
                dicom_content = create_dicom_from_image(data['content'], patient, study_uid, series_uid, i + 1)
                dicom_dataset = pydicom.dcmread(BytesIO(dicom_content), stop_before_pixels=True)

            response = requests.post('http://pacs:8042/instances', data=dicom_content, headers={'Content-Type': 'application/dicom'}, auth=auth)
            
            if response.status_code != 200:
                raise Exception(f"Lỗi Orthanc cho file {data['original_filename']}: {response.text}")

            if i == 0:
                orthanc_study_id = response.json().get('ParentStudy')
                if not orthanc_study_id:
                    raise Exception("Không nhận được Orthanc Study ID từ Orthanc.")
                
                study_obj, _ = DICOMStudy.objects.update_or_create(
                    study_instance_uid=study_uid,
                    defaults={
                        'patient': patient,
                        'user': upload_obj.user,
                        'orthanc_study_id': orthanc_study_id,
                        'study_description': dicom_dataset.get('StudyDescription', 'N/A'),
                        'study_date': datetime.datetime.strptime(dicom_dataset.get('StudyDate', '19000101'), '%Y%m%d').date(),
                        'study_time': datetime.datetime.strptime(dicom_dataset.get('StudyTime', '000000').split('.')[0], '%H%M%S').time(),
                    }
                )

            DICOMInstance.objects.get_or_create(
                instance_uid=dicom_dataset.SOPInstanceUID,
                defaults={'study': study_obj}
            )
            
            # SỬA LỖI: SỬ DỤNG FileUpload.Status (S viết hoa)
            upload_obj.status = FileUpload.Status.COMPLETED
            upload_obj.save()

        if study_obj:
            study_obj.session_id = session_id
            study_obj.save()
            
            for _ in range(10):
                if requests.get(f"http://pacs:8042/studies/{orthanc_study_id}", auth=auth).status_code == 200:
                    print(f"Orthanc đã xác nhận study {orthanc_study_id} sẵn sàng.")
                    return
                time.sleep(0.5)
            print(f"CẢNH BÁO: Orthanc không xác nhận study {orthanc_study_id} kịp thời nhưng tác vụ vẫn hoàn thành.")
        
    except Exception as exc:
        print(f"Xử lý phiên upload thất bại: {exc}")
        upload_ids = [data['upload_id'] for data in uploads_data]
        # SỬA LỖI: SỬ DỤNG FileUpload.Status (S viết hoa)
        FileUpload.objects.filter(upload_id__in=upload_ids).update(status=FileUpload.Status.FAILED)
        self.retry(exc=exc)