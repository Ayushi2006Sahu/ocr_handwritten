import streamlit as st
from PIL import Image, ImageDraw
import pandas as pd
from io import BytesIO
import torch

from transformers import (
    TrOCRProcessor,
    VisionEncoderDecoderModel
)

# -----------------------------
# PAGE CONFIG
# -----------------------------

st.set_page_config(
    page_title="Employee Form OCR",
    page_icon="✍️",
    layout="centered"
)

st.title("✍️ Employee Form OCR")
st.write("Upload Employee Information Sheet")

# -----------------------------
# LOAD MODEL
# -----------------------------

@st.cache_resource
def load_models():

    processor = TrOCRProcessor.from_pretrained(
        "microsoft/trocr-base-handwritten"
    )

    model = VisionEncoderDecoderModel.from_pretrained(
        "microsoft/trocr-base-handwritten"
    )

    model.eval()

    return processor, model


processor, model = load_models()

# -----------------------------
# FIELD COORDINATES
# -----------------------------

FIELDS = {

    "Full Name":
        (290, 180, 1080, 280),

    "Phone Number":
        (290, 280, 1080, 380),

    "Address":
        (290, 380, 1080, 480),

    "City, State, Zip":
        (290, 480, 1080, 580),

    "Email":
        (290, 580, 1080, 680),

    "Date of Birth":
        (290, 720, 1080, 820),

    "SSN":
        (290, 820, 1080, 920),

    "Marital Status":
        (290, 920, 1080, 1020),

    "Bank Name":
        (290, 1080, 1080, 1180),

    "Account Type":
        (290, 1180, 1080, 1280),

    "Routing Number":
        (290, 1280, 1080, 1380),

    "Account Number":
        (290, 1340, 1080, 1430)
}

# -----------------------------
# DEBUG BOXES
# -----------------------------

def show_boxes(image):

    img = image.copy()

    draw = ImageDraw.Draw(img)

    for box in FIELDS.values():

        draw.rectangle(
            box,
            outline="red",
            width=3
        )

    st.image(
        img,
        caption="Detected Fields"
    )

# -----------------------------
# PREPROCESS
# -----------------------------

def preprocess(crop):

    crop = crop.convert("L")

    crop = crop.resize(
        (
            crop.width * 2,
            crop.height * 2
        )
    )

    return crop

# -----------------------------
# OCR
# -----------------------------

def recognize_text(crop_img):

    pixel_values = processor(
        images=crop_img,
        return_tensors="pt"
    ).pixel_values

    with torch.no_grad():

        generated_ids = model.generate(
            pixel_values,
            max_new_tokens=100
        )

    text = processor.batch_decode(
        generated_ids,
        skip_special_tokens=True
    )[0]

    return text.strip()

# -----------------------------
# FIELD EXTRACTION
# -----------------------------

def extract_fields(image):

    data = {}

    for field, box in FIELDS.items():

        crop = image.crop(box)

        crop = preprocess(crop)

        text = recognize_text(crop)

        data[field] = text

    return data

# -----------------------------
# EXCEL EXPORT
# -----------------------------

def to_excel(data):

    df = pd.DataFrame([data])

    output = BytesIO()

    with pd.ExcelWriter(
        output,
        engine="openpyxl"
    ) as writer:

        df.to_excel(
            writer,
            index=False
        )

    return output.getvalue()

# -----------------------------
# UI
# -----------------------------

uploaded_file = st.file_uploader(
    "Upload Form",
    type=["jpg", "jpeg", "png"]
)

if uploaded_file is not None:

    image = Image.open(
        uploaded_file
    ).convert("RGB")

    st.image(
        image,
        caption="Uploaded Form",
        use_container_width=True
    )

    st.write(
        f"Image Size: {image.size}"
    )

    if st.checkbox("Show Field Boxes"):
        show_boxes(image)

    if st.button(
        "Extract Data",
        type="primary"
    ):

        with st.spinner(
            "Reading handwritten fields..."
        ):

            data = extract_fields(image)

            excel_file = to_excel(data)

        st.success(
            "Extraction Complete!"
        )

        st.subheader(
            "Extracted Data"
        )

        st.json(data)

        st.download_button(
            label="⬇ Download Excel",
            data=excel_file,
            file_name="employee_data.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

st.markdown("---")
st.caption(
    "Fixed Template OCR using TrOCR"
)
