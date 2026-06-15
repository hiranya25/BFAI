import os
import tempfile
import subprocess
from pathlib import Path
from typing import List, Dict, Any

from pdf2image import convert_from_path
from PIL import Image

from app.core.config import get_settings

settings = get_settings()
THUMBNAIL_DIR = settings.thumbnail_dir
THUMBNAIL_DIR.mkdir(parents=True, exist_ok=True)

def _generate_thumbnails(file_path: str, doc_id: str, is_image: bool = False) -> List[str]:
    image_paths = []
    if is_image:
        try:
            pil_img = Image.open(file_path)
            if pil_img.mode in ("RGBA", "P"):
                pil_img = pil_img.convert("RGB")
            thumb_filename = f"{doc_id}_page_1.jpg"
            thumb_path = THUMBNAIL_DIR / thumb_filename
            pil_img.save(str(thumb_path), "JPEG", quality=85)
            image_paths.append(thumb_filename)
        except Exception as e:
            print(f"Failed generating thumbnail for image: {e}")
    else:
        try:
            page_images = convert_from_path(str(file_path), dpi=150, first_page=1, last_page=50)
            for i, pil_img in enumerate(page_images):
                thumb_filename = f"{doc_id}_page_{i+1}.jpg"
                thumb_path = THUMBNAIL_DIR / thumb_filename
                pil_img.save(str(thumb_path), "JPEG", quality=85)
                image_paths.append(thumb_filename)
        except Exception as e:
            print(f"Failed generating thumbnails for PDF: {e}")
    return image_paths

def _clean_ocr_text_with_llm(raw_text: str) -> str:
    """Uses ultra-fast Groq LLM to correct OCR typos from messy handwriting."""
    if len(raw_text.strip()) < 5:
        return raw_text
    
    try:
        from groq import Groq
        from app.core.config import get_settings
        settings = get_settings()
        client = Groq(api_key=settings.groq_api_key)
        
        prompt = f"""You are an expert at correcting OCR errors from scanned handwritten notes.
Please read the following noisy OCR text. Correct any obvious misspellings, typos, and formatting errors caused by bad handwriting recognition. 
For example, if you see 'Tsve posshve', correct it to 'True positive'. If you see 'Logishe regression', correct it to 'Logistic regression'.
Do NOT add any new information. Do not hallucinate. Just fix the typos to make it perfectly readable.
Output ONLY the corrected text and nothing else.

Raw OCR Text:
{raw_text}
"""
        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        print(f"LLM OCR correction failed: {e}")
        return raw_text

def _preprocess_for_ocr(image_path: str) -> str:
    import cv2
    import numpy as np
    
    # Read with alpha channel to preserve transparency
    img = cv2.imread(image_path, cv2.IMREAD_UNCHANGED)
    if img is None:
        return image_path
        
    # Handle transparent PNGs by compositing over a white background
    if len(img.shape) == 3 and img.shape[2] == 4:
        alpha_channel = img[:, :, 3] / 255.0
        rgb_channels = img[:, :, :3]
        white_background = np.ones_like(rgb_channels, dtype=np.uint8) * 255
        
        img = (rgb_channels * alpha_channel[:, :, np.newaxis] + 
               white_background * (1 - alpha_channel[:, :, np.newaxis])).astype(np.uint8)
    
    # Convert to grayscale for consistent OCR but skip aggressive CLAHE 
    # which introduces heavy artifacts on clean digital screenshots
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    out_path = image_path + "_preproc.png"
    cv2.imwrite(out_path, gray)
    return out_path

def _extract_handwriting(image_path: str, doctr_result) -> str:
    from PIL import Image
    from transformers import TrOCRProcessor, VisionEncoderDecoderModel
    import torch
    
    print("Loading TrOCR model for handwriting fallback...")
    processor = TrOCRProcessor.from_pretrained("microsoft/trocr-small-handwritten")
    model = VisionEncoderDecoderModel.from_pretrained("microsoft/trocr-small-handwritten")
    
    img = Image.open(image_path).convert("RGB")
    width, height = img.size
    full_text = ""
    
    for page in doctr_result.pages:
        for block in page.blocks:
            for line in block.lines:
                ((xmin, ymin), (xmax, ymax)) = line.geometry
                x1 = max(0, int(xmin * width) - 5)
                y1 = max(0, int(ymin * height) - 5)
                x2 = min(width, int(xmax * width) + 5)
                y2 = min(height, int(ymax * height) + 5)
                
                if x2 <= x1 or y2 <= y1:
                    continue
                    
                line_img = img.crop((x1, y1, x2, y2))
                pixel_values = processor(line_img, return_tensors="pt").pixel_values
                with torch.no_grad():
                    generated_ids = model.generate(pixel_values, max_new_tokens=50)
                text = processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
                full_text += text + "\n"
            full_text += "\n"
    return full_text.strip()

