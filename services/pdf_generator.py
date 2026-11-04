"""
PDF Generator Service.
Generates an individual, one-page PDF document for a voter entry.
Uses PyMuPDF clipping and page.show_pdf_page() to preserve original vector quality,
Telugu typography, photo resolution, and original borders without modification.
Includes the required official footer outside the extracted entry.
"""

import os
import fitz
from services.pdf_processor import get_voter_by_serial, PDF_PATH

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GENERATED_DIR = os.path.join(BASE_DIR, 'generated')
FONT_PATH = os.path.join(BASE_DIR, 'static', 'fonts', 'Nirmala.ttc')
if not os.path.exists(FONT_PATH) and os.path.exists("C:/Windows/Fonts/Nirmala.ttc"):
    FONT_PATH = "C:/Windows/Fonts/Nirmala.ttc"

# Use exact bounding box from vector path - guarantees all 4 borders are captured
# without any bleed from neighboring text/headers.
BOX_MARGIN = 0.0

def generate_voter_pdf(serial_no, save_to_disk=True):
    """
    Generates a high-quality one-page PDF for the voter entry.
    Returns the file path or bytes of the generated PDF.
    """
    os.makedirs(GENERATED_DIR, exist_ok=True)
    out_path = os.path.join(GENERATED_DIR, f"voter_{serial_no}.pdf")
    
    # Return cached if already exists and valid
    if save_to_disk and os.path.exists(out_path) and os.path.getsize(out_path) > 1000:
        with open(out_path, "rb") as f:
            return out_path, f.read()

    voter = get_voter_by_serial(serial_no)
    if not voter:
        return None, None

    src_doc = fitz.open(PDF_PATH)
    page_idx = voter['page_index']
    
    # Bounding box of original entry with border safety margin
    orig_box = fitz.Rect(
        voter['box_x0'] - BOX_MARGIN,
        voter['box_y0'] - BOX_MARGIN,
        voter['box_x1'] + BOX_MARGIN,
        voter['box_y1'] + BOX_MARGIN
    )

    # Document layout:
    # Card is scaled 2.4x for crisp readability and high-resolution presentation
    scale = 2.4
    card_w = (voter['box_x1'] - voter['box_x0']) * scale
    card_h = (voter['box_y1'] - voter['box_y0']) * scale
    
    page_w = 480.0
    page_h = 285.0
    
    card_x = (page_w - card_w) / 2.0
    card_y = 50.0
    target_rect = fitz.Rect(card_x, card_y, card_x + card_w, card_y + card_h)
    
    out_doc = fitz.open()
    out_page = out_doc.new_page(width=page_w, height=page_h)
    
    # Show the exact original voter entry via PDF Form XObject
    # Preserves 100% vector typography, photo bytes, and original styling
    out_page.show_pdf_page(target_rect, src_doc, page_idx, clip=orig_box)
    
    # Load Telugu font for headers and required footer
    font = fitz.Font(fontfile=FONT_PATH) if os.path.exists(FONT_PATH) else None
    
    # Header above the card
    header_text = "హరిపాలెం గ్రామ పంచాయతీ – ఓటరు వివరాల పత్రం (2026)"
    if font:
        tw_header = fitz.TextWriter(out_page.rect)
        h_len = font.text_length(header_text, fontsize=11)
        tw_header.append(((page_w - h_len) / 2.0, 30), header_text, font=font, fontsize=11)
        tw_header.write_text(out_page, color=(0.08, 0.38, 0.18))
    
    # Mandatory footer text required by specification:
    # "అనధికారిక ఓటరు సమాచారం ప్రతీ — గుర్తింపు పత్రం కాదు"
    footer_text = "అనధికారిక ఓటరు సమాచారం ప్రతీ — గుర్తింపు పత్రం కాదు"
    if font:
        tw_footer = fitz.TextWriter(out_page.rect)
        footer_y = card_y + card_h + 24
        f_len = font.text_length(footer_text, fontsize=9.5)
        tw_footer.append(((page_w - f_len) / 2.0, footer_y), footer_text, font=font, fontsize=9.5)
        tw_footer.write_text(out_page, color=(0.42, 0.42, 0.42))
        
        # Subtitle with ward and serial number outside entry
        meta_text = f"వరుస సంఖ్య: {voter['serial_no']}  |  వార్డు నెంబరు: {voter['ward_no']}  |  అనకాపల్లి జిల్లా"
        m_len = font.text_length(meta_text, fontsize=7.5)
        tw_meta = fitz.TextWriter(out_page.rect)
        tw_meta.append(((page_w - m_len) / 2.0, footer_y + 14), meta_text, font=font, fontsize=7.5)
        tw_meta.write_text(out_page, color=(0.55, 0.55, 0.55))

    pdf_bytes = out_doc.tobytes()
    
    if save_to_disk:
        with open(out_path, "wb") as f:
            f.write(pdf_bytes)
            
    out_doc.close()
    src_doc.close()
    
    return out_path, pdf_bytes
