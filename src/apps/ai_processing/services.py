import cv2
import numpy as np
import tensorflow as tf
from tensorflow.keras.models import Model
from tensorflow.keras.layers import Input, GlobalAveragePooling2D, Dropout, Dense
from tensorflow.keras.applications import ResNet50
import pydicom
from io import BytesIO
import base64
from matplotlib import cm
from scipy.interpolate import griddata
import logging

from .models import AIModel

# --- Logger ---
logger = logging.getLogger(__name__)

# --- Config ---
IMG_SIZE = 224
CLASS_NAMES = ["Mild_Dementia", "Moderate_Dementia", "Non_Dementia", "Very_mild_Dementia"]
_model_cache = {}


def crop_brain_region_with_bbox(image, margin=10):
    """Trả về (cropped_image, bbox) với bbox = (x, y, w, h)."""
    if len(image.shape) == 3 and image.shape[2] == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        h, w = image.shape[:2]
        return image, (0, 0, w, h)
    largest_contour = max(contours, key=cv2.contourArea)
    x, y, w, h = cv2.boundingRect(largest_contour)
    x0, y0 = max(x - margin, 0), max(y - margin, 0)
    x2, y2 = min(x + w + margin * 2, image.shape[1]), min(y + h + margin * 2, image.shape[0])
    cropped = image[y0:y2, x0:x2]
    return cropped, (x0, y0, x2 - x0, y2 - y0)


def resize_and_pad_with_info(image, target_size=IMG_SIZE):
    """Resize giữ tỷ lệ và pad về target_size."""
    h, w = image.shape[:2]
    scale = target_size / max(h, w)
    new_w, new_h = int(round(w * scale)), int(round(h * scale))
    resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)
    delta_w, delta_h = target_size - new_w, target_size - new_h
    left = delta_w // 2
    top = delta_h // 2
    right = delta_w - left
    bottom = delta_h - top
    padded = cv2.copyMakeBorder(resized, top, bottom, left, right, cv2.BORDER_CONSTANT, value=[0, 0, 0])
    info = {"scale": scale, "left": left, "top": top, "new_w": new_w, "new_h": new_h}
    return padded, info


def preprocess_dcm_frame(pixel_array_2d):
    """Trả về batch, processed_img, original_bgr, bbox, resize_info."""
    image_2d_normalized = cv2.normalize(pixel_array_2d, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)
    image_bgr = cv2.cvtColor(image_2d_normalized, cv2.COLOR_GRAY2BGR)
    cropped, bbox = crop_brain_region_with_bbox(image_bgr, margin=10)
    if cropped is None:
        raise ValueError("Không thể crop vùng não từ ảnh DICOM.")
    processed_image, resize_info = resize_and_pad_with_info(cropped, target_size=IMG_SIZE)
    img_array_expanded = np.expand_dims(processed_image, axis=0)
    return img_array_expanded, processed_image, image_bgr, bbox, resize_info


def preprocess_generic_image(image_bgr):
    """Tương tự cho ảnh upload thường."""
    cropped, bbox = crop_brain_region_with_bbox(image_bgr, margin=10)
    if cropped is None:
        raise ValueError("Không thể crop vùng não từ ảnh.")
    processed_image, resize_info = resize_and_pad_with_info(cropped, target_size=IMG_SIZE)
    img_array_expanded = np.expand_dims(processed_image, axis=0)
    return img_array_expanded, processed_image, image_bgr, bbox, resize_info


def create_advanced_brain_mask_full(image_array):
    """Mask não ở kích thước gốc."""
    if image_array.ndim > 2:
        gray = cv2.cvtColor(image_array, cv2.COLOR_BGR2GRAY)
    else:
        gray = image_array.astype(np.uint8)
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    closed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel, iterations=3)
    contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        mask = np.zeros_like(gray)
        h, w = gray.shape[:2]
        center = (int(w / 2), int(h / 2))
        axes = (int(w * 0.4), int(h * 0.45))
        return cv2.ellipse(mask, center, axes, 0, 0, 360, 255, -1)
    largest_contour = max(contours, key=cv2.contourArea)
    hull = cv2.convexHull(largest_contour)
    mask = np.zeros_like(gray)
    cv2.drawContours(mask, [hull], -1, 255, thickness=cv2.FILLED)
    return mask


