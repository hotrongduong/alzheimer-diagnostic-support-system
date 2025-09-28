# src/apps/uploads/views.py

from django.shortcuts import render
from django.http import JsonResponse
from django.core.exceptions import ValidationError
from .models import Patient, FileUpload, DICOMStudy, DICOMInstance
import uuid
from .tasks import process_upload_session
import pydicom
from io import BytesIO

def upload_page(request):
    if request.method == 'POST':
        session_id = uuid.uuid4()
        try:
            patient_type = request.POST.get('patient_type')
            files = request.FILES.getlist('files')
            patient = None

            if not files:
                return JsonResponse({
                    'status': 'error', 
                    'message': "Vui lòng chọn ít nhất một file hoặc folder để tải lên."
                }, status=400)

            for f in files:
                f.seek(0)
                try:
                    ds = pydicom.dcmread(BytesIO(f.read()), stop_before_pixels=True)
                    sop_instance_uid = ds.SOPInstanceUID
                    if DICOMInstance.objects.filter(instance_uid=sop_instance_uid).exists():
                        raise ValidationError(f"Ảnh DICOM '{f.name}' đã tồn tại trong hệ thống.")
                except pydicom.errors.InvalidDicomError:
                    pass
                finally:
                    f.seek(0)

            first_file = files[0]
            first_file.seek(0)
            try:
                ds = pydicom.dcmread(BytesIO(first_file.read()), stop_before_pixels=True)
                existing_study_uid = ds.StudyInstanceUID
                existing_study = DICOMStudy.objects.filter(study_instance_uid=existing_study_uid).first()
                if existing_study:
                    patient = existing_study.patient
                    print(f"Phát hiện file thuộc về ca bệnh đã có của bệnh nhân: {patient.full_name}. Sử dụng bệnh nhân gốc.")
            except (pydicom.errors.InvalidDicomError, AttributeError):
                pass
            
            first_file.seek(0)
            
            if patient is None:
                if patient_type == 'existing':
                    patient_uuid_str = request.POST.get('patient_uuid')
                    if not patient_uuid_str:
                        raise ValueError("Vui lòng nhập UUID của bệnh nhân tái khám.")
                    try:
                        patient_uuid = uuid.UUID(patient_uuid_str, version=4)
                        patient = Patient.objects.get(patient_id=patient_uuid)
                    except (ValueError, Patient.DoesNotExist):
                        raise ValueError(f"Không tìm thấy bệnh nhân với UUID: {patient_uuid_str}")
                elif patient_type == 'new':
                    full_name = request.POST.get('full_name')
                    date_of_birth = request.POST.get('date_of_birth')
                    if not full_name or not date_of_birth:
                        raise ValueError("Vui lòng nhập đầy đủ họ tên và ngày sinh cho bệnh nhân mới.")
                    patient = Patient.objects.create(full_name=full_name, date_of_birth=date_of_birth)
                else:
                    raise ValueError("Vui lòng chọn loại bệnh nhân (mới hoặc tái khám).")

            if patient:
                uploads_data = []
                for f in files:
                    f.seek(0)
                    file_content = f.read()
                    file_upload_obj = FileUpload.objects.create(
                        user=request.user if request.user.is_authenticated else None,
                        patient=patient,
                        original_filename=f.name,
                        file_format=f.name.split('.')[-1] if '.' in f.name else 'unknown',
                        status=FileUpload.Status.PENDING
                    )
                    uploads_data.append({
                        'upload_id': file_upload_obj.upload_id,
                        'content': file_content,
                        'original_filename': f.name, # <-- SỬA LỖI: THÊM LẠI DÒNG NÀY
                    })
                
                if uploads_data:
                    process_upload_session.delay(str(patient.patient_id), uploads_data, str(session_id))

                return JsonResponse({'status': 'processing', 'session_id': session_id})
        
        except (ValueError, ValidationError) as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

    return render(request, 'uploads/upload.html')


def check_study_status(request, session_id):
    try:
        study = DICOMStudy.objects.get(session_id=session_id)
        if study.study_instance_uid:
            return JsonResponse({'status': 'COMPLETED', 'study_instance_uid': study.study_instance_uid})
        else:
             return JsonResponse({'status': 'PROCESSING'})
    except DICOMStudy.DoesNotExist:
        return JsonResponse({'status': 'PENDING'})