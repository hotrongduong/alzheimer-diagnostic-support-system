import cv2
import numpy as np
import tensorflow as tf
from tensorflow.keras.models import Model
from tensorflow.keras.layers import Input, GlobalAveragePooling2D, Dropout, Dense
from tensorflow.keras.applications import ResNet50
import pydicom
from io import BytesIO
import requests
import os
from django.conf import settings
import uuid
import base64
from matplotlib import cm
from scipy.interpolate import griddata

from .models import AIModel, AIReport
from apps.uploads.models import DICOMInstance

# --- Cấu hình Model ---
IMG_SIZE = 224
CLASS_NAMES = [ "Mild_Dementia", "Moderate_Dementia", "Non_Dementia", "Very_mild_Dementia" ]
_model_cache = {}

# --- Các hàm tiền xử lý ---
def crop_brain_region(image, margin=10):
    if len(image.shape) == 3 and image.shape[2] == 3:
      gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
      gray = image
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours: return image
    largest_contour = max(contours, key=cv2.contourArea)
    x, y, w, h = cv2.boundingRect(largest_contour)
    x, y = max(x - margin, 0), max(y - margin, 0)
    x2, y2 = min(x + w + margin * 2, image.shape[1]), min(y + h + margin * 2, image.shape[0])
    return image[y:y2, x:x2]

def resize_and_pad(image, target_size=224):
    h, w = image.shape[:2]
    scale = target_size / max(h, w)
    new_w, new_h = int(w * scale), int(h * scale)
    resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)
    delta_w, delta_h = target_size - new_w, target_size - new_h
    top, bottom = delta_h // 2, delta_h - (delta_h // 2)
    left, right = delta_w // 2, delta_w - (delta_w // 2)
    return cv2.copyMakeBorder(resized, top, bottom, left, right, cv2.BORDER_CONSTANT, value=[0, 0, 0])

def preprocess_dcm_frame(pixel_array_2d):
    image_2d_normalized = cv2.normalize(pixel_array_2d, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)
    image_bgr = cv2.cvtColor(image_2d_normalized, cv2.COLOR_GRAY2BGR)
    cropped = crop_brain_region(image_bgr, margin=10)
    if cropped is None: raise ValueError("Không thể crop vùng não từ ảnh DICOM.")
    processed_image = resize_and_pad(cropped, target_size=IMG_SIZE)
    img_array_expanded = np.expand_dims(processed_image, axis=0)
    return img_array_expanded, processed_image

def preprocess_generic_image(image_bgr):
    cropped = crop_brain_region(image_bgr, margin=10)
    if cropped is None: raise ValueError("Không thể crop vùng não từ ảnh.")
    processed_image = resize_and_pad(cropped, target_size=IMG_SIZE)
    img_array_expanded = np.expand_dims(processed_image, axis=0)
    return img_array_expanded, processed_image
    
def create_advanced_brain_mask(image_array):
    if image_array.ndim > 2:
        gray = cv2.cvtColor(image_array, cv2.COLOR_BGR2GRAY)
    else:
        gray = image_array.astype(np.uint8)

    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5,5))
    closed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel, iterations=3)

    contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        mask = np.zeros_like(gray)
        center = (int(IMG_SIZE/2), int(IMG_SIZE/2))
        axes = (int(IMG_SIZE*0.4), int(IMG_SIZE*0.45))
        return cv2.ellipse(mask, center, axes, 0, 0, 360, 255, -1)
    
    largest_contour = max(contours, key=cv2.contourArea)
    hull = cv2.convexHull(largest_contour)
    mask = np.zeros_like(gray)
    cv2.drawContours(mask, [hull], -1, 255, thickness=cv2.FILLED)
    return mask

# --- Các hàm AI ---
def get_model_and_grad_model(ai_model_obj: AIModel):
    model_key = str(ai_model_obj.model_id)
    if model_key in _model_cache: return _model_cache[model_key]['main'], _model_cache[model_key]['grad']
    
    inputs = Input(shape=(IMG_SIZE, IMG_SIZE, 3))
    preprocessed_input = tf.keras.applications.resnet50.preprocess_input(inputs)
    base_model = ResNet50(include_top=False, weights=None, input_tensor=preprocessed_input)
    x = base_model.output
    x = GlobalAveragePooling2D(name="avg_pool")(x)
    x = Dropout(0.5)(x)
    x = Dense(512, activation='relu', name='dense_hidden')(x)
    outputs = Dense(len(CLASS_NAMES), activation='softmax', name='dense_output')(x)
    model = Model(inputs=inputs, outputs=outputs)
    
    weights_path = f"/{ai_model_obj.model_path}"
    model.load_weights(weights_path)
    
    grad_model = Model([model.inputs], [model.get_layer('conv5_block3_out').output, model.output])
    _model_cache[model_key] = {'main': model, 'grad': grad_model}
    return model, grad_model

