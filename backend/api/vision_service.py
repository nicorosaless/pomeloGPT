import torch
from transformers import AutoProcessor, AutoModelForCausalLM
from PIL import Image
import io
from pdf2image import convert_from_path
import os

# Fix Tokenizers Parallelism Warning
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# Global model cache to avoid reloading
_model = None
_processor = None
_device = None

def get_device():
    global _device
    if _device is None:
        if torch.backends.mps.is_available():
            _device = "mps"
        elif torch.cuda.is_available():
            _device = "cuda"
        else:
            _device = "cpu"
    return _device

def load_florence_model():
    global _model, _processor
    if _model is None:
        print(f"[VisionService] Loading Florence-2-base on {get_device()}...")
        model_id = "microsoft/Florence-2-base"
        # Load model with trust_remote_code=True as required for Florence-2
        _model = AutoModelForCausalLM.from_pretrained(
            model_id, 
            trust_remote_code=True,
            torch_dtype=torch.float16 if get_device() != "cpu" else torch.float32,
            attn_implementation="eager" # Fix for _supports_sdpa error
        ).to(get_device())
        _processor = AutoProcessor.from_pretrained(model_id, trust_remote_code=True)
        print("[VisionService] Model loaded successfully.")
    return _model, _processor

def process_image(image: Image.Image, task_prompt: str = "<MORE_DETAILED_CAPTION>") -> str:
    """
    Process a single image with Florence-2.
    Tasks: <OCR>, <CAPTION>, <DETAILED_CAPTION>, <MORE_DETAILED_CAPTION>
    """
    model, processor = load_florence_model()
    device = get_device()

    if image.mode != "RGB":
        image = image.convert("RGB")

    inputs = processor(text=task_prompt, images=image, return_tensors="pt").to(device, torch.float16 if device != "cpu" else torch.float32)

    generated_ids = model.generate(
        input_ids=inputs["input_ids"],
        pixel_values=inputs["pixel_values"],
        max_new_tokens=1024,
        early_stopping=False,
        do_sample=False,
        num_beams=3,
    )
    generated_text = processor.batch_decode(generated_ids, skip_special_tokens=False)[0]
    parsed_answer = processor.post_process_generation(
        generated_text, 
        task=task_prompt, 
        image_size=(image.width, image.height)
    )
    
    # Florence-2 returns a dictionary, we want the text content
    return parsed_answer.get(task_prompt, "")

def extract_text_from_pdf_with_vision(pdf_path: str, progress_callback=None) -> str:
    """
    Convert PDF pages to images and process each with Florence-2 OCR.
    progress_callback: function(current_page, total_pages)
    """
    print(f"[VisionService] Processing PDF: {pdf_path}")
    try:
        images = convert_from_path(pdf_path)
    except Exception as e:
        print(f"[VisionService] Error converting PDF to images: {e}")
        # Fallback or re-raise? Let's re-raise for now as this is the primary path
        raise e

    full_text = ""
    for i, img in enumerate(images):
        if progress_callback:
            progress_callback(i + 1, len(images))
            
        print(f"[VisionService] Processing page {i+1}/{len(images)}...")
        # Use <OCR> task for text extraction, or <MORE_DETAILED_CAPTION> for description
        # For documents, we often want OCR. But Florence-2 <OCR> is very good.
        # Let's try to combine OCR with a structural understanding if possible, 
        # but <OCR> is the standard for text.
        # However, the user wants "tables". Florence-2 doesn't output Markdown tables natively in base model 
        # as well as DeepSeek, but it does OCR well. 
        # Let's use <OCR> for now. 
        # Ideally we would use a prompt like 'Analyze this document image and extract text and tables.'
        # Florence-2 supports specific tasks. <OCR> is the safest bet for raw text.
        
        page_content = process_image(img, task_prompt="<OCR>")
        
        # We can also get a description of the layout/images
        description = process_image(img, task_prompt="<MORE_DETAILED_CAPTION>")
        
        full_text += f"\n--- Page {i+1} ---\n"
        full_text += f"[Page Description: {description}]\n\n"
        full_text += page_content + "\n"
        
    return full_text