def _extract_with_vision(image_path: str) -> str:
    """Uses Groq's incredibly fast Vision model to extract complex scanned tables into Markdown."""
    import base64
    from groq import Groq
    from app.core.config import get_settings
    from PIL import Image
    import io
    
    try:
        settings = get_settings()
        client = Groq(api_key=settings.groq_api_key)
        
        # Resize image to prevent Payload Too Large errors
        img = Image.open(image_path)
        img.thumbnail((1024, 1024), Image.Resampling.LANCZOS)
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
            
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=85)
        encoded_string = base64.b64encode(buffer.getvalue()).decode('utf-8')
            
        prompt = """You are a highly precise document extraction AI.
Please read the attached scanned document and extract ALL text exactly as it appears.
The document may contain both English and Hindi text. Extract BOTH accurately.
If the document contains tables, you MUST format them strictly as proper Markdown tables.
Do not hallucinate. Do not add conversational text. Output ONLY the extracted text/markdown."""

        completion = client.chat.completions.create(
            model="llama-3.2-90b-vision-preview",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{encoded_string}",
                            },
                        },
                    ],
                }
            ],
            temperature=0,
            max_tokens=2000,
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        print(f"Groq Vision extraction failed: {e}")
        return ""

def _run_doctr_and_trocr(image_path: str) -> tuple[str, float, str]:
    from doctr.models import ocr_predictor
    from doctr.io import DocumentFile
    import numpy as np
    
    preprocessed_path = _preprocess_for_ocr(image_path)
    
    model = ocr_predictor(det_arch='db_resnet50', reco_arch='parseq', pretrained=True)
    d_doc = DocumentFile.from_images(preprocessed_path)
    result = model(d_doc)
    
    page_text = ""
    confidences = []
    for doctr_page in result.pages:
        for block in doctr_page.blocks:
            for line in block.lines:
                for word in line.words:
                    page_text += word.value + " "
                    confidences.append(word.confidence)
                page_text += "\n"
            page_text += "\n"
            
    avg_conf = float(np.mean(confidences)) if confidences else 0.0
    text = page_text.strip()
    extraction_method = "doctr_parseq_ocr"
    
    if avg_conf < 0.85 and len(confidences) > 0:
        print(f"Low OCR confidence ({avg_conf}). Routing to TrOCR handwriting fallback...")
        trocr_text = _extract_handwriting(preprocessed_path, result)
        if len(trocr_text.strip()) > 10:
            text = trocr_text
            extraction_method = "trocr_handwriting"
            avg_conf = 0.9 
            
    # Apply post-OCR correction via LLM to fix "Tsve" -> "True", "posshve" -> "positive", etc.
    if text.strip():
        text = _clean_ocr_text_with_llm(text)
            
    return text, avg_conf, extraction_method

def _parse_with_doctr(file_path: str, doc_id: str, is_image: bool = False) -> List[Dict[str, Any]]:
    pages = []
    image_paths = _generate_thumbnails(file_path, doc_id, is_image=is_image)
    
    try:
        if is_image:
            vision_text = _extract_with_vision(file_path)
            if vision_text and len(vision_text.strip()) > 20:
                text = vision_text
                conf = 0.98
                method = "groq_vision_90b"
            else:
                text, conf, method = _run_doctr_and_trocr(file_path)
                
            pages.append({
                "page_num": 1,
                "text": text,
                "tables": [],
                "confidence_score": conf,
                "image_path": image_paths[0] if image_paths else "",
                "extraction_method": method,
                "parse_mode": "doctr"
            })
        else:
            import fitz
            import tempfile
            doc = fitz.open(file_path)
            for i, page in enumerate(doc):
                pix = page.get_pixmap(dpi=200)
                with tempfile.NamedTemporaryFile(suffix=".png") as tmp:
                    pix.save(tmp.name)
                    text, conf, method = _run_doctr_and_trocr(tmp.name)
                    
                    pages.append({
                        "page_num": i + 1,
                        "text": text,
                        "tables": [],
                        "confidence_score": conf,
                        "image_path": image_paths[i] if i < len(image_paths) else "",
                        "extraction_method": method,
                        "parse_mode": "doctr"
                    })
    except Exception as e:
        print(f"DocTR/TrOCR failed: {e}")
        pages.append({
            "page_num": 1,
            "text": f"Error: {e}",
            "tables": [],
            "confidence_score": 0.0,
            "image_path": image_paths[0] if image_paths else "",
            "extraction_method": "error",
            "parse_mode": "error"
        })
    return pages