def get_grad_cam_plus_plus(grad_model, img_array, class_index):
    with tf.GradientTape() as tape:
        conv_outputs, predictions = grad_model(img_array)
        loss = predictions[:, class_index]
    grads = tape.gradient(loss, conv_outputs)
    guided_grads = (tf.cast(conv_outputs > 0, "float32") * tf.cast(grads > 0, "float32") * grads)
    weights = tf.reduce_mean(guided_grads, axis=(0, 1, 2))
    cam = np.dot(conv_outputs[0], weights)
    cam = np.maximum(cam, 0)
    
    h, w = cam.shape
    points = np.array([(i, j) for i in range(h) for j in range(w)])
    values = cam.flatten()
    grid_x, grid_y = np.mgrid[0:h-1:IMG_SIZE*1j, 0:w-1:IMG_SIZE*1j]
    
    smooth_heatmap = griddata(points, values, (grid_x, grid_y), method='cubic', fill_value=0)
    smooth_heatmap = np.maximum(smooth_heatmap, 0)
    heatmap = (smooth_heatmap - np.min(smooth_heatmap)) / (np.max(smooth_heatmap) - np.min(smooth_heatmap) + 1e-10)
    return heatmap

# --- Hàm điều phối chính ---
def run_prediction_from_file_bytes(model_id, image_bytes):
    ai_model_obj = AIModel.objects.get(model_id=model_id)
    try:
        ds = pydicom.dcmread(BytesIO(image_bytes))
        pixel_array = ds.pixel_array
        image_2d = pixel_array[0] if len(pixel_array.shape) > 2 else pixel_array
        preprocessed_img_batch, original_processed_img = preprocess_dcm_frame(image_2d)
    except pydicom.errors.InvalidDicomError:
        image_np = np.frombuffer(image_bytes, np.uint8)
        image_bgr = cv2.imdecode(image_np, cv2.IMREAD_COLOR)
        preprocessed_img_batch, original_processed_img = preprocess_generic_image(image_bgr)

    model, grad_model = get_model_and_grad_model(ai_model_obj)
    prediction = model.predict(preprocessed_img_batch)[0]
    pred_index = np.argmax(prediction)
    
    # === LOGIC HEATMAP HOÀN CHỈNH TỐI ƯU ===
    brain_mask = create_advanced_brain_mask(original_processed_img)
    grad_cam_heatmap = get_grad_cam_plus_plus(grad_model, preprocessed_img_batch, pred_index)
    
    # Chỉ giữ lại heatmap bên trong vùng não
    heatmap_on_brain = grad_cam_heatmap * (brain_mask / 255.0)

    # Tô màu cho heatmap đã được lọc
    # <<< SỬA LỖI: Đổi từ 'jet_r' (đảo ngược) thành 'jet' (tiêu chuẩn) >>>
    jet_colormap = cm.get_cmap('jet') 
    heatmap_colored_rgb = np.uint8(jet_colormap(heatmap_on_brain)[..., :3] * 255)
    heatmap_colored_bgr = cv2.cvtColor(heatmap_colored_rgb, cv2.COLOR_RGB2BGR)

    # Trộn ảnh chính xác bằng mặt nạ
    final_image = original_processed_img.copy()
    # Chỉ áp dụng heatmap lên vùng não (những pixel có giá trị > 0 trong mask)
    final_image[brain_mask > 0] = cv2.addWeighted(
        original_processed_img[brain_mask > 0], 0.5,
        heatmap_colored_bgr[brain_mask > 0], 0.5, 0
    )
    # =======================================================
    
    _, img_encoded = cv2.imencode('.png', final_image)
    heatmap_base64 = base64.b64encode(img_encoded).decode('utf-8')
    prediction_result = {
        "class_index": int(pred_index), "class_name": CLASS_NAMES[pred_index], "confidence": float(prediction[pred_index]),
        "all_probabilities": {name: float(prob) for name, prob in zip(CLASS_NAMES, prediction)}
    }
    return prediction_result, f"data:image/png;base64,{heatmap_base64}"