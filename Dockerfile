# Sử dụng một image Python chính thức, gọn nhẹ
FROM python:3.12-slim-bullseye

# Tắt việc tạo file .pyc và bật chế độ unbuffered để log hiển thị ngay lập tức
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Tạo và đặt thư mục làm việc bên trong container
WORKDIR /app

# Sao chép file requirements.txt vào trước để tận dụng Docker cache
COPY requirements.txt /app/

# Cài đặt các thư viện
RUN pip install --no-cache-dir -r requirements.txt

# Sao chép toàn bộ mã nguồn trong thư mục 'src' vào thư mục làm việc '/app'
COPY ./src /app/
COPY ./models /app/models/

# BƯỚC 1: Tạo group và user trước
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser

# BƯỚC 2: Chuyển sang user mới tạo
USER appuser