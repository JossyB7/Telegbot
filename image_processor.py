import io
import os
import logging
import numpy as np
import cv2
from PIL import Image, ImageEnhance, UnidentifiedImageError
from psd_tools import PSDImage
from rembg import remove, new_session

logger = logging.getLogger(__name__)

def get_rembg_session():
    try:
        logger.info("Loading rembg session/model...")
        return new_session("u2netp")
    except Exception as e:
        logger.error(f"Failed to load rembg model: {e}")
        raise RuntimeError("Background removal model could not be loaded.")

# Load once for performance.
session = get_rembg_session()

def process_image_with_psd(user_image_path, psd_template_path, output_path, placeholder_name="USER_PHOTO"):
    if not os.path.exists(psd_template_path):
        raise FileNotFoundError(f"PSD template not found at: {psd_template_path}")
    if session is None:
        raise RuntimeError("Background removal (rembg session) not initialized.")

    try:
        logger.info(f"Processing {user_image_path} with template {psd_template_path}...")

        psd = PSDImage.open(psd_template_path)

        # --- 1. BACKGROUND REMOVAL ---
        try:
            with open(user_image_path, "rb") as i:
                input_data = i.read()
            user_no_bg_bytes = remove(input_data, session=session)
            user_no_bg = Image.open(io.BytesIO(user_no_bg_bytes)).convert("RGBA")
        except UnidentifiedImageError:
            logger.error("Uploaded file not recognized as an image.")
            raise ValueError("Provided file is not a valid image.")
        except Exception as e:
            logger.error(f"Background removal failed: {e}")
            raise ValueError("Failed to remove background from image.")

        # --- 2. COLOR ENHANCEMENT ---
        try:
            user_no_bg = ImageEnhance.Color(user_no_bg).enhance(1.4)
            user_no_bg = ImageEnhance.Contrast(user_no_bg).enhance(1.1)
        except Exception as e:
            logger.warning(f"Saturation/contrast step failed: {e}")

        # --- 3. LOCATE PLACEHOLDER ON PSD ---
        placeholder = None
        for l in psd.descendants():
            # Defensive: allow partial match or case-insensitive if needed
            if l.name and l.name.strip().lower() == placeholder_name.strip().lower():
                placeholder = l
                break

        if not placeholder:
            logger.error(f"No layer named '{placeholder_name}' in PSD.")
            raise ValueError(f"Layer named '{placeholder_name}' not found in template PSD.")

        left, top, right, bottom = placeholder.bbox
        target_w, target_h = right - left, bottom - top

        # --- 4. FACE-CENTERED AUTO-ZOOM ---
        face_center_x_ratio, face_center_y_ratio = 0.5, 0.4
        face_detected = False
        try:
            cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
            img_rgb = np.array(user_no_bg.convert("RGB"))
            img_gray = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2GRAY)

            face_cascade = cv2.CascadeClassifier(cascade_path)
            faces = face_cascade.detectMultiScale(img_gray, 1.1, 5)
            if len(faces) > 0:
                fx, fy, fw, fh = max(faces, key=lambda f: f[2]*f[3])
                face_center_x_ratio = (fx + fw/2) / user_no_bg.width
                face_center_y_ratio = (fy + fh/2) / user_no_bg.height
                face_detected = True
                logger.info("Face detected for centering")
        except Exception as e:
            logger.info("Face detection skipped or errored: %s", e)

        # --- 5. SCALE & POSITION USER IMAGE FOR PLACEHOLDER LAYER ---
        if face_detected:
            src_w, src_h = user_no_bg.width, user_no_bg.height
            scale = max(target_w / src_w, target_h / src_h)
            scaled_w = int(src_w * scale)
            scaled_h = int(src_h * scale)
            user_scaled = user_no_bg.resize((scaled_w, scaled_h), Image.LANCZOS)

            face_px_x = face_center_x_ratio * scaled_w
            face_px_y = face_center_y_ratio * scaled_h
            crop_x = max(0, min(int(face_px_x - target_w/2), scaled_w - target_w))
            crop_y = max(0, min(int(face_px_y - target_h/2), scaled_h - target_h))

            user_resized = user_scaled.crop((crop_x, crop_y, crop_x + target_w, crop_y + target_h))
            paste_x = left
            paste_y = top
        else:
            aspect = user_no_bg.width / user_no_bg.height
            new_w = target_w
            new_h = int(new_w / aspect)
            if new_h > target_h:
                new_h = target_h
                new_w = int(aspect * new_h)
            user_resized = user_no_bg.resize((new_w, new_h), Image.LANCZOS)
            paste_x = left + (target_w - new_w) // 2
            paste_y = top + (target_h - new_h) // 2

        # --- 6. FINAL COMPOSITING ---
        final_canvas = Image.new("RGBA", psd.size, (0, 0, 0, 0))
        for layer in psd:
            if not layer.is_visible():
                continue
            if layer.name and layer.name.strip().lower() == placeholder_name.strip().lower():
                final_canvas.alpha_composite(user_resized, (paste_x, paste_y))
            try:
                layer_img = layer.composite().convert("RGBA")
                final_canvas.alpha_composite(layer_img, layer.offset)
            except Exception as e:
                logger.warning(f"Skipping PSD layer {layer.name}: {e}")

        final_canvas.convert("RGB").save(output_path, "JPEG", quality=95, optimize=True)
        logger.info(f"Saved composited image to {output_path}")
        return output_path
    except Exception as e:
        logger.error(f"Image processing error: {e}")
        raise