"""
Haripalem Telugu Voter Information & PDF Extraction System
Flask Web Application.
"""

import os
import io
from flask import Flask, render_template, request, jsonify, send_file, abort
from services.pdf_processor import (
    init_database,
    get_voter_by_serial,
    get_village_statistics
)
from services.voter_extractor import extract_voter_preview_base64, extract_voter_preview_bytes
from services.pdf_generator import generate_voter_pdf

app = Flask(__name__)
app.config['SECRET_KEY'] = 'haripalem-voter-secret-key-2026'

# Ensure database is initialized on startup
with app.app_context():
    try:
        init_database()
    except Exception as e:
        print(f"Database initialization note: {e}")

@app.route('/', methods=['GET'])
def index():
    """Main application dashboard and search view in Telugu."""
    stats = get_village_statistics()
    return render_template('index.html', stats=stats)

@app.route('/search', methods=['POST'])
def search_voter():
    """
    Search voter by serial number (1 to 2856).
    Accepts JSON or Form submission.
    """
    if request.is_json:
        data = request.get_json() or {}
        raw_val = data.get('serial_number')
    else:
        raw_val = request.form.get('serial_number')

    if raw_val is None or str(raw_val).strip() == '':
        return jsonify({
            'success': False,
            'error': 'దయచేసి ఓటరు వరుస సంఖ్యను నమోదు చేయండి.'
        }), 400

    raw_str = str(raw_val).strip()
    if not raw_str.isdigit():
        return jsonify({
            'success': False,
            'error': 'దయచేసి సరైన సంఖ్యను నమోదు చేయండి. అక్షరాలు లేదా ప్రత్యేక గుర్తులు అనుమతించబడవు.'
        }), 400

    serial_no = int(raw_str)
    if serial_no < 1 or serial_no > 2856:
        return jsonify({
            'success': False,
            'error': 'ఓటరు వరుస సంఖ్య 1 నుండి 2856 మధ్య మాత్రమే ఉండాలి.'
        }), 400

    voter, preview_image = extract_voter_preview_base64(serial_no)
    if not voter:
        return jsonify({
            'success': False,
            'error': f'వరుస సంఖ్య {serial_no} తో ఓటరు వివరాలు లభించలేదు.'
        }), 404

    return jsonify({
        'success': True,
        'voter': voter,
        'preview_image': preview_image,
        'download_url': f'/download/{serial_no}'
    })

@app.route('/download/<int:serial_number>', methods=['GET'])
def download_voter_pdf(serial_number):
    """
    Download standalone PDF for the given voter serial number.
    Extracts the exact original entry preserving typography, borders, and photo.
    """
    if serial_number < 1 or serial_number > 2856:
        return "చెల్లని ఓటరు వరుస సంఖ్య. 1 నుండి 2856 మధ్య మాత్రమే అనుమతించబడుతుంది.", 400

    out_path, pdf_bytes = generate_voter_pdf(serial_number)
    if not pdf_bytes:
        return f"వరుస సంఖ్య {serial_number} కొరకు పి.డి.ఎఫ్ తయారు చేయడం సాధ్యం కాలేదు.", 404

    return send_file(
        io.BytesIO(pdf_bytes),
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f'haripalem_voter_{serial_number}.pdf'
    )

@app.route('/preview/<int:serial_number>', methods=['GET'])
def preview_voter_image(serial_number):
    """
    Returns PNG image bytes of the cropped entry directly from the PDF.
    """
    if serial_number < 1 or serial_number > 2856:
        return abort(400)

    voter, png_bytes = extract_voter_preview_bytes(serial_number)
    if not png_bytes:
        return abort(404)

    return send_file(
        io.BytesIO(png_bytes),
        mimetype='image/png'
    )

@app.route('/api/voter/<int:serial_number>', methods=['GET'])
def api_voter_details(serial_number):
    """
    REST API endpoint for authorized systems to retrieve structured voter data.
    """
    if serial_number < 1 or serial_number > 2856:
        return jsonify({'error': 'ఓటరు వరుస సంఖ్య 1 నుండి 2856 మధ్య మాత్రమే ఉండాలి.'}), 400

    voter = get_voter_by_serial(serial_number)
    if not voter:
        return jsonify({'error': 'ఓటరు వివరాలు లభించలేదు.'}), 404

    return jsonify({
        'success': True,
        'voter': voter,
        'download_url': f'/download/{serial_number}',
        'preview_url': f'/preview/{serial_number}'
    })

@app.errorhandler(404)
def not_found(e):
    return render_template('index.html', stats=get_village_statistics()), 404

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"Starting Haripalem Voter Web App on port {port}...")
    app.run(host='0.0.0.0', port=port, debug=False)
