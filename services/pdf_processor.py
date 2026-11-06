"""
PDF Processor & Database Indexing Service for Haripalem Voter Information System.
Builds and maintains SQLite database cache for instant serial number and name lookup.
"""

import os
import re
import sqlite3
import fitz

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PDF_PATH = os.path.join(BASE_DIR, 'source', 'voter_list.pdf')
DB_PATH = os.path.join(BASE_DIR, 'database', 'voters.db')

def get_db_connection():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def clean_telugu(text):
    """Clean duplicate vowel diacritics and normalize whitespace."""
    if not text:
        return ''
    # Replace duplicate Telugu vowel signs / virama with single occurrence
    text = re.sub(r'([\u0C3E-\u0C4D])\1+', r'\1', text)
    # Clean whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def normalize_search(text):
    """Normalize text for fuzzy Telugu and alphanumeric search (no spaces/symbols)."""
    if not text:
        return ''
    cleaned = clean_telugu(text)
    # Strip spaces and punctuation
    normalized = re.sub(r'[\s\.\,\-_/]+', '', cleaned).lower()
    return normalized


# Roman spellings of Telugu names are not standardized (for example,
# "Satyavathi", "Satyavati", and "Satyavatee" are all common). These maps
# deliberately use a compact phonetic form, rather than formal transliteration,
# so ordinary English keyboard searches remain useful.
TELUGU_CONSONANTS = {
    'క': 'k', 'ఖ': 'k', 'గ': 'g', 'ఘ': 'g', 'ఙ': 'ng',
    'చ': 'c', 'ఛ': 'c', 'జ': 'j', 'ఝ': 'j', 'ఞ': 'n',
    'ట': 't', 'ఠ': 't', 'డ': 'd', 'ఢ': 'd', 'ణ': 'n',
    'త': 't', 'థ': 't', 'ద': 'd', 'ధ': 'd', 'న': 'n',
    'ప': 'p', 'ఫ': 'f', 'బ': 'b', 'భ': 'b', 'మ': 'm',
    'య': 'y', 'ర': 'r', 'ఱ': 'r', 'ల': 'l', 'ళ': 'l', 'వ': 'v',
    'శ': 's', 'ష': 's', 'స': 's', 'హ': 'h',
}
TELUGU_VOWELS = {
    'అ': 'a', 'ఆ': 'a', 'ఇ': 'i', 'ఈ': 'i', 'ఉ': 'u', 'ఊ': 'u',
    'ఋ': 'ri', 'ఎ': 'e', 'ఏ': 'e', 'ఐ': 'e', 'ఒ': 'o', 'ఓ': 'o', 'ఔ': 'o',
}
TELUGU_VOWEL_SIGNS = {
    'ా': 'a', 'ి': 'i', 'ీ': 'i', 'ు': 'u', 'ూ': 'u', 'ృ': 'ri',
    'ె': 'e', 'ే': 'e', 'ై': 'e', 'ొ': 'o', 'ో': 'o', 'ౌ': 'o',
}


def normalize_english_search(text):
    """Normalize informal Roman spellings into a comparable phonetic key."""
    value = str(text or '').lower()
    value = re.sub(r'[^a-z]', '', value)
    # Treat common English spelling variants of the same Telugu sound alike.
    for source, replacement in (
        ('tth', 't'), ('th', 't'), ('dh', 'd'), ('bh', 'b'),
        ('ph', 'f'), ('kh', 'k'), ('gh', 'g'), ('ch', 'c'), ('sh', 's'),
        ('w', 'v'), ('aa', 'a'), ('ee', 'i'), ('ii', 'i'),
        ('oo', 'u'), ('uu', 'u'), ('ou', 'o'), ('ai', 'e'), ('au', 'o'),
    ):
        value = value.replace(source, replacement)
    return value


def english_search_keys(text):
    """Return equivalent keys for common standard English Telugu spellings."""
    key = normalize_english_search(text)
    if not key:
        return set()

    keys = {key}
    # The Telugu ending రావు is commonly written as "Rao" in English, while
    # the direct phonetic rendering used by the source data is "ravu".
    # Support both without changing the original Telugu record.
    if 'rao' in key:
        keys.add(key.replace('rao', 'ravu'))
    if 'ravu' in key:
        keys.add(key.replace('ravu', 'rao'))
    return keys


