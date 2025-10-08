from django.urls import path
from . import views
from .views import (
    api_test_page,
    ai_model_list_api,
    predict_from_frame_api
)

app_name = 'ai_processing'

urlpatterns = [
    # API endpoint để lấy danh sách model
    path('models/', ai_model_list_api, name='list_models'),
    
    # API endpoint để nhận frame ảnh từ OHIF và dự đoán
    path('predict-frame/', predict_from_frame_api, name='predict_frame'),

    # URL cho trang test (nếu bạn vẫn cần)
    path('test/', api_test_page, name='api_test_page'),
    path("ai/save-review/", views.save_review, name="save_review"),
]