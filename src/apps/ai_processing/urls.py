from django.urls import path
from .views import (
    run_prediction_api, 
    api_test_page, 
    run_prediction_from_file_api,
    ai_model_list_api # <-- Thêm import
)

app_name = 'ai_processing'

urlpatterns = [
    # URL cho OHIF
    path('predict/', run_prediction_api, name='run_prediction'),
    # URL cho trang test
    path('test/', api_test_page, name='api_test_page'),
    path('predict-file/', run_prediction_from_file_api, name='run_prediction_from_file'),
    # URL mới để lấy danh sách model
    path('models/', ai_model_list_api, name='list_models'),
]