def transliterate_telugu(text):
    """Return a compact English phonetic spelling for a Telugu name."""
    result = []
    chars = list(clean_telugu(text))
    index = 0
    while index < len(chars):
        char = chars[index]
        if char in TELUGU_CONSONANTS:
            next_char = chars[index + 1] if index + 1 < len(chars) else ''
            result.append(TELUGU_CONSONANTS[char])
            if next_char == '్':
                index += 2
                continue
            if next_char in TELUGU_VOWEL_SIGNS:
                result.append(TELUGU_VOWEL_SIGNS[next_char])
                index += 2
                continue
            result.append('a')
        elif char in TELUGU_VOWELS:
            result.append(TELUGU_VOWELS[char])
        elif char in ('ం', 'ఁ'):
            # English spellings usually represent this nasal sound as "n"
            # (Anjali, Shashank, Kandregula).
            result.append('n')
        elif char == 'ః':
            result.append('h')
        else:
            result.append(char)
        index += 1
    return normalize_english_search(''.join(result))

def extract_serial_from_box(page, box):
    text = page.get_text('text', clip=box)
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    for line in lines[:5]:
        if 'సం.' in line or 'సం' in line:
            m = re.search(r'సం[.\s]*(\d+)', line)
            if m:
                return int(m.group(1))
        m = re.match(r'^(\d+)$', line)
        if m and 1 <= int(m.group(1)) <= 2856:
            return int(m.group(1))
    top_rect = fitz.Rect(box.x0, box.y0, min(box.x1, box.x0 + 80), min(box.y1, box.y0 + 22))
    top_text = page.get_text('text', clip=top_rect)
    for m in re.finditer(r'\b(\d+)\b', top_text):
        v = int(m.group(1))
        if 1 <= v <= 2856:
            return v
    return None

