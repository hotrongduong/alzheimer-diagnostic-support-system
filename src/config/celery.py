import os
from celery import Celery

# Đặt biến môi trường mặc định cho settings của Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Tạo một instance của Celery app
app = Celery('config')

# Tải cấu hình từ file settings.py của Django
# namespace='CELERY' nghĩa là tất cả các cấu hình Celery phải có tiền tố 'CELERY_'
app.config_from_object('django.conf:settings', namespace='CELERY')

# Tự động tìm tất cả các file tasks.py trong các app đã đăng ký
app.autodiscover_tasks()