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
    if not file_doc:
        return None

    return frappe.get_doc("File", file_doc[0].name).get_full_path()


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

@frappe.whitelist(allow_guest=True)
def pdf_to_base64_image(file_url):
    try:
        file_path = _get_file_path(file_url)
        if not file_path:
            return None

        pdf_doc = fitz.open(file_path)
        try:
            page = pdf_doc[0]
            clip_rect = _get_content_rect(page)

            # Render only the visible content area for cleaner print output.
            pix = page.get_pixmap(
                matrix=fitz.Matrix(3, 3),
                alpha=False,
                clip=clip_rect,
            )
            img_bytes = pix.tobytes("png")
        finally:
            pdf_doc.close()

        b64 = base64.b64encode(img_bytes).decode("utf-8")
        return f"data:image/png;base64,{b64}"
    except Exception:
        frappe.log_error(frappe.get_traceback(), "PDF to Image Conversion Error")
        return None
