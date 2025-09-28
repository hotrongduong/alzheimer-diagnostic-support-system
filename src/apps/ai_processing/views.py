from django.shortcuts import render

# Create your views here.
from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from . import services
from .serializers import AIReportSerializer, AIModelSerializer
from .models import AIModel
from apps.uploads.models import DICOMInstance

class AIModelListView(APIView):
    def get(self, request, *args, **kwargs):
        models = AIModel.objects.all().order_by('model_name')
        serializer = AIModelSerializer(models, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
ai_model_list_api = AIModelListView.as_view()

# --- API cho OHIF (dùng trong tương lai) ---
class RunPredictionAPIView(APIView):
    def post(self, request, *args, **kwargs):
        data = request.data
        study_uid = data.get('studyInstanceUID')
        series_uid = data.get('seriesInstanceUID')
        instance_uid = data.get('sopInstanceUID')
        frame_number = data.get('frameNumber', 0)
        model_id = data.get('modelId')

        if not all([study_uid, series_uid, instance_uid, model_id]):
            return Response({"error": "Thiếu thông tin studyUID, seriesUID, instanceUID hoặc modelId."}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            AIModel.objects.get(model_id=model_id)
            DICOMInstance.objects.get(instance_uid=instance_uid)
        except (AIModel.DoesNotExist, DICOMInstance.DoesNotExist) as e:
            return Response({"error": f"Không tìm thấy đối tượng trong database: {e}"}, status=status.HTTP_404_NOT_FOUND)

        try:
            report = services.run_prediction(study_uid, series_uid, instance_uid, frame_number, model_id)
            serializer = AIReportSerializer(report, context={'request': request})
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        except Exception as e:
            print(f"LỖI NGHIÊM TRỌNG KHI CHẠY AI PREDICTION: {e}")
            import traceback
            traceback.print_exc()
            return Response({"error": "Đã có lỗi xảy ra ở server khi xử lý AI.", "details": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

run_prediction_api = RunPredictionAPIView.as_view()

# --- API CHO TRANG TEST ---
class RunPredictionFromFileAPIView(APIView):
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request, *args, **kwargs):
        model_id = request.data.get('modelId')
        image_file = request.FILES.get('imageFile')

        if not model_id or not image_file:
            return Response({"error": "Thiếu modelId hoặc imageFile."}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            image_bytes = image_file.read()
            prediction, heatmap_base64 = services.run_prediction_from_file_bytes(model_id, image_bytes)
            
            return Response({
                "prediction": prediction,
                "heatmap_image_base64": heatmap_base64
            }, status=status.HTTP_200_OK)

        except Exception as e:
            print(f"LỖI KHI CHẠY TEST PREDICTION: {e}")
            import traceback
            traceback.print_exc()
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

run_prediction_from_file_api = RunPredictionFromFileAPIView.as_view()


# --- VIEW CHO TRANG TEST ---
def api_test_page(request):
    """Lấy danh sách model và render trang test."""
    all_models = AIModel.objects.all()
    context = {
        'models': all_models
    }
    return render(request, 'ai_processing/api_test.html', context)