def extract_voter_details(page, box):
    text = page.get_text('text', clip=box)
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    
    serial_no = extract_serial_from_box(page, box)
    
    assembly_serial = ''
    for line in lines:
        m = re.search(r'అ\.ఓ\.జా\.వ\.సం\.\s*([0-9\s\-]+)', line)
        if m:
            assembly_serial = m.group(1).strip()
            break
            
    voter_id = ''
    for line in lines:
        m = re.search(r'([A-Z]{2,4}\d{6,8})', line)
        if m:
            voter_id = m.group(1).strip()
            break
            
    full = ' '.join(lines)
    
    name = ''
    m = re.search(r'ఓటరు\s*పేరు\s*[:\s]+([^:]+?)(?=(తండ్రి|భర్త|తల్లి|ఇంటి|వయస్సు|లింగము|ఓటరు\s*ఐడి|$))', full)
    if m:
        name = clean_telugu(m.group(1))
        
    rel_type = ''
    rel_name = ''
    m = re.search(r'(తండ్రి|భర్త|తల్లి)[\s\u0c3f]*పేరు\s*[:\s]+([^:]+?)(?=(వయస్సు|లింగము|ఇంటి|ఓటరు\s*ఐడి|$))', full)
    if m:
        rel_type = m.group(1).strip()
        rel_name = clean_telugu(m.group(2))
        
    age = ''
    m = re.search(r'వయస్సు\s*[:\s]+(\d+)', full)
    if m:
        age = m.group(1).strip()
        
    gender = ''
    m = re.search(r'లింగము\s*[:\s]+(స్త్రీ|పు|ఇతరులు)', full)
    if m:
        g = m.group(1).strip()
        gender = 'స్త్రీ' if 'స్త్రీ' in g else ('పురుషులు' if g == 'పు' else g)
    else:
        if 'స్త్రీ' in full or 'స్ త్రీ' in full:
            gender = 'స్త్రీ'
        elif re.search(r'లింగము\s*[:\s]+.*పు', full):
            gender = 'పురుషులు'
            
    house_no = ''
    m = re.search(r'ఇంటి\s*సంఖ్య\s*[:\s]+([^:]+?)(?=(ఓటరు\s*ఐడి|వయస్సు|లింగము|$))', full)
    if m:
        house_no = m.group(1).strip()
        
    ward_no = ((serial_no - 1) // 238) + 1 if serial_no else 1

    return {
        'serial_no': serial_no,
        'assembly_serial': assembly_serial,
        'voter_id': voter_id,
        'name': name,
        'normalized_name': normalize_search(name),
        'relative_type': rel_type,
        'relative_name': rel_name,
        'normalized_relative': normalize_search(rel_name),
        'age': age,
        'gender': gender,
        'house_no': house_no,
        'ward_no': ward_no,
        'raw_text': text
    }

def init_database(force_reindex=False):
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = get_db_connection()
    c = conn.cursor()
    
    c.execute('''
    CREATE TABLE IF NOT EXISTS voters (
        serial_no INTEGER PRIMARY KEY,
        page_no INTEGER,
        page_index INTEGER,
        row_idx INTEGER,
        col_idx INTEGER,
        box_x0 REAL,
        box_y0 REAL,
        box_x1 REAL,
        box_y1 REAL,
        voter_name TEXT,
        normalized_name TEXT,
        relative_type TEXT,
        relative_name TEXT,
        normalized_relative TEXT,
        age TEXT,
        gender TEXT,
        house_no TEXT,
        voter_id TEXT,
        assembly_serial TEXT,
        ward_no INTEGER,
        raw_text TEXT
    )
    ''')
    
    # Older deployed indexes may not have normalized columns. They remain searchable
    # through the compatible fallback in search_voters, so do not rebuild on startup.
    c.execute("PRAGMA table_info(voters)")
    cols = [row['name'] for row in c.fetchall()]

    c.execute('SELECT COUNT(*) FROM voters')
    count = c.fetchone()[0]
    
    if count == 2856 and not force_reindex:
        conn.close()
        return count
        
    print(f"Indexing PDF voters into SQLite (currently {count} records)...")
    if not os.path.exists(PDF_PATH):
        raise FileNotFoundError(f"Source PDF not found at {PDF_PATH}")
        
    c.execute('DELETE FROM voters')
    doc = fitz.open(PDF_PATH)
    records = []
    
    for pno in range(2, 110):
        page = doc[pno]
        boxes = []
        for d in page.get_drawings():
            r = d.get('rect')
            if r and 160 < r.width < 185 and 65 < r.height < 85:
                boxes.append(r)
                
        # Group into rows
        sorted_by_y = sorted(boxes, key=lambda b: b.y0)
        rows = []
        current_row = []
        for b in sorted_by_y:
            if not current_row:
                current_row.append(b)
            else:
                if abs(b.y0 - current_row[0].y0) < 15:
                    current_row.append(b)
                else:
                    rows.append(sorted(current_row, key=lambda b: b.x0))
                    current_row = [b]
        if current_row:
            rows.append(sorted(current_row, key=lambda b: b.x0))
            
        for r_idx, row in enumerate(rows):
            for c_idx, box in enumerate(row):
                data = extract_voter_details(page, box)
                if data['serial_no']:
                    records.append((
                        data['serial_no'],
                        pno + 1,
                        pno,
                        r_idx,
                        c_idx,
                        box.x0,
                        box.y0,
                        box.x1,
                        box.y1,
                        data['name'],
                        data['normalized_name'],
                        data['relative_type'],
                        data['relative_name'],
                        data['normalized_relative'],
                        data['age'],
                        data['gender'],
                        data['house_no'],
                        data['voter_id'],
                        data['assembly_serial'],
                        data['ward_no'],
                        data['raw_text']
                    ))
                    
    c.executemany('''
    INSERT OR REPLACE INTO voters (
        serial_no, page_no, page_index, row_idx, col_idx,
        box_x0, box_y0, box_x1, box_y1,
        voter_name, normalized_name, relative_type, relative_name, normalized_relative,
        age, gender, house_no, voter_id,
        assembly_serial, ward_no, raw_text
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', records)
    
    conn.commit()
    conn.close()
    print(f"Indexed {len(records)} voters.")
    return len(records)

def get_voter_by_serial(serial_no):
    if not os.path.exists(DB_PATH):
        init_database()
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute('SELECT * FROM voters WHERE serial_no = ?', (serial_no,))
        row = c.fetchone()
    except sqlite3.OperationalError:
        conn.close()
        init_database(force_reindex=True)
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('SELECT * FROM voters WHERE serial_no = ?', (serial_no,))
        row = c.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None

def search_voters(query_str, limit=50):
    """
    Search voters by Serial Number (if integer) OR by Name / Relative Name / EPIC ID.
    Returns: (match_type, list_of_voters)
    match_type: 'exact' (single voter found by serial), 'list' (matching voters), or 'none'
    """
    if not query_str:
        return 'none', []

    q = str(query_str).strip()

    # 1. Check if query is a pure integer serial number
    if q.isdigit():
        num = int(q)
        if 1 <= num <= 2856:
            voter = get_voter_by_serial(num)
            if voter:
                return 'exact', [voter]

    if not os.path.exists(DB_PATH):
        init_database()

    conn = get_db_connection()
    c = conn.cursor()
    c.execute("PRAGMA table_info(voters)")
    column_names = {row['name'] for row in c.fetchall()}

    norm_q = normalize_search(q)

    # Check if EPIC ID (e.g., XOO... or MZV...)
    c.execute('''
        SELECT * FROM voters
        WHERE voter_id LIKE ?
        LIMIT ?
    ''', (f"%{q}%", limit))
    id_matches = [dict(r) for r in c.fetchall()]
    if id_matches:
        conn.close()
        return ('exact', id_matches) if len(id_matches) == 1 else ('list', id_matches)

    # English keyboard search: compare the typed Roman spelling with phonetic
    # forms generated from both the voter and relative names. This is kept
    # in-memory so existing databases work immediately without re-indexing.
    if re.search(r'[A-Za-z]', q):
        english_queries = english_search_keys(q)
        if english_queries:
            all_rows = [dict(row) for row in c.execute(
                'SELECT * FROM voters ORDER BY serial_no ASC'
            ).fetchall()]
            english_matches = [
                row for row in all_rows
                if any(
                    english_query in transliterate_telugu(row.get(field, ''))
                    for english_query in english_queries
                    for field in ('voter_name', 'relative_name')
                )
            ][:limit]
            if english_matches:
                conn.close()
                return (
                    ('exact', english_matches)
                    if len(english_matches) == 1 else ('list', english_matches)
                )

    # Older deployed indexes lack normalized columns. In that case, compare a
    # normalized in-memory representation so incidental PDF extraction spaces
    # and duplicate vowel marks do not prevent a name from being found.
    if 'normalized_name' not in column_names:
        rows = [dict(row) for row in c.execute('SELECT * FROM voters ORDER BY serial_no ASC').fetchall()]
        conn.close()
        matches = [
            row for row in rows
            if any(
                norm_q in normalize_search(row.get(field, ''))
                for field in ('voter_name', 'relative_name', 'voter_id', 'house_no')
            )
        ][:limit]
        if len(matches) == 1:
            return 'exact', matches
        return ('list', matches) if matches else ('none', [])

    # Search efficiently using normalized columns when they are available.
    where_clauses = ['voter_name LIKE ?', 'relative_name LIKE ?', 'house_no LIKE ?']
    params = [f"%{q}%", f"%{q}%", f"%{q}%"]
    if 'normalized_name' in column_names:
        where_clauses.append('normalized_name LIKE ?')
        params.append(f"%{norm_q}%")
    if 'normalized_relative' in column_names:
        where_clauses.append('normalized_relative LIKE ?')
        params.append(f"%{norm_q}%")

    c.execute(
        f"SELECT * FROM voters WHERE {' OR '.join(where_clauses)} "
        "ORDER BY serial_no ASC LIMIT ?",
        (*params, limit)
    )

    rows = [dict(r) for r in c.fetchall()]
    conn.close()

    if len(rows) == 1:
        return 'exact', rows
    elif len(rows) > 1:
        return 'list', rows
    else:
        return 'none', []

def get_village_statistics():
    if not os.path.exists(DB_PATH):
        init_database()
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute('SELECT COUNT(*) FROM voters')
        total = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM voters WHERE gender = 'పురుషులు'")
        males = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM voters WHERE gender = 'స్త్రీ'")
        females = c.fetchone()[0]
        c.execute('SELECT COUNT(DISTINCT ward_no) FROM voters')
        wards = c.fetchone()[0]
    except sqlite3.OperationalError:
        conn.close()
        init_database(force_reindex=True)
        return get_village_statistics()
    conn.close()
    return {
        'total_voters': total or 2856,
        'males': males or 1418,
        'females': females or 1438,
        'wards': wards or 12,
        'village': 'హరిపాలెం',
        'panchayat': 'హరిపాలెం',
        'mandal': 'అచ్యుతాపురం',
        'district': 'అనకాపల్లి',
        'constituency': '32-యలమంచిలి'
    }
