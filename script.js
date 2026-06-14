// ============================================================
// Khaata — Handwritten OCR (frontend logic)
// ============================================================

const fileInput = document.getElementById("file-input");
const chooseBtn = document.getElementById("choose-btn");
const changeBtn = document.getElementById("change-btn");
const extractBtn = document.getElementById("extract-btn");
const uploadZone = document.getElementById("upload-zone");
const uploadPrompt = document.getElementById("upload-prompt");
const previewWrap = document.getElementById("preview-wrap");
const previewImg = document.getElementById("preview-img");

const statusBox = document.getElementById("status");
const statusText = document.getElementById("status-text");
const errorBox = document.getElementById("error-box");
const errorText = document.getElementById("error-text");
const resultBox = document.getElementById("result");
const resultText = document.getElementById("result-text");
const copyBtn = document.getElementById("copy-btn");
const downloadBtn = document.getElementById("download-btn");

let selectedFile = null;

// ---------- Helpers ----------
function show(el) {
  el.classList.remove("hidden");
}
function hide(el) {
  el.classList.add("hidden");
}

function resetView() {
  hide(errorBox);
  hide(resultBox);
  hide(statusBox);
}

// ---------- Choose / change image ----------
chooseBtn.addEventListener("click", () => fileInput.click());
changeBtn.addEventListener("click", () => fileInput.click());

fileInput.addEventListener("change", (e) => {
  const file = e.target.files[0];
  if (!file) return;
  setPreview(file);
});

function setPreview(file) {
  selectedFile = file;
  const reader = new FileReader();
  reader.onload = (e) => {
    previewImg.src = e.target.result;
    hide(uploadPrompt);
    show(previewWrap);
    resetView();
  };
  reader.readAsDataURL(file);
}

// ---------- Drag & drop ----------
["dragenter", "dragover"].forEach((evt) =>
  uploadZone.addEventListener(evt, (e) => {
    e.preventDefault();
    uploadZone.classList.add("drag-over");
  })
);

["dragleave", "drop"].forEach((evt) =>
  uploadZone.addEventListener(evt, (e) => {
    e.preventDefault();
    uploadZone.classList.remove("drag-over");
  })
);

uploadZone.addEventListener("drop", (e) => {
  const file = e.dataTransfer.files[0];
  if (file && file.type.startsWith("image/")) {
    setPreview(file);
  }
});

// ---------- Extract ----------
extractBtn.addEventListener("click", async () => {
  if (!selectedFile) return;

  resetView();
  show(statusBox);
  statusText.textContent = "Padh raha hoon, ek line ek line...";
  extractBtn.disabled = true;

  const formData = new FormData();
  formData.append("image", selectedFile);

  try {
    const res = await fetch("/extract", {
      method: "POST",
      body: formData,
    });

    const data = await res.json();

    if (!res.ok) {
      throw new Error(data.error || "Server error");
    }

    resultText.value = data.text || "(Koi text nahi mila)";
    hide(statusBox);
    show(resultBox);
  } catch (err) {
    hide(statusBox);
    errorText.textContent = err.message;
    show(errorBox);
  } finally {
    extractBtn.disabled = false;
  }
});

// ---------- Copy ----------
copyBtn.addEventListener("click", async () => {
  try {
    await navigator.clipboard.writeText(resultText.value);
    const original = copyBtn.textContent;
    copyBtn.textContent = "Copied!";
    setTimeout(() => (copyBtn.textContent = original), 1200);
  } catch {
    // Fallback for older browsers
    resultText.select();
    document.execCommand("copy");
  }
});

// ---------- Download ----------
downloadBtn.addEventListener("click", () => {
  const blob = new Blob([resultText.value], { type: "text/plain" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "extracted_text.txt";
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
});