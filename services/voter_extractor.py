"""
Voter Extractor Service.
Extracts voter entry from original PDF, renders high-resolution preview images,
and preserves the exact original PDF appearance.
"""

import os
import base64
import fitz
from services.pdf_processor import get_voter_by_serial, PDF_PATH

# Exact bounding box preserves borders without neighboring bleed
BOX_MARGIN = 0.0

def get_voter_box_rect(voter):
    """
    Returns fitz.Rect for the voter box with a small margin to capture full outer borders.
    """
    return fitz.Rect(
        voter['box_x0'] - BOX_MARGIN,
        voter['box_y0'] - BOX_MARGIN,
        voter['box_x1'] + BOX_MARGIN,
        voter['box_y1'] + BOX_MARGIN
    )

def extract_voter_preview_bytes(serial_no, dpi=250):
    """
    Renders the exact voter entry as a high-resolution PNG image.
    Does not modify or rebuild any HTML/canvas: renders directly from the original PDF vector/image stream.
    """
    voter = get_voter_by_serial(serial_no)
    if not voter:
        return None, None
        
    doc = fitz.open(PDF_PATH)
    page_idx = voter['page_index']
    page = doc[page_idx]
    
    clip_rect = get_voter_box_rect(voter)
    
    # Render with high DPI for crisp Telugu text and photo clarity
    pix = page.get_pixmap(clip=clip_rect, dpi=dpi)
    png_bytes = pix.tobytes("png")
    doc.close()
    
    return voter, png_bytes

def extract_voter_preview_base64(serial_no, dpi=250):
    """
    Returns voter dict and base64-encoded PNG data URL.
    """
    voter, png_bytes = extract_voter_preview_bytes(serial_no, dpi=dpi)
    if not voter or not png_bytes:
        return None, None
        
    b64_str = base64.b64encode(png_bytes).decode('ascii')
    data_url = f"data:image/png;base64,{b64_str}"
    return voter, data_url
