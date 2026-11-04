"""
Haripalem Telugu Voter Information & PDF Extraction System
Flask Web Application.
"""

import os
import io
from functools import wraps
from flask import Flask, render_template, request, jsonify, send_file, abort, redirect, session, url_for
from werkzeug.security import check_password_hash
from services.pdf_processor import init_database, get_voter_by_serial, get_village_statistics, search_voters
from services.voter_extractor import extract_voter_preview_base64, extract_voter_preview_bytes

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', os.urandom(32))
ACCESS_PASSWORD_HASH = os.environ.get('ACCESS_PASSWORD_HASH')

def format_display_text(value):
    """Remove PDF text-extraction artifacts without changing actual voter data."""
    if not value:
        return value
    text = ' '.join(str(value).split())
    # Collapse duplicated Telugu vowel marks produced by the source PDF text layer.
    import re
    text = re.sub(r'([\u0C3E-\u0C4D])\1+', r'\1', text)
    parts = text.split(' ')
    fixed = []
    index = 0
    while index < len(parts):
        part = parts[index]
        # A detached conjunct such as "ప్ర ణవ్" is a single word in the card.
        if index + 1 < len(parts) and len(part) <= 3 and '\u0c4d' in part:
            fixed.append(part + parts[index + 1])
            index += 2
            continue
        # A PDF line wrap can split the common surname ending "కాండ్రే గుల".
        if index + 1 < len(parts) and parts[index + 1] == 'గుల' and '\u0c4d' in part:
            fixed.append(part + parts[index + 1])
            index += 2
            continue
        fixed.append(part)
        index += 1
    return ' '.join(fixed)

def format_voter_for_display(voter):
    voter = dict(voter)
    for field in ('voter_name', 'relative_name'):
        voter[field] = format_display_text(voter.get(field))
    return voter

def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if not session.get('authenticated'):
            if request.path == '/search' or request.path.startswith(('/preview/', '/api/')):
                return jsonify({'success': False, 'error': 'దయచేసి ముందుగా సైన్ ఇన్ చేయండి.'}), 401
            return redirect(url_for('login', next=request.path))
        return view(*args, **kwargs)
    return wrapped_view

# Ensure database is initialized on startup
with app.app_context():
    try:
        init_database()
    except Exception as e:
        print(f"Database initialization note: {e}")

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        submitted_password = request.form.get('password', '')
        if ACCESS_PASSWORD_HASH and check_password_hash(ACCESS_PASSWORD_HASH, submitted_password):
            session.clear()
            session['authenticated'] = True
            session.permanent = True
            next_page = request.form.get('next') or url_for('index')
            return redirect(next_page)
        error = 'పాస్‌వర్డ్ సరైనది కాదు.'
    return render_template('login.html', error=error, next_page=request.args.get('next', ''))

@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/', methods=['GET'])
@login_required
def index():
    """Main application dashboard and search view in Telugu."""
    stats = get_village_statistics()
    return render_template('index.html', stats=stats)

@app.route('/search', methods=['POST'])
@login_required
def search_voter():
    """
    Search voter by serial number (1 to 2856).
    Accepts JSON or Form submission.
    """
    if request.is_json:
        data = request.get_json() or {}
        raw_val = data.get('query')
    else:
        raw_val = request.form.get('query')

    if raw_val is None or str(raw_val).strip() == '':
        return jsonify({
            'success': False,
            'error': 'దయచేసి వరుస సంఖ్య, పేరు లేదా ఓటరు ఐడి నమోదు చేయండి.'
        }), 400

    query = str(raw_val).strip()
    if query.isdigit() and not 1 <= int(query) <= 2856:
        return jsonify({
            'success': False,
            'error': 'ఓటరు వరుస సంఖ్య 1 నుండి 2856 మధ్య మాత్రమే ఉండాలి.'
        }), 400

    match_type, voters = search_voters(query)
    if match_type == 'none':
        return jsonify({
            'success': False,
            'error': 'మీ శోధనకు సరిపోయే ఓటరు వివరాలు లభించలేదు.'
        }), 404

    if match_type == 'list':
        return jsonify({
            'success': True,
            'match_type': 'list',
            'voters': [format_voter_for_display(voter) for voter in voters]
        })

    voter, preview_image = extract_voter_preview_base64(voters[0]['serial_no'])
    voter = format_voter_for_display(voter)

    return jsonify({
        'success': True,
        'match_type': 'exact',
        'voter': voter,
        'preview_image': preview_image,
        'print_url': f'/print/{voter["serial_no"]}'
    })

@app.route('/print/<int:serial_number>', methods=['GET'])
@login_required
def print_voter(serial_number):
    """Show a printer-friendly voter record; the browser handles printing."""
    voter = get_voter_by_serial(serial_number)
    if not voter:
        abort(404)
    return render_template('print.html', voter=voter)

@app.route('/preview/<int:serial_number>', methods=['GET'])
@login_required
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
@login_required
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
    app.run(host='127.0.0.1', port=port, debug=False)
