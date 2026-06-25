import os
import json
import re
import torch
import pandas as pd
import streamlit as st
from PIL import Image
from transformers import DonutProcessor, VisionEncoderDecoderModel
from io import BytesIO

st.set_page_config(page_title="Advance Offline Form Extractor", page_icon="📝", layout="wide")

LOCAL_MODEL_DIR = "./my_local_donut_model"

@st.cache_resource
def load_offline_model():
    if not os.path.exists(LOCAL_MODEL_DIR):
        with st.spinner("Downloading Model... Please keep internet ON."):
            processor = DonutProcessor.from_pretrained("naver-clova-ix/donut-base-finetuned-docvqa")
            model = VisionEncoderDecoderModel.from_pretrained("naver-clova-ix/donut-base-finetuned-docvqa")
            os.makedirs(LOCAL_MODEL_DIR, exist_ok=True)
            processor.save_pretrained(LOCAL_MODEL_DIR)
            model.save_pretrained(LOCAL_MODEL_DIR)
            st.success("Model downloaded successfully!")
            
    processor = DonutProcessor.from_pretrained(LOCAL_MODEL_DIR)
    model = VisionEncoderDecoderModel.from_pretrained(LOCAL_MODEL_DIR)
    return processor, model

# ==========================================
# 🛠️ CORRECTED EXTRACTION LOGIC
# ==========================================
def extract_all_fields(image, processor, model, device, prompts_dict):
    extracted_row = {}
    
   
    pixel_values = processor(image, return_tensors="pt").pixel_values.to(device)
    
    for field_name, question in prompts_dict.items():
        prompt = f"<s_docvqa><question>{question}</question>"
        decoder_input_ids = processor.tokenizer(prompt, add_special_tokens=False, return_tensors="pt").input_ids.to(device)
        
        with torch.no_grad():
            outputs = model.generate(
                pixel_values, 
                decoder_input_ids=decoder_input_ids, 
                max_length=128,
                pad_token_id=processor.tokenizer.pad_token_id,
                eos_token_id=processor.tokenizer.eos_token_id,
            )
        
        # 💡 FIX: batch_decode से पहली स्ट्रिंग (index 0) को निकालें
        decoded_output = processor.batch_decode(outputs)[0]
        
        # 💡 FIX: Tags को साफ करने का मजबूत तरीका
        if "<s_answer>" in decoded_output:
            val = decoded_output.split("<s_answer>")[-1].split("</s_answer>")[0].strip()
        else:
            # अगर विशेष टोकन न मिले तो सारे HTML/XML टैग्स हटा दें
            val = re.sub(r"<.*?>", "", decoded_output).strip()
            # प्रॉम्ट के सवाल को आउटपुट से साफ करें
            val = val.replace(question, "").strip()
            
        # फालतू बचे हुए स्पेशल कैरेक्टर्स साफ करें
        val = val.replace("<s>", "").replace("</s>", "").strip()
        
        # फाइनल वैल्यू को स्टोर करें
        extracted_row[field_name] = val.upper() if val else "NOT FOUND"
        
    return extracted_row

def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Form Data')
    processed_data = output.getvalue()
    return processed_data

# ==========================================
# UI DESIGN
# ==========================================
st.title("📝 Advance Form Data Extractor (Fixed Code)")

device = "cuda" if torch.cuda.is_available() else "cpu"
processor, model = load_offline_model()
model.to(device)

ALL_QUESTIONS = {
    "Trade": "what is the trade?",
    "Candidate Name": "what is the candidate name?",
    "Father Name": "what is the father name?",
    "Date of Birth": "what is the date of birth?"
}

col1, col2 = st.columns(2)

with col1:
    uploaded_file = st.file_uploader("Choose a Form Image...", type=["jpg", "jpeg", "png"])
    if uploaded_file is not None:
        image = Image.open(uploaded_file).convert("RGB")
        st.image(image, caption="Uploaded Form Image", use_container_width=True)

with col2:
    if uploaded_file is not None:
        st.subheader("📋 Extraction Process")
        
        if st.button("🚀 Run Full Form Extraction", type="primary"):
            status_text = st.empty()
            status_text.text("Extracting data from form fields...")
            
            # डिक्शनरी डेटा जनरेट करें
            extracted_data = extract_all_fields(image, processor, model, device, ALL_QUESTIONS)
            
            status_text.empty()
            st.success("Extraction Completed! 🎉")
            
            # 💡 FIX: एक्सेल और यूआई टेबल के लिए सही फॉर्मेटिंग
            # सीधे डिक्शनरी को DataFrame में बदलें ताकि की-वैल्यू सही से आएं
            df_display = pd.DataFrame(list(extracted_data.items()), columns=["Field", "Extracted Value"])
            
            st.subheader("📊 Extracted Data Table")
            st.dataframe(df_display, use_container_width=True)
            
            # एक्सेल के लिए डेटा रो फॉर्मेट में रखें (Horizontal Row)
            df_excel = pd.DataFrame([extracted_data])
            excel_data = to_excel(df_excel)
            
            st.download_button(
                label="📥 Download Full Data as Excel",
                data=excel_data,
                file_name="Full_Form_Data.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
