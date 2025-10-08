import base64
import uuid
import os
from django.conf import settings
from django.shortcuts import render

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes

from . import services
from .serializers import AIReportSerializer, AIModelSerializer, ReviewSessionSerializer
from .models import AIModel, AIReport, ReviewSession
from apps.uploads.models import DICOMStudy


# --- API CHO OHIF ---
class PredictFromFrameAPIView(APIView):
    parser_classes = [JSONParser]

    def post(self, request, *args, **kwargs):
        data = request.data
        image_data_uri = data.get('imageData')
        study_instance_uid = data.get('studyInstanceUID')
        model_id = data.get('modelId')

        if not all([image_data_uri, study_instance_uid, model_id]):
            return Response(
                {"error": "Thiếu imageData, studyInstanceUID hoặc modelId."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            header, encoded = image_data_uri.split(",", 1)
            image_bytes = base64.b64decode(encoded)

            service_result = services.run_prediction_from_file_bytes(model_id, image_bytes)
            prediction_result = service_result["prediction_result"]
            heatmap_base64_uri = service_result["heatmap_url"]

            study = DICOMStudy.objects.get(study_instance_uid=study_instance_uid)
            ai_model = AIModel.objects.get(model_id=model_id)

            _, heatmap_encoded = heatmap_base64_uri.split(",", 1)
            heatmap_data = base64.b64decode(heatmap_encoded)

            heatmap_filename = f"heatmaps/{study.study_id}/{uuid.uuid4()}.png"
            heatmap_path = os.path.join(settings.MEDIA_ROOT, heatmap_filename)

            os.makedirs(os.path.dirname(heatmap_path), exist_ok=True)
            with open(heatmap_path, "wb") as f:
                f.write(heatmap_data)

            report = AIReport.objects.create(
                study=study,
                model=ai_model,
                prediction_result=prediction_result,
                heatmap_image_path=heatmap_filename,
            )

            serializer = AIReportSerializer(report, context={"request": request})
            response_data = serializer.data
            response_data.update({
                "bbox": service_result.get("bbox"),
                "image_width": service_result.get("image_width"),
                "image_height": service_result.get("image_height"),
                "heatmap_url": heatmap_base64_uri,
            })

            return Response(response_data, status=status.HTTP_200_OK)

        except DICOMStudy.DoesNotExist:
            return Response(
                {"error": f"Không tìm thấy Study với UID: {study_instance_uid}"},
                status=status.HTTP_404_NOT_FOUND,
            )
        except AIModel.DoesNotExist:
            return Response(
                {"error": f"Không tìm thấy Model với ID: {model_id}"},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            import traceback; traceback.print_exc()
            return Response(
                {"error": "Lỗi server khi xử lý ảnh.", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


predict_from_frame_api = PredictFromFrameAPIView.as_view()


# --- API LẤY DANH SÁCH MODEL ---
class AIModelListView(APIView):
    def get(self, request, *args, **kwargs):
        models = AIModel.objects.all().order_by("model_name")
        serializer = AIModelSerializer(models, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


ai_model_list_api = AIModelListView.as_view()


# --- API TEST UPLOAD FILE ---
class RunPredictionFromFileAPIView(APIView):
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request, *args, **kwargs):
        model_id = request.data.get("modelId")
        image_file = request.FILES.get("imageFile")

        if not model_id or not image_file:
            return Response(
                {"error": "Thiếu modelId hoặc imageFile."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            image_bytes = image_file.read()
            service_result = services.run_prediction_from_file_bytes(model_id, image_bytes)

            return Response(service_result, status=status.HTTP_200_OK)

        except Exception as e:
            import traceback; traceback.print_exc()
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


run_prediction_from_file_api = RunPredictionFromFileAPIView.as_view()

@api_view(["POST"])
# @permission_classes([IsAuthenticated])  # Tạm thời comment để test
def save_review(request):
    """
    Lưu đánh giá của chuyên gia cho một AIReport.
    Yêu cầu: report_id, reviewer_status, reviewer_comments?, annotated_regions?
    """
    data = request.data.copy()
    
    # Nếu có user đăng nhập thì lưu, không thì để null
    if request.user.is_authenticated:
        data["user"] = request.user.id
    else:
        data["user"] = None

    serializer = ReviewSessionSerializer(data=data)
    if serializer.is_valid():
        review = serializer.save()
        return Response(ReviewSessionSerializer(review).data, status=201)
    return Response(serializer.errors, status=400)

def api_test_page(request):
    all_models = AIModel.objects.all()
    context = {"models": all_models}
    return render(request, "ai_processing/api_test.html", context)