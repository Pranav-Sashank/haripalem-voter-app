"""
Comprehensive Unit and Integration Test Suite for Haripalem Voter Web Application.
Validates all endpoints, edge cases, error conditions, and the 16 mandatory test serial numbers.
"""

import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding='utf-8')

from app import app
from services.pdf_processor import get_village_statistics
import fitz

def test_village_statistics():
    print("Testing village statistics...")
    stats = get_village_statistics()
    assert stats['total_voters'] == 2856, f"Expected 2856 voters, got {stats['total_voters']}"
    assert stats['village'] == 'హరిపాలెం'
    assert stats['mandal'] == 'అచ్యుతాపురం'
    assert stats['district'] == 'అనకాపల్లి'
    assert stats['wards'] == 12
    print("  ✓ Village statistics test passed.")

def test_index_route():
    print("Testing index route (GET /)...")
    client = app.test_client()
    resp = client.get('/')
    assert resp.status_code == 200
    html = resp.data.decode('utf-8')
    assert 'హరిపాలెం గ్రామ పంచాయతీ' in html
    assert 'ఓటరు శోధన' in html
    assert '2,856' in html or '2856' in html
    print("  ✓ Index route test passed.")

def test_search_validations():
    print("Testing search input validations...")
    client = app.test_client()
    
    # 1. Empty input
    resp = client.post('/search', json={'serial_number': ''})
    assert resp.status_code == 400
    data = json.loads(resp.data)
    assert data['success'] is False
    assert 'దయచేసి ఓటరు వరుస సంఖ్యను నమోదు చేయండి' in data['error']
    print("  ✓ Empty input validation passed.")

    # 2. Non-numeric
    resp = client.post('/search', json={'serial_number': 'abc'})
    assert resp.status_code == 400
    data = json.loads(resp.data)
    assert data['success'] is False
    assert 'సరైన సంఖ్యను నమోదు చేయండి' in data['error']
    print("  ✓ Non-numeric validation passed.")

    # 3. Low boundary (< 1)
    resp = client.post('/search', json={'serial_number': 0})
    assert resp.status_code == 400
    data = json.loads(resp.data)
    assert data['success'] is False
    assert '1 నుండి 2856 మధ్య మాత్రమే ఉండాలి' in data['error']
    print("  ✓ Out of bounds (0) validation passed.")

    # 4. High boundary (> 2856)
    resp = client.post('/search', json={'serial_number': 2857})
    assert resp.status_code == 400
    data = json.loads(resp.data)
    assert data['success'] is False
    assert '1 నుండి 2856 మధ్య మాత్రమే ఉండాలి' in data['error']
    print("  ✓ Out of bounds (2857) validation passed.")

REQUIRED_TEST_SERIALS = [
    (1, 3, 0, 0, 'సత్యవతీ పైలా', 'XOO0422949'),
    (2, 3, 0, 1, 'అంజలి దోసూరు', 'XOO1333954'),
    (27, 3, 8, 2, 'రామచంద్ర రావు కాండ్రేే గుల', 'MZV2424778'),
    (28, 4, 0, 0, 'శ్రీీనువాస రావు వడిశల', 'XOO1333616'),
    (54, 4, 8, 2, 'నూక అప్పారావు ముప్పిడి', 'XOO0571257'),
    (72, 5, 5, 2, 'ప్ర ణవ్ శశాంక్ కాండ్రేే గుల', 'XOO2131480'),
    (238, 11, 7, 0, 'సతీష్ కుమార్ మత్తుర్తి', 'XOO0733916'),
    (239, 12, 0, 0, 'గౌతమి మత్తుర్తి', 'XOO2111078'),
    (476, 20, 7, 0, 'ఆది లక్ష్మీ ఈశ్వరమ్మ కాండ్రేే గుల', 'MZV1814722'),
    (952, 38, 7, 0, 'నాయుడు కశిరెడ్డి', 'XOO1790997'),
    (1190, 47, 7, 0, 'నాయుడు మారిసెట్టి', 'XOO0733858'),
    (1428, 56, 7, 0, 'షణ్ముఖ శరగడం', 'XOO1989235'),
    (1904, 74, 7, 0, 'మౌనిక కాండ్రేే గుల', 'XOO1313519'),
    (2380, 92, 7, 0, 'కర్రిరి సోనియ మహాలక్ష్మి కర్రిరి', 'XOO1097435'),
    (2618, 101, 7, 0, 'పలివెల లక్ష్మి', 'XOO0734377'),
    (2856, 110, 7, 0, 'పవన్ కుమార్ కాండ్రేే గుల', 'XOO2168466')
]

def test_all_16_required_serials():
    print("\nTesting 16 mandatory serial numbers required by specification...")
    client = app.test_client()

    for sl, exp_page, exp_row, exp_col, exp_name_sub, exp_id in REQUIRED_TEST_SERIALS:
        # 1. Search endpoint
        resp = client.post('/search', json={'serial_number': sl})
        assert resp.status_code == 200, f"Search failed for serial {sl}"
        data = json.loads(resp.data)
        assert data['success'] is True
        
        voter = data['voter']
        assert voter['serial_no'] == sl
        assert voter['page_no'] == exp_page, f"Page mismatch for {sl}: expected {exp_page}, got {voter['page_no']}"
        assert voter['row_idx'] == exp_row, f"Row mismatch for {sl}: expected {exp_row}, got {voter['row_idx']}"
        assert voter['col_idx'] == exp_col, f"Col mismatch for {sl}: expected {exp_col}, got {voter['col_idx']}"
        assert exp_id in voter['voter_id'], f"Voter ID mismatch for {sl}: expected {exp_id}, got {voter['voter_id']}"
        
        # Check preview image
        assert data['preview_image'].startswith('data:image/png;base64,'), f"Invalid preview image for {sl}"
        assert len(data['preview_image']) > 500
        
        # 2. Preview endpoint
        prev_resp = client.get(f'/preview/{sl}')
        assert prev_resp.status_code == 200
        assert prev_resp.mimetype == 'image/png'
        assert len(prev_resp.data) > 1000
        
        # 3. Download PDF endpoint
        dl_resp = client.get(f'/download/{sl}')
        assert dl_resp.status_code == 200, f"Download failed for {sl}"
        assert dl_resp.mimetype == 'application/pdf'
        assert len(dl_resp.data) > 1000
        
        # Verify PDF integrity and mandatory footer
        pdf_doc = fitz.open(stream=dl_resp.data, filetype='pdf')
        assert len(pdf_doc) == 1, f"Expected 1 page PDF for {sl}, got {len(pdf_doc)}"
        page_text = pdf_doc[0].get_text()
        assert 'అనధికారిక' in page_text and 'గుర్తింపు' in page_text, f"Missing footer in PDF for {sl}"
        pdf_doc.close()
        
        print(f"  ✓ SL {sl:4d}: Page {exp_page:3d} (r={exp_row}, c={exp_col}) -> {voter['voter_name']} ({exp_id}) verified.")

    print("\nAll 16 mandatory serial numbers passed with 100% accuracy!")

if __name__ == '__main__':
    test_village_statistics()
    test_index_route()
    test_search_validations()
    test_all_16_required_serials()
    print("\n==========================================")
    print("ALL TEST SUITES PASSED SUCCESSFULLY (100%)")
    print("==========================================")
