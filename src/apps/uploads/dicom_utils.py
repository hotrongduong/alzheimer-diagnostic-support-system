import pydicom
from pydicom.dataset import Dataset, FileMetaDataset
from pydicom.uid import generate_uid
from PIL import Image
import numpy as np
import datetime
from io import BytesIO

def create_dicom_from_image(image_bytes, patient, study_uid, series_uid, instance_number=1):
    """
    Chuyển đổi một file ảnh thường (JPG, PNG) từ bytes trong bộ nhớ thành một file DICOM hợp lệ.
    """
    try:
        # 1. Đọc ảnh từ bytes và chuyển thành mảng numpy
        img = Image.open(BytesIO(image_bytes)).convert('L') # Chuyển sang ảnh grayscale 8-bit
        pixel_array = np.array(img, dtype=np.uint8)

        # 2. Tạo metadata cho file DICOM (File Meta Information)
        file_meta = FileMetaDataset()
        file_meta.MediaStorageSOPClassUID = '1.2.840.10008.5.1.4.1.1.7'
        file_meta.MediaStorageSOPInstanceUID = generate_uid()
        file_meta.ImplementationClassUID = generate_uid()
        file_meta.TransferSyntaxUID = pydicom.uid.ExplicitVRLittleEndian 

        # 3. Tạo dataset chính và điền các thẻ DICOM bắt buộc
        ds = Dataset()
        ds.file_meta = file_meta
        
        ds.SOPClassUID = file_meta.MediaStorageSOPClassUID
        ds.SOPInstanceUID = file_meta.MediaStorageSOPInstanceUID
        ds.PatientName = str(patient.full_name)
        ds.PatientID = str(patient.patient_id)
        ds.PatientBirthDate = patient.date_of_birth.strftime('%Y%m%d')
        ds.PatientSex = 'O'

        ds.StudyInstanceUID = study_uid
        ds.StudyDate = datetime.datetime.now().strftime('%Y%m%d')
        ds.StudyTime = datetime.datetime.now().strftime('%H%M%S')
        ds.AccessionNumber = ''
        ds.StudyID = "1"
        ds.StudyDescription = "Image converted from JPG/PNG"

        ds.SeriesInstanceUID = series_uid
        ds.Modality = 'OT'
        ds.SeriesNumber = "1"
        ds.SeriesDate = ds.StudyDate
        ds.SeriesTime = ds.StudyTime

        ds.InstanceNumber = str(instance_number)
        ds.ContentDate = ds.StudyDate
        ds.ContentTime = ds.StudyTime

        ds.PhotometricInterpretation = "MONOCHROME2"
        ds.SamplesPerPixel = 1
        ds.BitsAllocated = 8
        ds.BitsStored = 8
        ds.HighBit = 7
        ds.PixelRepresentation = 0
        ds.Rows, ds.Columns = pixel_array.shape

        ds.PixelData = pixel_array.tobytes()

        ds.is_little_endian = True
        ds.is_implicit_VR = False

        ds.fix_meta_info(enforce_standard=True)
        
        mem_file = BytesIO()
        pydicom.dcmwrite(mem_file, ds, write_like_original=False)
        mem_file.seek(0)
        
        return mem_file.getvalue()

    except Exception as e:
        print(f"Lỗi khi tạo file DICOM từ ảnh trong bộ nhớ: {e}")
        raise