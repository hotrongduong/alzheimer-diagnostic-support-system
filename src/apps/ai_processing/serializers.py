from rest_framework import serializers
from .models import AIReport, AIModel, ReviewSession
from django.conf import settings # Thêm import settings

class AIModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIModel
        fields = [
            'model_id',
            'model_name',
            'model_version',
            'description'
        ]

class AIReportSerializer(serializers.ModelSerializer):
    heatmap_url = serializers.SerializerMethodField()

    class Meta:
        model = AIReport
        fields = [
            'report_id', 
            'prediction_result', 
            'heatmap_url'
        ]

    def get_heatmap_url(self, obj):
        request = self.context.get('request')
        if request and obj.heatmap_image_path:
            # --- SỬA LỖI Ở ĐÂY ---
            # Xây dựng URL đầy đủ bằng cách kết hợp MEDIA_URL
            # Kết quả sẽ là: http://localhost:8000/media/heatmaps/...
            return request.build_absolute_uri(f"{settings.MEDIA_URL}{obj.heatmap_image_path}")
        return None
    
class ReviewSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReviewSession
        fields = [
            "review_session_id",
            "report",
            "user",
            "reviewer_status",
            "reviewer_comments",
            "annotated_regions",
            "reviewed_at",
        ]
        read_only_fields = ["review_session_id", "user", "reviewed_at"]