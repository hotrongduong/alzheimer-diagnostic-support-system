from rest_framework import serializers
from .models import AIReport, AIModel

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
    # Tạo một trường mới để trả về URL đầy đủ của heatmap
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
            return request.build_absolute_uri(obj.heatmap_image_path)
        return None