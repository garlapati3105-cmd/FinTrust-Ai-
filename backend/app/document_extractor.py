from __future__ import annotations

import io
from dataclasses import dataclass
from typing import Any

import numpy as np
from PIL import Image
import pymupdf

from .document_security import MAX_PDF_PAGES, safe_temporary_file

# Initialize RapidOCR lazily or gracefully
_ocr_engine = None


def get_ocr_engine():
    global _ocr_engine
    if _ocr_engine is None:
        try:
            from rapidocr_onnxruntime import RapidOCR
            _ocr_engine = RapidOCR()
        except Exception:
            _ocr_engine = False
    return _ocr_engine if _ocr_engine is not False else None


@dataclass
class PageExtraction:
    page_number: int
    text: str
    ocr_applied: bool = False


@dataclass
class DocumentTextResult:
    file_type: str
    page_count: int
    pages: list[PageExtraction]
    full_text: str
    ocr_applied: bool
    ocr_engine: str | None


def _perform_image_ocr(image_bytes: bytes) -> tuple[str, bool]:
    ocr = get_ocr_engine()
    if ocr is None:
        return "", False

    try:
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        img_arr = np.array(image)
        result, _ = ocr(img_arr)
        if not result:
            return "", True
        extracted_lines = [item[1].strip() for item in result if len(item) > 1 and item[1].strip()]
        return "\n".join(extracted_lines), True
    except Exception:
        return "", False


def _perform_pixmap_ocr(pix: pymupdf.Pixmap) -> tuple[str, bool]:
    ocr = get_ocr_engine()
    if ocr is None:
        return "", False

    try:
        img_arr = np.frombuffer(pix.samples, dtype=np.uint8).reshape((pix.height, pix.width, pix.n))
        if pix.n == 4:
            img_arr = img_arr[:, :, :3]
        result, _ = ocr(img_arr)
        if not result:
            return "", True
        extracted_lines = [item[1].strip() for item in result if len(item) > 1 and item[1].strip()]
        return "\n".join(extracted_lines), True
    except Exception:
        return "", False


def extract_document_text(content: bytes, file_type: str) -> DocumentTextResult:
    """
    Extracts text from PDF (native selectable text with OCR fallback) or image (OCR).
    Preserves page boundaries and numbers (1-indexed).
    Raises ValueError on oversized, malformed, or blank documents.
    """
    if file_type == "pdf":
        with safe_temporary_file(content, suffix=".pdf") as temp_pdf_path:
            try:
                doc = pymupdf.open(temp_pdf_path)
            except Exception as err:
                raise ValueError(f"Malformed or corrupt PDF document: {err}") from err

            try:
                page_count = len(doc)
                if page_count == 0:
                    raise ValueError("PDF document contains 0 pages.")
                if page_count > MAX_PDF_PAGES:
                    raise ValueError(
                        f"Document contains {page_count} pages, which exceeds the maximum "
                        f"allowed limit of {MAX_PDF_PAGES} pages."
                    )

                pages: list[PageExtraction] = []
                any_ocr = False

                for page_idx in range(page_count):
                    page = doc[page_idx]
                    native_text = page.get_text("text").strip()
                    ocr_used = False

                    # If page has very little or no native text, run OCR fallback
                    if len(native_text) < 15:
                        pix = page.get_pixmap(dpi=150)
                        ocr_text, ocr_success = _perform_pixmap_ocr(pix)
                        if ocr_text:
                            # Combine or use OCR text
                            page_text = f"{native_text}\n{ocr_text}".strip() if native_text else ocr_text
                            ocr_used = True
                            any_ocr = True
                        else:
                            page_text = native_text
                    else:
                        page_text = native_text

                    pages.append(PageExtraction(page_number=page_idx + 1, text=page_text, ocr_applied=ocr_used))

                full_text = "\n\n".join([f"--- Page {p.page_number} ---\n{p.text}" for p in pages if p.text.strip()])
                combined_clean = " ".join([p.text.strip() for p in pages]).strip()

                if not combined_clean:
                    raise ValueError(
                        "No readable text could be extracted from the PDF document. "
                        "The document appears to be empty, unreadable, or missing text layers."
                    )

                return DocumentTextResult(
                    file_type="pdf",
                    page_count=page_count,
                    pages=pages,
                    full_text=full_text,
                    ocr_applied=any_ocr,
                    ocr_engine="RapidOCR" if any_ocr else None,
                )
            finally:
                doc.close()

    elif file_type in ("png", "jpeg"):
        text, ocr_success = _perform_image_ocr(content)
        if not text.strip():
            raise ValueError(
                "No readable text could be extracted from the image. "
                "The image may be blank, low resolution, or contain no recognizable text."
            )

        page_extraction = PageExtraction(page_number=1, text=text.strip(), ocr_applied=True)
        return DocumentTextResult(
            file_type=file_type,
            page_count=1,
            pages=[page_extraction],
            full_text=f"--- Page 1 ---\n{page_extraction.text}",
            ocr_applied=True,
            ocr_engine="RapidOCR",
        )
    else:
        raise ValueError(f"Unsupported file type: {file_type}")