def get_model_and_grad_model(ai_model_obj: AIModel):
    model_key = str(ai_model_obj.model_id)
    if model_key in _model_cache:
        return _model_cache[model_key]["main"], _model_cache[model_key]["grad"]

    inputs = Input(shape=(IMG_SIZE, IMG_SIZE, 3))
    preprocessed_input = tf.keras.applications.resnet50.preprocess_input(inputs)
    base_model = ResNet50(include_top=False, weights=None, input_tensor=preprocessed_input)
    x = base_model.output
    x = GlobalAveragePooling2D(name="avg_pool")(x)
    x = Dropout(0.5)(x)
    x = Dense(512, activation="relu", name="dense_hidden")(x)
    outputs = Dense(len(CLASS_NAMES), activation="softmax", name="dense_output")(x)
    model = Model(inputs=inputs, outputs=outputs)

    weights_path = f"/{ai_model_obj.model_path}"
    model.load_weights(weights_path)

    grad_model = Model([model.inputs], [model.get_layer("conv5_block3_out").output, model.output])
    _model_cache[model_key] = {"main": model, "grad": grad_model}
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
    grid_x, grid_y = np.mgrid[0:h - 1:IMG_SIZE * 1j, 0:w - 1:IMG_SIZE * 1j]

    smooth_heatmap = griddata(points, values, (grid_x, grid_y), method="cubic", fill_value=0)
    smooth_heatmap = np.maximum(smooth_heatmap, 0)
    heatmap = (smooth_heatmap - np.min(smooth_heatmap)) / (np.max(smooth_heatmap) - np.min(smooth_heatmap) + 1e-10)
    return heatmap


def run_prediction_from_file_bytes(model_id, image_bytes):
    ai_model_obj = AIModel.objects.get(model_id=model_id)

    try:
        ds = pydicom.dcmread(BytesIO(image_bytes))
        pixel_array = ds.pixel_array
        image_2d = pixel_array[0] if len(pixel_array.shape) > 2 else pixel_array
        preprocessed_img_batch, _, original_bgr, bbox, _ = preprocess_dcm_frame(image_2d)
    except pydicom.errors.InvalidDicomError:
        image_np = np.frombuffer(image_bytes, np.uint8)
        image_bgr = cv2.imdecode(image_np, cv2.IMREAD_COLOR)
        preprocessed_img_batch, _, original_bgr, bbox, _ = preprocess_generic_image(image_bgr)

    model, grad_model = get_model_and_grad_model(ai_model_obj)
    prediction = model.predict(preprocessed_img_batch)[0]
    pred_index = int(np.argmax(prediction))

    rows, cols = original_bgr.shape[:2]
    x, y, w_bbox, h_bbox = bbox

    logger.info(f"[AI DEBUG] Original size: {cols}x{rows}")
    logger.info(f"[AI DEBUG] BBox: {bbox}")
    logger.info(f"[AI DEBUG] GradCAM input: {preprocessed_img_batch.shape}")

    brain_mask_full = create_advanced_brain_mask_full(original_bgr)

    grad_cam_heatmap = get_grad_cam_plus_plus(grad_model, preprocessed_img_batch, pred_index)

    # Resize heatmap trực tiếp về bbox
    if w_bbox <= 0 or h_bbox <= 0:
        w_bbox, h_bbox = cols, rows
        x, y = 0, 0
    resized_heatmap = cv2.resize(grad_cam_heatmap, (w_bbox, h_bbox), interpolation=cv2.INTER_CUBIC)

    heatmap_full = np.zeros((rows, cols), dtype=np.float32)
    x2, y2 = min(x + w_bbox, cols), min(y + h_bbox, rows)
    heatmap_full[y:y2, x:x2] = resized_heatmap[:y2 - y, :x2 - x]

    logger.info(f"[AI DEBUG] Heatmap resized to bbox: {w_bbox}x{h_bbox}")
    logger.info(f"[AI DEBUG] Heatmap pasted at: ({x},{y}) → ({x2},{y2}) on {cols}x{rows}")

    heatmap_on_brain = heatmap_full * (brain_mask_full / 255.0)

    jet_colormap = cm.get_cmap("jet_r")
    heatmap_colored_rgba = np.uint8(jet_colormap(heatmap_on_brain) * 255)
    heatmap_colored_rgba[brain_mask_full == 0, 3] = 0

    _, img_encoded = cv2.imencode(".png", heatmap_colored_rgba)
    heatmap_base64 = base64.b64encode(img_encoded).decode("utf-8")

    prediction_result = {
        "class_index": pred_index,
        "class_name": CLASS_NAMES[pred_index],
        "confidence": float(prediction[pred_index]),
        "all_probabilities": {name: float(prob) for name, prob in zip(CLASS_NAMES, prediction)},
        "bbox": [int(x), int(y), int(w_bbox), int(h_bbox)],
    }

    return {
        "prediction_result": prediction_result,
        "heatmap_url": f"data:image/png;base64,{heatmap_base64}",
        "bbox": [int(x), int(y), int(w_bbox), int(h_bbox)],
        "image_width": cols,
        "image_height": rows,
    }
