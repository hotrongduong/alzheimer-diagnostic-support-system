import uuid
from django.db import models
from django.conf import settings

class Patient(models.Model):
    patient_id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="UUID duy nhất cho mỗi bệnh nhân",
    )
    full_name = models.CharField(max_length=255, help_text="Họ và tên bệnh nhân")
    date_of_birth = models.DateField(help_text="Ngày sinh của bệnh nhân")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.full_name} ({str(self.patient_id).split('-')[0]})"

    class Meta:
        verbose_name = "Bệnh nhân"
        verbose_name_plural = "Quản lý Bệnh nhân"

class FileUpload(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Đang chờ"
        PROCESSING = "PROCESSING", "Đang xử lý"
        COMPLETED = "COMPLETED", "Hoàn thành"
        FAILED = "FAILED", "Thất bại"

    upload_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="uploads",
        help_text="Người dùng đã tải file lên",
    )
    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name="files",
        help_text="File này thuộc về bệnh nhân nào",
    )
    original_filename = models.CharField(max_length=255, help_text="Tên file gốc")
    file_format = models.CharField(
        max_length=50, help_text="Định dạng file gốc (ví dụ: jpg, png, dcm)"
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )

    def __str__(self):
        return f"File: {self.original_filename} ({self.get_status_display()})"

    class Meta:
        verbose_name = "Tệp tải lên"
        verbose_name_plural = "Quản lý Tệp tải lên"

class DICOMStudy(models.Model):
    study_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name="studies",
        help_text="Nghiên cứu này của bệnh nhân nào",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="studies",
        help_text="Người dùng thực hiện ca chụp",
    )
    study_description = models.TextField(
        blank=True, help_text="Mô tả về ca chụp/nghiên cứu"
    )
    study_date = models.DateField()
    study_time = models.TimeField()
    orthanc_study_id = models.CharField(
        max_length=255, unique=True, help_text="ID của Study trên server Orthanc"
    )
    study_instance_uid = models.CharField(
        max_length=255, unique=True, help_text="Study Instance UID của ca chụp (dùng cho OHIF)", null=True
    )
    session_id = models.UUIDField(unique=True, help_text="ID của phiên upload để theo dõi", null=True)

    def __str__(self):
        return f"Study cho {self.patient.full_name} vào ngày {self.study_date}"

    class Meta:
        verbose_name = "Nghiên cứu DICOM"
        verbose_name_plural = "Quản lý Nghiên cứu DICOM"
        
class DICOMInstance(models.Model):
    """Lưu lại SOPInstanceUID của mỗi file DICOM đã được xử lý thành công."""
    
    instance_uid = models.CharField(
        primary_key=True,
        max_length=255, 
        help_text="SOP Instance UID (0008,0018) duy nhất của ảnh"
    )
    study = models.ForeignKey(
        DICOMStudy,
        on_delete=models.CASCADE,
        related_name="instances",
        help_text="Ảnh này thuộc về ca chụp nào"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.instance_uid