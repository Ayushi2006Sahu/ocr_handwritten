"""
OCR Engine - Core logic (UI-independent)
==========================================
Ye file sirf OCR ka kaam karti hai - koi Streamlit/Flask/HTML ka code nahi.
Future mein Flask/FastAPI app mein ye file as-is import ho jaayegi.

Usage:
    from ocr_engine import load_models, run_ocr
    reader, processor, model = load_models()
    text = run_ocr(image, reader, processor, model)
"""

import numpy as np
import torch
import easyocr
from transformers import TrOCRProcessor, VisionEncoderDecoderModel


def load_models():
    """
    Models ko load karta hai (ek baar call karna hai, cache ho jaata hai).
    Returns: (easyocr_reader, trocr_processor, trocr_model)
    """
    # EasyOCR: sirf line detection ke liye
    reader = easyocr.Reader(['en'], gpu=False)

    # TrOCR: actual handwriting recognition ke liye
    processor = TrOCRProcessor.from_pretrained("microsoft/trocr-base-handwritten")
    model = VisionEncoderDecoderModel.from_pretrained("microsoft/trocr-base-handwritten")
    model.eval()

    return reader, processor, model


def recognize_line(crop_img, processor, model):
    """TrOCR se ek cropped line image ka text nikalo"""
    pixel_values = processor(images=crop_img, return_tensors="pt").pixel_values
    with torch.no_grad():
        ids = model.generate(pixel_values, max_new_tokens=150)
    return processor.batch_decode(ids, skip_special_tokens=True)[0].strip()


def run_ocr(image, reader, processor, model):
    """
    Main function: image leta hai, extracted text return karta hai.

    Args:
        image: PIL.Image object
        reader: EasyOCR reader (from load_models)
        processor: TrOCR processor (from load_models)
        model: TrOCR model (from load_models)

    Returns:
        str: extracted text (multi-line)
    """
    rgb = image.convert("RGB")
    img_array = np.array(rgb)

    # Step 1: EasyOCR se WORD-level detections lo
    detections = reader.readtext(img_array, detail=1, paragraph=False)

    if not detections:
        return ""

    # Step 2: Har word ka center-Y aur bounding box nikalo
    words = []
    for (bbox, _, _) in detections:
        xs = [p[0] for p in bbox]
        ys = [p[1] for p in bbox]
        left, right = min(xs), max(xs)
        top, bottom = min(ys), max(ys)
        cy = (top + bottom) / 2
        height = bottom - top
        words.append({"left": left, "right": right, "top": top, "bottom": bottom, "cy": cy, "h": height})

    # Step 3: Y-center ke hisaab se sort karo, phir lines mein group karo
    words.sort(key=lambda w: w["cy"])

    avg_height = sum(w["h"] for w in words) / len(words)
    line_threshold = avg_height * 0.6  # Kitna Y-diff allowed same line ke liye

    lines = []
    current_line = [words[0]]
    for w in words[1:]:
        if abs(w["cy"] - current_line[-1]["cy"]) <= line_threshold:
            current_line.append(w)
        else:
            lines.append(current_line)
            current_line = [w]
    lines.append(current_line)

    # Step 4: Har line ke andar words ko LEFT-to-RIGHT (x-axis) sort karo,
    # aur poori line ka combined bounding box banao
    results = []
    pad = 5
    for line in lines:
        line.sort(key=lambda w: w["left"])
        left = max(0, int(min(w["left"] for w in line)) - pad)
        right = min(rgb.width, int(max(w["right"] for w in line)) + pad)
        top = max(0, int(min(w["top"] for w in line)) - pad)
        bottom = min(rgb.height, int(max(w["bottom"] for w in line)) + pad)

        crop = rgb.crop((left, top, right, bottom))

        # Step 5: TrOCR se is line ka text nikalo
        text = recognize_line(crop, processor, model)
        if text:
            results.append(text)

    return "\n".join(results)