const API_BASE = "/api";

// DOM Elements
const dropZone = document.getElementById('drop-zone');
const fileInput = document.getElementById('file-input');
const uploadStatus = document.getElementById('upload-status');
const heroSection = document.getElementById('hero');
const dashboardSection = document.getElementById('dashboard');

const bookTitle = document.getElementById('book-title');
const bookAuthor = document.getElementById('book-author');
const entitiesList = document.getElementById('entities-list');
const storyContainer = document.getElementById('story-container'); // Note: This might be unused in new layout if we don't show text
const imageDisplay = document.getElementById('image-display');

const btnAudio = document.getElementById('btn-audio');
const btnVisuals = document.getElementById('btn-visuals');
const audioPlayer = document.getElementById('audio-player');

// New Audio UI Elements
const btnPlayPause = document.getElementById('btn-play-pause');
const audioProgress = document.getElementById('audio-progress');
const timeDisplay = document.querySelector('.time-display');

// State
let currentStoryText = "";
let isPlaying = false;

// Event Listeners
dropZone.addEventListener('click', () => fileInput.click());
dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.style.borderColor = '#00d4ff';
});
dropZone.addEventListener('dragleave', () => {
    dropZone.style.borderColor = 'rgba(255, 255, 255, 0.2)';
});
dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.style.borderColor = 'rgba(255, 255, 255, 0.2)';
    if (e.dataTransfer.files.length) {
        handleUpload(e.dataTransfer.files[0]);
    }
});

fileInput.addEventListener('change', (e) => {
    if (e.target.files.length) {
        handleUpload(e.target.files[0]);
    }
});

// Audio Player Events
audioPlayer.addEventListener('timeupdate', updateProgress);
audioPlayer.addEventListener('ended', () => {
    isPlaying = false;
    btnPlayPause.textContent = "▶";
});

// Q&A Events
function setupQA() {
    document.querySelectorAll('.chip').forEach(chip => {
        chip.addEventListener('click', () => {
            const question = chip.textContent;
            document.querySelector('.qa-input').value = question;
            askQuestion(question);
        });
    });
}

document.querySelector('.btn-send').addEventListener('click', () => {
    const question = document.querySelector('.qa-input').value;
    if (question) {
        askQuestion(question);
    }
});

async function askQuestion(question) {
    const answerBox = document.getElementById('qa-answer');
    const answerText = document.getElementById('qa-text');

    answerBox.classList.remove('hidden');
    answerText.textContent = "Thinking...";

    try {
        const res = await fetch(`${API_BASE}/qa`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ question: question })
        });

        if (!res.ok) throw new Error("Failed to get answer");

        const data = await res.json();
        answerText.textContent = data.answer;

    } catch (e) {
        answerText.textContent = "Error: " + e.message;
    }
}

async function fetchSuggestedQuestions() {
    try {
        const res = await fetch(`${API_BASE}/suggested_questions`);
        const data = await res.json();

        if (data.questions && data.questions.length > 0) {
            const chipsContainer = document.querySelector('.qa-suggestions');
            chipsContainer.innerHTML = '';

            data.questions.forEach(q => {
                const chip = document.createElement('span');
                chip.className = 'chip';
                chip.textContent = q;
                chipsContainer.appendChild(chip);
            });

            // Re-bind events
            setupQA();
        }
    } catch (e) {
        console.error("Failed to fetch suggested questions", e);
    }
}

// Functions

async function handleUpload(file) {
    // UI Update
    dropZone.classList.add('hidden');
    uploadStatus.classList.remove('hidden');

    const formData = new FormData();
    formData.append('file', file);

    try {
        const response = await fetch(`${API_BASE}/upload`, {
            method: 'POST',
            body: formData
        });

        if (!response.ok) throw new Error("Upload failed");

        const data = await response.json();

        // Transition to Dashboard
        loadDashboard(data);

    } catch (error) {
        console.error(error);
        alert("Error uploading file: " + error.message);
        dropZone.classList.remove('hidden');
        uploadStatus.classList.add('hidden');
    }
}

function loadDashboard(data) {
    heroSection.classList.add('hidden');
    dashboardSection.classList.remove('hidden');

    // Set Info
    bookTitle.textContent = data.title || "Unknown Title";
    bookAuthor.textContent = data.author || "Unknown Author";

    // Set Story
    currentStoryText = data.analysis.summary || "No summary available.";
    // We might not need to fetch story content if we aren't displaying text anymore, 
    // but keeping it for audio generation context.
    fetchStoryContent();

    // Set Entities
    renderEntities(data.analysis.entities);

    // Fetch Suggested Questions
    fetchSuggestedQuestions();
}

async function fetchStoryContent() {
    try {
        const res = await fetch(`${API_BASE}/story`);
        const data = await res.json();
        currentStoryText = data.body;
    } catch (e) {
        console.error("Failed to fetch story", e);
    }
}

