import streamlit as st
from PIL import Image
import numpy as np
import torch
import easyocr
from transformers import TrOCRProcessor, VisionEncoderDecoderModel

st.set_page_config(page_title="Handwritten OCR", page_icon="✍️", layout="centered")
st.title("✍️ Handwritten Text OCR (Hybrid)")
st.markdown("Image upload karo aur handwritten text extract ho jayega!")

@st.cache_resource
def load_models():
    with st.spinner("🔄 Models load ho rahe hain..."):
        # EasyOCR: sirf line detection ke liye
        reader = easyocr.Reader(['en'], gpu=False)
        # TrOCR: actual text recognition ke liye
        processor = TrOCRProcessor.from_pretrained("microsoft/trocr-base-handwritten")
        model = VisionEncoderDecoderModel.from_pretrained("microsoft/trocr-base-handwritten")
        model.eval()
    return reader, processor, model

reader, processor, model = load_models()


def recognize_line(crop_img):
    """TrOCR se ek line ka text nikalo"""
    pixel_values = processor(images=crop_img, return_tensors="pt").pixel_values
    with torch.no_grad():
        ids = model.generate(pixel_values, max_new_tokens=150)
    return processor.batch_decode(ids, skip_special_tokens=True)[0].strip()


def run_ocr(image: Image.Image) -> str:
    rgb = image.convert("RGB")
    img_array = np.array(rgb)

    # Step 1: EasyOCR se WORD-level detections lo (paragraph=False)
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
        text = recognize_line(crop)
        if text:
            results.append(text)

    return "\n".join(results)


uploaded_file = st.file_uploader("📁 Image upload karo (JPG / PNG)", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    image = Image.open(uploaded_file).convert("RGB")
    st.image(image, caption="Uploaded Image", width="stretch")

    if st.button("🔍 Text Extract Karo", type="primary"):
        with st.spinner("⏳ Reading line by line..."):
            extracted_text = run_ocr(image)

        st.success("✅ Done!")
        st.text_area("Extracted Output", value=extracted_text, height=250, label_visibility="collapsed")
        st.download_button("⬇️ Download .txt", data=extracted_text, file_name="output.txt", mime="text/plain")

st.markdown("---")
st.caption("EasyOCR (line detection) + TrOCR (handwriting recognition) ✅")