/**
 * Haripalem Voter App - Client-side script
 * Entirely in Telugu, handling search, validation, preview rendering, and downloads.
 */

// Error message strings in pure Telugu
const TELUGU_MESSAGES = {
    EMPTY_INPUT: "దయచేసి ఓటరు వరుస సంఖ్యను నమోదు చేయండి.",
    NOT_A_NUMBER: "దయచేసి సరైన సంఖ్యను నమోదు చేయండి. అక్షరాలు లేదా ప్రత్యేక గుర్తులు అనుమతించబడవు.",
    OUT_OF_RANGE: "ఓటరు వరుస సంఖ్య 1 నుండి 2856 మధ్య మాత్రమే ఉండాలి.",
    NOT_FOUND: "నమోదు చేసిన వరుస సంఖ్యతో ఓటరు వివరాలు లభించలేదు. దయచేసి సంఖ్యను సరిచూసుకోండి.",
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

function quickSearch(num) {
    const input = document.getElementById('serialNumberInput');
    input.value = num;
    executeSearch(num);
}

function handleSearch(event) {
    if (event) {
        event.preventDefault();
    }
    const input = document.getElementById('serialNumberInput');
    const rawVal = input.value.trim();
    
    // 1. Validate empty
    if (!rawVal) {
        showError(TELUGU_MESSAGES.EMPTY_INPUT);
        input.focus();
        return;
    }
    
    // 2. Validate numeric
    const num = Number(rawVal);
    if (!/^\d+$/.test(rawVal) || isNaN(num)) {
        showError(TELUGU_MESSAGES.NOT_A_NUMBER);
        input.focus();
        return;
    }
    
    // 3. Validate range (1 to 2856)
    if (num < 1 || num > 2856) {
        showError(TELUGU_MESSAGES.OUT_OF_RANGE);
        input.focus();
        return;
    }
    
    executeSearch(num);
}

async function executeSearch(serialNo) {
    clearError();
    
    const loadingBox = document.getElementById('loadingBox');
    const resultSection = document.getElementById('resultSection');
    const searchBtn = document.getElementById('searchBtn');
    
    // Show loading
    loadingBox.style.display = 'block';
    resultSection.style.display = 'none';
    searchBtn.disabled = true;
    
    try {
        const response = await fetch('/search', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            body: JSON.stringify({ serial_number: serialNo })
        });
        
        const data = await response.json();
        
        if (!response.ok || !data.success) {
            const msg = data.error || TELUGU_MESSAGES.NOT_FOUND;
            showError(msg);
            return;
        }
        
        // Populate results
        displayResult(data);
        
    } catch (err) {
        console.error('Search error:', err);
        showError(TELUGU_MESSAGES.NETWORK_ERROR);
    } finally {
        loadingBox.style.display = 'none';
        searchBtn.disabled = false;
    }
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
    
    // Download Buttons
    const downloadUrl = data.download_url || `/download/${voter.serial_no}`;
    const btn1 = document.getElementById('downloadPdfBtn');
    const btn2 = document.getElementById('downloadPdfBtnSecondary');
    btn1.href = downloadUrl;
    btn2.href = downloadUrl;
    btn1.setAttribute('download', `haripalem_voter_${voter.serial_no}.pdf`);
    btn2.setAttribute('download', `haripalem_voter_${voter.serial_no}.pdf`);
    
    // Show Result Section
    const resultSection = document.getElementById('resultSection');
    resultSection.style.display = 'block';
    
    // Scroll smoothly to results
    resultSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
}