function safeId(name) {
    return `img-${name.replace(/[^a-zA-Z0-9]/g, '')}`;
}

function renderEntities(entities) {
    entitiesList.innerHTML = '';
    entities.forEach(ent => {
        // Handle both list and string formats
        let name, role;
        if (Array.isArray(ent)) {
            name = ent[0];
            role = ent[1] || "Character";
        } else {
            name = ent;
            role = "Character";
        }

        const card = document.createElement('div');
        card.className = 'entity-card';
        const imgId = safeId(name);

        card.innerHTML = `
            <img src="https://ui-avatars.com/api/?name=${encodeURIComponent(name)}&background=random" class="entity-img" id="${imgId}">
            <div>
                <div style="font-weight:bold">${name}</div>
                <div style="font-size:0.8rem; opacity:0.7">${role}</div>
            </div>
        `;
        entitiesList.appendChild(card);

        // Lazy load real image
        fetchEntityImage(name, imgId);
    });
}

async function fetchEntityImage(name, imgId) {
    try {
        const res = await fetch(`${API_BASE}/entity_image/${encodeURIComponent(name)}`);
        const data = await res.json();
        if (data.image_url) {
            const img = document.getElementById(imgId);
            if (img) {
                // Add timestamp to force reload
                img.src = `${data.image_url}?t=${new Date().getTime()}`;
            } else {
                console.warn(`Image element ${imgId} not found`);
            }
        }
    } catch (e) {
        console.error("Entity image error", e);
    }
}

async function generateAudio() {
    const btn = btnAudio;
    const originalText = btn.textContent;
    btn.textContent = "Generating...";
    btn.disabled = true;

    const voiceId = document.getElementById('voice-id-input').value;
    const stability = parseFloat(document.getElementById('stability-range').value);
    const similarity = parseFloat(document.getElementById('similarity-range').value);
    const style = parseFloat(document.getElementById('style-range').value);
    const speakerBoost = document.getElementById('speaker-boost-check').checked;

    try {
        const res = await fetch(`${API_BASE}/generate/audio`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                text: currentStoryText,
                voice_id: voiceId,
                stability: stability,
                similarity_boost: similarity,
                style: style,
                use_speaker_boost: speakerBoost
            })
        });

        if (!res.ok) throw new Error("Audio generation failed");

        const data = await res.json();
        audioPlayer.src = data.audio_url;
        // Auto play
        toggleAudio();

    } catch (e) {
        alert(e.message);
    } finally {
        btn.textContent = originalText;
        btn.disabled = false;
    }
}

async function generateVisuals() {
    const btn = btnVisuals;
    const originalText = btn.textContent;
    btn.textContent = "Painting...";
    btn.disabled = true;

    const style = document.getElementById('style-select').value;

    try {
        const res = await fetch(`${API_BASE}/generate/visuals`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                style: style,
                seed: 42
            })
        });

        if (!res.ok) throw new Error("Visuals generation failed");

        const data = await res.json();
        injectImages(data.images);

    } catch (e) {
        alert(e.message);
    } finally {
        btn.textContent = originalText;
        btn.disabled = false;
    }
}

function injectImages(images) {
    imageDisplay.innerHTML = '';

    if (images && images.length > 0) {
        images.forEach((imgUrl, index) => {
            const card = document.createElement('div');
            card.className = 'image-card';
            // First image is title page
            if (index === 0) {
                card.classList.add('title-page');
            }

            const img = document.createElement('img');
            img.src = imgUrl;
            img.className = 'generated-img';
            img.alt = index === 0 ? "Title Page" : `Scene ${index}`;

            card.appendChild(img);
            imageDisplay.appendChild(card);
        });
    } else {
        imageDisplay.innerHTML = '<div class="placeholder-text">No images generated.</div>';
    }
}

// Audio Controls
function toggleAudio() {
    if (audioPlayer.paused) {
        audioPlayer.play();
        isPlaying = true;
        btnPlayPause.textContent = "⏸";
    } else {
        audioPlayer.pause();
        isPlaying = false;
        btnPlayPause.textContent = "▶";
    }
}

function skip(seconds) {
    audioPlayer.currentTime += seconds;
}

function updateProgress() {
    const percent = (audioPlayer.currentTime / audioPlayer.duration) * 100;
    audioProgress.style.width = `${percent}%`;

    const current = formatTime(audioPlayer.currentTime);
    const total = formatTime(audioPlayer.duration || 0);
    timeDisplay.textContent = `${current} / ${total}`;
}

function formatTime(seconds) {
    const min = Math.floor(seconds / 60);
    const sec = Math.floor(seconds % 60);
    return `${min}:${sec < 10 ? '0' : ''}${sec}`;
}

// Bind buttons
btnAudio.addEventListener('click', generateAudio);
btnVisuals.addEventListener('click', generateVisuals);
