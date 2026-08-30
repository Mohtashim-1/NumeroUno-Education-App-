import os
import base64
from urllib.parse import unquote, urlparse

import fitz  # PyMuPDF
import frappe


def _get_file_path(file_url):
    if not file_url:
        return None

    parsed_url = urlparse(file_url)
    normalized_url = unquote(parsed_url.path or file_url)

    if not normalized_url.startswith("/"):
        normalized_url = "/" + normalized_url.lstrip("/")

    file_doc = frappe.get_all(
        "File",
        filters={"file_url": normalized_url},
        fields=["name"],
        limit=1,
    )
    if file_doc:
        full_path = frappe.get_doc("File", file_doc[0].name).get_full_path()
        return os.path.abspath(full_path) if full_path else None

    fname = os.path.basename(normalized_url.split("?")[0])
    if not fname:
        return None
    is_private = "/private/files/" in normalized_url
    candidate = frappe.utils.get_files_path(fname, is_private=is_private)
    if candidate and os.path.exists(candidate):
        return os.path.abspath(candidate)
    return None


def _get_content_rect(page, padding=12):
    rects = []

    text_blocks = page.get_text("blocks") or []
    for block in text_blocks:
        x0, y0, x1, y1 = block[:4]
        if x1 > x0 and y1 > y0:
            rects.append(fitz.Rect(x0, y0, x1, y1))

    image_infos = page.get_image_info() or []
    for image in image_infos:
        bbox = image.get("bbox")
        if bbox:
            rects.append(fitz.Rect(bbox))

    if not rects:
        return page.rect

    content_rect = rects[0]
    for rect in rects[1:]:
        content_rect |= rect

    content_rect.x0 = max(page.rect.x0, content_rect.x0 - padding)
    content_rect.y0 = max(page.rect.y0, content_rect.y0 - padding)
    content_rect.x1 = min(page.rect.x1, content_rect.x1 + padding)
    content_rect.y1 = min(page.rect.y1, content_rect.y1 + padding)
    return content_rect

def _page_to_data_uri(page, clip=False, scale=2):
    kwargs = {"matrix": fitz.Matrix(scale, scale), "alpha": False}
    if clip:
        kwargs["clip"] = _get_content_rect(page)
    pix = page.get_pixmap(**kwargs)
    img_bytes = pix.tobytes("png")
    b64 = base64.b64encode(img_bytes).decode("utf-8")
    return f"data:image/png;base64,{b64}"


def pdf_to_base64_images(file_url, max_pages=20, clip=False, scale=2):
    """Convert every PDF page into a print-ready PNG data URI."""
    try:
        file_path = _get_file_path(file_url)
        if not file_path:
            return []

        pdf_doc = fitz.open(file_path)
        try:
            page_count = min(len(pdf_doc), int(max_pages or 20))
            return [
                _page_to_data_uri(pdf_doc[index], clip=clip, scale=scale)
                for index in range(page_count)
            ]
        finally:
            pdf_doc.close()
    except Exception:
        frappe.log_error(frappe.get_traceback(), "PDF to Images Conversion Error")
        return []


@frappe.whitelist(allow_guest=True)
def pdf_to_base64_image(file_url):
    try:
        pages = pdf_to_base64_images(file_url, max_pages=1, clip=True, scale=3)
        return pages[0] if pages else None
    except Exception:
        frappe.log_error(frappe.get_traceback(), "PDF to Image Conversion Error")
        return None
