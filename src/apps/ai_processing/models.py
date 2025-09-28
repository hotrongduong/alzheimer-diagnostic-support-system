import uuid
from django.db import models
from django.conf import settings
from apps.uploads.models import DICOMStudy

class AIModel(models.Model):
    model_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    model_name = models.CharField(max_length=255, unique=True, help_text="Tên định danh cho mô hình")
    model_version = models.CharField(max_length=50, help_text="Phiên bản hiện tại của mô hình")
    description = models.TextField(blank=True, help_text="Mô tả chi tiết về mô hình")
    model_path = models.CharField(max_length=1024, help_text="Đường dẫn tương đối đến file trọng số")
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.model_name} (v{self.model_version})"
    
class AIReport(models.Model):
    report_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    study = models.ForeignKey(DICOMStudy, on_delete=models.CASCADE, related_name="ai_reports")
    model = models.ForeignKey(AIModel, on_delete=models.PROTECT, related_name="reports")
    prediction_result = models.JSONField(help_text="Kết quả dự đoán chi tiết dưới dạng JSON")
    heatmap_image_path = models.CharField(max_length=1024, help_text="Đường dẫn tới heatmap đã tạo")
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Baó cáo kết quả dự đoán bằng AI cho {self.study} bởi {self.model.model_name}"
    
class ReviewSession(models.Model):
    class Status(models.TextChoices):
        CORRECT = "CORRECT", "Chính xác"
        INCORRECT = "INCORRECT", "Không chính xác"
        IRRELEVANT = "IRRELEVANT", "Không liên quan"
    
    review_session_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    report = models.ForeignKey(AIReport, on_delete=models.CASCADE, related_name="reviews")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, help_text="Chuyên gia thực hiện đánh giá")
    reviewer_status = models.CharField(max_length=20, choices=Status.choices, help_text="Đánh giá của chuyên gia")
    reviewer_comments = models.TextField(blank=True, help_text="Nhận xét chi tiết")
    annotated_regions = models.JSONField(null=True, blank=True, help_text="Vùng quan trọng được chuyên gia đánh dấu")
    reviewed_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Đánh giá của {self.user} cho {self.report.report_id}"