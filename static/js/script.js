/**
 * Haripalem Voter App - Client-side script
 * Entirely in Telugu, handling flexible search, previews, result selection, and printing.
 */

// Error message strings in pure Telugu
const TELUGU_MESSAGES = {
    EMPTY_INPUT: "దయచేసి వరుస సంఖ్య, పేరు లేదా ఓటరు ఐడి నమోదు చేయండి.",
    OUT_OF_RANGE: "ఓటరు వరుస సంఖ్య 1 నుండి 2856 మధ్య మాత్రమే ఉండాలి.",
    NOT_FOUND: "మీ శోధనకు సరిపోయే ఓటరు వివరాలు లభించలేదు.",
    NETWORK_ERROR: "సర్వర్‌తో అనుసంధానం కాలేదు. దయచేసి కాసేపటి తర్వాత మళ్ళీ ప్రయత్నించండి."
};

function showError(message) {
    const errorBox = document.getElementById('errorBox');
    const errorMessage = document.getElementById('errorMessage');
    errorMessage.textContent = message;
    errorBox.style.display = 'flex';
    
    // Hide loading & results if showing
    document.getElementById('loadingBox').style.display = 'none';
    document.getElementById('resultSection').style.display = 'none';
}

function clearError() {
    const errorBox = document.getElementById('errorBox');
    errorBox.style.display = 'none';
    document.getElementById('errorMessage').textContent = '';
}

function handleSearch(event) {
    if (event) {
        event.preventDefault();
    }
    const input = document.getElementById('searchInput');
    const rawVal = input.value.trim();
    
    // 1. Validate empty
    if (!rawVal) {
        showError(TELUGU_MESSAGES.EMPTY_INPUT);
        input.focus();
        return;
    }
    
    if (/^\d+$/.test(rawVal) && (Number(rawVal) < 1 || Number(rawVal) > 2856)) {
        showError(TELUGU_MESSAGES.OUT_OF_RANGE);
        input.focus();
        return;
    }
    
    executeSearch(rawVal);
}

async function executeSearch(query) {
    clearError();
    
    const loadingBox = document.getElementById('loadingBox');
    const resultSection = document.getElementById('resultSection');
    const matchListSection = document.getElementById('matchListSection');
    const searchBtn = document.getElementById('searchBtn');
    
    // Show loading
    loadingBox.style.display = 'block';
    resultSection.style.display = 'none';
    matchListSection.style.display = 'none';
    searchBtn.disabled = true;
    
    try {
        const response = await fetch('/search', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            body: JSON.stringify({ query })
        });
        
        const data = await response.json();
        
        if (!response.ok || !data.success) {
            const msg = data.error || TELUGU_MESSAGES.NOT_FOUND;
            showError(msg);
            return;
        }
        
        if (data.match_type === 'list') {
            displayMatchList(data.voters);
        } else {
            displayResult(data);
        }
        
    } catch (err) {
        console.error('Search error:', err);
        showError(TELUGU_MESSAGES.NETWORK_ERROR);
    } finally {
        loadingBox.style.display = 'none';
        searchBtn.disabled = false;
    }
}

function displayMatchList(voters) {
    const list = document.getElementById('matchList');
    const title = document.getElementById('matchListTitle');
    title.textContent = `${voters.length} సరిపోయే ఓటర్లు లభించారు`;
    list.replaceChildren();

    voters.forEach((voter) => {
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'match-item';
        button.innerHTML = `<strong>${escapeHtml(voter.voter_name || 'పేరు లభ్యం కాలేదు')}</strong>
            <span>వరుస సంఖ్య: ${voter.serial_no} · వార్డు: ${voter.ward_no || '-'}</span>
            <span>${escapeHtml(voter.relative_type || 'బంధువు')} పేరు: ${escapeHtml(voter.relative_name || 'లభ్యం కాలేదు')}</span>`;
        button.addEventListener('click', () => executeSearch(String(voter.serial_no)));
        list.appendChild(button);
    });

    const section = document.getElementById('matchListSection');
    section.style.display = 'block';
    section.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function escapeHtml(value) {
    const div = document.createElement('div');
    div.textContent = String(value);
    return div.innerHTML;
}

function displayResult(data) {
    const voter = data.voter;
    
    // Title
    document.getElementById('resultVoterTitle').textContent = `ఓటరు: ${voter.voter_name || 'నమోదు చేయబడింది'} (వరుస సంఖ్య: ${voter.serial_no})`;
    
    // Image Preview
    const imgEl = document.getElementById('voterEntryImage');
    if (data.preview_image) {
        imgEl.src = data.preview_image;
        imgEl.alt = `ఓటరు వరుస సంఖ్య ${voter.serial_no} అసలు నమోదు ప్రతి`;
    }
    
    // PDF coordinates caption
    document.getElementById('pdfPageNo').textContent = voter.page_no || '-';
    document.getElementById('pdfRowNo').textContent = (voter.row_idx !== undefined ? voter.row_idx + 1 : '-');
    document.getElementById('pdfColNo').textContent = (voter.col_idx !== undefined ? voter.col_idx + 1 : '-');
    
    // Ward Badge
    document.getElementById('wardBadge').textContent = `వార్డు నెంబరు: ${voter.ward_no || '-'}`;
    
    // Table Details
    document.getElementById('detailSerialNo').textContent = voter.serial_no;
    document.getElementById('detailVoterName').textContent = voter.voter_name || 'లభ్యం కాలేదు';
    
    // Relative Label & Name
    const relLabelEl = document.getElementById('detailRelativeLabel');
    if (voter.relative_type) {
        relLabelEl.textContent = `${voter.relative_type} పేరు`;
    } else {
        relLabelEl.textContent = 'తండ్రి / భర్త / తల్లి పేరు';
    }
    document.getElementById('detailRelativeName').textContent = voter.relative_name || 'లభ్యం కాలేదు';
    
    document.getElementById('detailAge').textContent = voter.age ? `${voter.age} సంవత్సరాలు` : 'లభ్యం కాలేదు';
    document.getElementById('detailGender').textContent = voter.gender || 'లభ్యం కాలేదు';
    document.getElementById('detailHouseNo').textContent = voter.house_no || 'లభ్యం కాలేదు';
    document.getElementById('detailVoterId').textContent = voter.voter_id || 'లభ్యం కాలేదు';
    document.getElementById('detailAssemblySerial').textContent = voter.assembly_serial ? `32 - ${voter.assembly_serial}` : (voter.assembly_serial || 'లభ్యం కాలేదు');
    document.getElementById('detailWardNo').textContent = voter.ward_no || '1';
    
    const printUrl = data.print_url || `/print/${voter.serial_no}`;
    document.getElementById('printBtn').href = printUrl;
    document.getElementById('printBtnSecondary').href = printUrl;
    
    // Show Result Section
    const resultSection = document.getElementById('resultSection');
    resultSection.style.display = 'block';
    
    // Scroll smoothly to results
    resultSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
}
