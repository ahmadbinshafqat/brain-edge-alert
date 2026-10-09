from pathlib import Path
from pypdf import PdfReader


def extract_text(path: str, content_type: str = "") -> str:
    suffix = Path(path).suffix.lower()
    if suffix == ".pdf" or "pdf" in content_type:
        return _extract_pdf_text(path)
    if suffix in {".txt", ".csv", ".md"} or content_type.startswith("text/"):
        return Path(path).read_text(encoding="utf-8", errors="ignore")
    if suffix in {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp"} or content_type.startswith("image/"):
        return _extract_image_text(path)
    return Path(path).read_bytes()[:4096].decode("utf-8", errors="ignore")


def _extract_pdf_text(path: str) -> str:
    try:
        reader = PdfReader(path)
        parts = []
        for page in reader.pages:
            parts.append(page.extract_text() or "")
        text = "\n".join(parts).strip()
        return text or "No selectable PDF text found. If this is a scanned document, upload an image with Tesseract OCR installed."
    except Exception as exc:
        return f"PDF text extraction failed: {exc}"


def _extract_image_text(path: str) -> str:
    try:
        from PIL import Image
        import pytesseract

        return pytesseract.image_to_string(Image.open(path)).strip()
    except Exception as exc:
        return f"Image OCR unavailable or failed: {exc}. Install the Tesseract system binary to enable image OCR."