def _parse_pdf_smart(file_path: str, doc_id: str) -> List[Dict[str, Any]]:
    """Smart Document Routing: PyMuPDF for digital text/tables, DocTR PARSeq for scanned/handwritten."""
    pages = []
    image_paths = _generate_thumbnails(file_path, doc_id, is_image=False)
    
    try:
        import fitz
        import pandas as pd
        doc = fitz.open(file_path)
        
        doctr_model = None
        
        for i, page in enumerate(doc):
            text = page.get_text("text")
            tables = []
            
            # Extract tables accurately
            try:
                tabs = page.find_tables()
                for tab in tabs:
                    df = tab.to_pandas()
                    if not df.empty:
                        tables.append({
                            "headers": df.columns.tolist() if not df.columns.empty else [],
                            "rows": df.values.tolist()
                        })
            except Exception as e:
                print(f"Table extraction failed on page {i+1}: {e}")
            
            # Smart Routing: If text length is very low, it's a scanned PDF or heavily handwritten
            if len(text.strip()) < 50:
                pix = page.get_pixmap(dpi=200)
                import tempfile
                with tempfile.NamedTemporaryFile(suffix=".png") as tmp:
                    pix.save(tmp.name)
                    
                    # Try Groq Vision first for perfect table preservation
                    vision_text = _extract_with_vision(tmp.name)
                    if vision_text and len(vision_text.strip()) > 20:
                        text = vision_text
                        avg_conf = 0.98
                        extraction_method = "groq_vision_90b"
                    else:
                        text, avg_conf, extraction_method = _run_doctr_and_trocr(tmp.name)
            else:
                avg_conf = 1.0
                extraction_method = "pymupdf_digital"
                
            pages.append({
                "page_num": i + 1,
                "text": text.strip(),
                "tables": tables,
                "confidence_score": round(avg_conf, 3),
                "image_path": image_paths[i] if i < len(image_paths) else "",
                "extraction_method": extraction_method,
                "parse_mode": "smart"
            })
            
    except Exception as e:
        print(f"Smart parsing failed: {e}. Falling back to pure OCR.")
        return _parse_with_doctr(file_path, doc_id, is_image=False)
        
    return pages

def _parse_with_marker(file_path: str, doc_id: str) -> List[Dict[str, Any]]:
    pages = []
    image_paths = _generate_thumbnails(file_path, doc_id, is_image=False)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            # We use marker_single CLI to convert PDF to Markdown
            subprocess.run([
                "marker_single", str(file_path), "--output_dir", temp_dir
            ], check=True, capture_output=True)
            
            base_name = Path(file_path).stem
            out_folder = Path(temp_dir) / base_name
            md_file = out_folder / f"{base_name}.md"
            
            if md_file.exists():
                text = md_file.read_text(encoding="utf-8")
                # Marker often outputs a single file for the whole document.
                # We map the whole extracted markdown text to the first page.
                for i in range(max(1, len(image_paths))):
                    pages.append({
                        "page_num": i + 1,
                        "text": text if i == 0 else "", 
                        "tables": [],
                        "image_path": image_paths[i] if i < len(image_paths) else "",
                        "parse_mode": "marker"
                    })
            else:
                raise FileNotFoundError("Marker did not produce an output markdown file.")
        except subprocess.CalledProcessError as e:
            err_msg = e.stderr.decode() if e.stderr else str(e)
            print(f"Marker failed: {err_msg}")
            pages.append({
                "page_num": 1,
                "text": f"Marker Error: {err_msg}",
                "tables": [],
                "image_path": image_paths[0] if image_paths else "",
                "parse_mode": "error"
            })
        except Exception as e:
            print(f"Marker failed: {e}")
            pages.append({
                "page_num": 1,
                "text": f"Marker Error: {e}",
                "tables": [],
                "image_path": image_paths[0] if image_paths else "",
                "parse_mode": "error"
            })
    return pages

def parse_document(file_path: str, doc_id: str) -> List[Dict[str, Any]]:
    import magic
    try:
        mime_type = magic.from_file(file_path, mime=True)
    except Exception as e:
        mime_type = "application/pdf"

    is_img = mime_type.startswith("image/")
    if is_img:
        return _parse_with_doctr(file_path, doc_id, is_image=True)
    else:
        return _parse_pdf_smart(file_path, doc_id)
