const API_BASE = "/api";

// DOM Elements
const dropZone = document.getElementById('drop-zone');
const fileInput = document.getElementById('file-input');
const uploadStatus = document.getElementById('upload-status');
const statusDetail = document.getElementById('status-detail');
const heroSection = document.getElementById('hero');
const dashboardSection = document.getElementById('dashboard');

const bookTitle = document.getElementById('book-title');
const bookAuthor = document.getElementById('book-author');
const entitiesList = document.getElementById('entities-list');
const entityCount = document.getElementById('entity-count');
const imageDisplay = document.getElementById('image-display');

const btnAudio = document.getElementById('btn-audio');
const btnVisuals = document.getElementById('btn-visuals');
const audioPlayer = document.getElementById('audio-player');
const audioVisualizer = document.querySelector('.audio-visualizer');
const chatbotFab = document.getElementById('chatbot-fab');

// Audio UI
const btnPlayPause = document.getElementById('btn-play-pause');
const audioProgress = document.getElementById('audio-progress');
const progressContainer = document.getElementById('progress-container');
const currentTimeEl = document.getElementById('current-time');
const totalTimeEl = document.getElementById('total-time');

// QA UI
const qaInput = document.getElementById('qa-input');
const btnSendQa = document.getElementById('btn-send-qa');
const qaChatContainer = document.getElementById('qa-chat-container');
const qaSuggestions = document.getElementById('qa-suggestions');

// State
let currentStoryText = "";
let isPlaying = false;
let audioDuration = 0;

// Default Settings
const DEFAULT_SETTINGS = {
    voiceId: "21m00Tcm4TlvDq8ikWAM",
    stability: 0.5,
    similarity: 0.75,
    styleStrength: 0.0,
    speakerBoost: false
};

// --- Initialization ---

function init() {
    setupEventListeners();
    // Initialize settings if not present
    if (!localStorage.getItem('b2v_settings')) {
        localStorage.setItem('b2v_settings', JSON.stringify(DEFAULT_SETTINGS));
    }
}

function setupEventListeners() {
    // Upload
    if (dropZone) {
        dropZone.addEventListener('click', () => fileInput.click());
        dropZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            dropZone.classList.add('dragover');
        });
        dropZone.addEventListener('dragleave', () => {
            dropZone.classList.remove('dragover');
        });
        dropZone.addEventListener('drop', (e) => {
            e.preventDefault();
            dropZone.classList.remove('dragover');
            if (e.dataTransfer.files.length) {
                handleUpload(e.dataTransfer.files[0]);
            }
        });
    }

    if (fileInput) {
        fileInput.addEventListener('change', (e) => {
            if (e.target.files.length) {
                handleUpload(e.target.files[0]);
            }
        });
    }

    // Audio
    if (btnAudio) btnAudio.addEventListener('click', generateAudio);
    if (btnPlayPause) btnPlayPause.addEventListener('click', toggleAudio);
    if (audioPlayer) {
        audioPlayer.addEventListener('timeupdate', updateProgress);
        audioPlayer.addEventListener('loadedmetadata', () => {
            audioDuration = audioPlayer.duration;
            totalTimeEl.textContent = formatTime(audioDuration);
        });
        audioPlayer.addEventListener('ended', () => {
            isPlaying = false;
            btnPlayPause.textContent = "▶";
            document.querySelector('.audio-player-ui').classList.remove('playing');
        });
    }

    // Skip Buttons
    const btnSkipBack = document.getElementById('btn-skip-back');
    const btnSkipFwd = document.getElementById('btn-skip-fwd');
    if (btnSkipBack) btnSkipBack.addEventListener('click', () => skip(-15));
    if (btnSkipFwd) btnSkipFwd.addEventListener('click', () => skip(15));

    if (progressContainer) {
        progressContainer.addEventListener('click', (e) => {
            const rect = progressContainer.getBoundingClientRect();
            const percent = (e.clientX - rect.left) / rect.width;
            audioPlayer.currentTime = percent * audioDuration;
        });
    }

    // Visuals
    if (btnVisuals) btnVisuals.addEventListener('click', generateVisuals);

    // QA
    if (btnSendQa) btnSendQa.addEventListener('click', handleQASubmit);
    if (qaInput) {
        qaInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') handleQASubmit();
        });
    }
}

// --- Settings Management ---

function getSettings() {
    const saved = localStorage.getItem('b2v_settings');
    return saved ? { ...DEFAULT_SETTINGS, ...JSON.parse(saved) } : DEFAULT_SETTINGS;
}

function saveSettings(newSettings) {
    const current = getSettings();
    const updated = { ...current, ...newSettings };
    localStorage.setItem('b2v_settings', JSON.stringify(updated));
    return updated;
}

// --- Core Logic ---

async function handleUpload(file) {
    // Validate file type
    const validTypes = ['.pdf', '.epub', '.txt'];
    const ext = file.name.substring(file.name.lastIndexOf('.')).toLowerCase();
    if (!validTypes.includes(ext)) {
        showToast("Invalid file type. Please upload PDF, EPUB, or TXT.", "error");
        return;
    }

    // UI Update
    dropZone.classList.add('hidden');
    uploadStatus.classList.remove('hidden');

    const formData = new FormData();
    formData.append('file', file);

    try {
        statusDetail.textContent = "Uploading and ingesting book...";
        const response = await fetch(`${API_BASE}/upload`, {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || "Upload failed");
        }

        statusDetail.textContent = "Analyzing content and characters...";
        const data = await response.json();

        showToast("Book uploaded successfully!", "success");
        loadDashboard(data, file.name);

    } catch (error) {
        console.error(error);
        showToast(error.message, "error");
        dropZone.classList.remove('hidden');
        uploadStatus.classList.add('hidden');
    }
}

function loadDashboard(data, filename) {
    heroSection.classList.add('hidden');
    dashboardSection.classList.remove('hidden');

    const fab = document.getElementById('chatbot-fab');
    if (fab) {
        fab.classList.remove('hidden');
        fab.style.display = 'flex'; // Force display
        fab.style.zIndex = '9999'; // Force z-index
    }

    // Set Info
    bookTitle.textContent = filename || data.title || "Unknown Title";
    bookAuthor.textContent = data.author || "Unknown Author";

    // Store context
    currentStoryText = data.analysis.summary || "";

    // Render Entities
    renderEntities(data.analysis.entities);

    // Fetch Suggested Questions
    fetchSuggestedQuestions();

    // Fetch full story text (background)
    fetchStoryContent();
}

async function fetchStoryContent() {
    try {
        const res = await fetch(`${API_BASE}/story`);
        const data = await res.json();
        currentStoryText = data.body; // Update with full text for better audio/QA
    } catch (e) {
        console.warn("Failed to fetch full story text, using summary.");
    }
}

function renderEntities(entities) {
    entitiesList.innerHTML = '';

    if (!entities || entities.length === 0) {
        entitiesList.innerHTML = '<div class="placeholder-text">No characters found.</div>';
        entityCount.textContent = "0";
        return;
    }

    entityCount.textContent = entities.length;

    entities.forEach(ent => {
        let name, role;
        if (Array.isArray(ent)) {
            name = ent[0];
            role = ent[1] || "Character";
        } else {
            name = ent;
            role = "Character";
        }

        const card = document.createElement('div');
        card.className = 'entity-card fade-in-element'; // Added animation class
        const imgId = `img-${name.replace(/[^a-zA-Z0-9]/g, '')}`;

        card.innerHTML = `
            <img src="https://ui-avatars.com/api/?name=${encodeURIComponent(name)}&background=random" class="entity-img" id="${imgId}">
            <div>
                <div style="font-weight:600">${name}</div>
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
        // Add regenerate param if needed, logic can be extended
        const res = await fetch(`${API_BASE}/entity_image/${encodeURIComponent(name)}`);
        const data = await res.json();
        if (data.image_url) {
            const img = document.getElementById(imgId);
            if (img) {
                // The backend now adds a timestamp, but we can add one here too just in case
                img.src = data.image_url;
            }
        }
    } catch (e) {
        // Silent fail for entity images
    }
}

// --- Audio ---

async function generateAudio() {
    if (!currentStoryText) {
        showToast("No text available to generate audio.", "error");
        return;
    }

    const originalText = btnAudio.innerHTML;
    btnAudio.innerHTML = '<span class="icon">⏳</span> Generating...';
    btnAudio.disabled = true;

    // Get settings from localStorage
    const settings = getSettings();
    const provider = document.getElementById('audio-provider').value;

    try {
        const res = await fetch(`${API_BASE}/generate/audio`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                text: currentStoryText,
                voice_id: settings.voiceId,
                stability: settings.stability,
                similarity_boost: settings.similarity,
                provider: provider
            })
        });

        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || "Audio generation failed");
        }

        const data = await res.json();
        audioPlayer.src = data.audio_url;
        audioPlayer.load(); // Ensure it loads

        showToast("Audio generated successfully!", "success");

        // Auto play when ready
        audioPlayer.oncanplay = () => {
            toggleAudio();
            audioPlayer.oncanplay = null; // Remove listener
        };

    } catch (e) {
        showToast(e.message, "error");
    } finally {
        btnAudio.innerHTML = originalText;
        btnAudio.disabled = false;
    }
}

function toggleAudio() {
    const ui = document.querySelector('.audio-player-ui');

    if (!audioPlayer.src || audioPlayer.src === window.location.href) {
        showToast("Please generate audio first.", "info");
        return;
    }

    if (audioPlayer.paused) {
        const playPromise = audioPlayer.play();
        if (playPromise !== undefined) {
            playPromise.then(() => {
                isPlaying = true;
                btnPlayPause.textContent = "⏸";
                ui.classList.add('playing');
            }).catch(e => {
                if (e.name === 'AbortError') {
                    // Ignore abort errors caused by rapid pausing
                    console.log("Play interrupted by pause");
                } else {
                    console.error("Play failed:", e);
                    showToast("Could not play audio. " + e.message, "error");
                }
            });
        }
    } else {
        audioPlayer.pause();
        isPlaying = false;
        btnPlayPause.textContent = "▶";
        ui.classList.remove('playing');
    }
}

function skip(seconds) {
    audioPlayer.currentTime += seconds;
}

function updateProgress() {
    const percent = (audioPlayer.currentTime / audioPlayer.duration) * 100;
    audioProgress.style.width = `${percent}%`;
    currentTimeEl.textContent = formatTime(audioPlayer.currentTime);
}

function formatTime(seconds) {
    if (isNaN(seconds)) return "0:00";
    const min = Math.floor(seconds / 60);
    const sec = Math.floor(seconds % 60);
    return `${min}:${sec < 10 ? '0' : ''}${sec}`;
}

// --- Visuals ---

async function generateVisuals() {
    const originalText = btnVisuals.innerHTML;
    btnVisuals.innerHTML = '<span class="icon">⏳</span> Requesting...';
    btnVisuals.disabled = true;

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

        // Immediate feedback: Inject placeholders
        injectImages(data.images, true);
        showToast("Generation started! Images will appear one by one.", "success");

    } catch (e) {
        showToast(e.message, "error");
    } finally {
        btnVisuals.innerHTML = originalText;
        btnVisuals.disabled = false;
    }
}

function injectImages(images, isAsync = false) {
    imageDisplay.innerHTML = '';

    if (images && images.length > 0) {
        images.forEach((imgUrl, index) => {
            const wrapper = document.createElement('div');
            wrapper.className = 'image-wrapper';

            const img = document.createElement('img');
            // Add timestamp to prevent caching of old failed attempts if any
            img.dataset.src = imgUrl;
            img.src = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 1 1'%3E%3C/svg%3E"; // Transparent placeholder
            img.className = 'generated-img placeholder';
            img.alt = `Scene ${index}`;

            // Loading spinner
            const spinner = document.createElement('div');
            spinner.className = 'loading-spinner';
            spinner.innerHTML = '🎨';

            wrapper.appendChild(img);
            wrapper.appendChild(spinner);
            imageDisplay.appendChild(wrapper);

            // Start polling for this image
            pollForImage(img, imgUrl, spinner);
        });
    } else {
        imageDisplay.innerHTML = '<div class="placeholder-content"><p>No images generated.</p></div>';
    }
}

function pollForImage(imgElement, url, spinner, attempts = 0) {
    const maxAttempts = 60; // 2 minutes approx (2s interval)

    const img = new Image();
    img.onload = () => {
        imgElement.src = url;
        imgElement.classList.remove('placeholder');
        imgElement.classList.add('loaded', 'fade-in-image');
        if (spinner) spinner.remove();
    };
    img.onerror = () => {
        if (attempts < maxAttempts) {
            setTimeout(() => pollForImage(imgElement, url, spinner, attempts + 1), 2000);
        } else {
            if (spinner) {
                spinner.innerHTML = '❌';
                spinner.title = "Failed to load";
            }
        }
    };
    // Add cache buster to check if file exists on server yet
    img.src = `${url}?t=${Date.now()}`;
}

// --- Q&A ---

async function handleQASubmit() {
    const question = qaInput.value.trim();
    if (!question) return;

    addChatMessage(question, 'user');
    qaInput.value = '';

    // Show loading state
    const loadingId = addChatMessage("Thinking...", 'ai');

    try {
        // Add timeout to fetch
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 40000); // 40s timeout for frontend

        const res = await fetch(`${API_BASE}/qa`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ question: question }),
            signal: controller.signal
        });

        clearTimeout(timeoutId);

        if (!res.ok) throw new Error("Failed to get answer");

        const data = await res.json();

        // Remove loading message and add real answer
        const loadingMsg = document.getElementById(loadingId);
        if (loadingMsg) loadingMsg.remove();

        addChatMessage(data.answer, 'ai');

    } catch (e) {
        const loadingMsg = document.getElementById(loadingId);
        if (loadingMsg) loadingMsg.remove();

        let errorMsg = "Sorry, I couldn't answer that.";
        if (e.name === 'AbortError') {
            errorMsg = "Sorry, the request timed out. Please try again.";
        } else {
            errorMsg += " " + e.message;
        }
        addChatMessage(errorMsg, 'ai');
    }
}

let msgCounter = 0;
function addChatMessage(text, type) {
    const msg = document.createElement('div');
    msg.className = `chat-message ${type} fade-in-element`; // Added animation
    msg.textContent = text;
    const id = 'msg-' + Date.now() + '-' + (msgCounter++);
    msg.id = id;

    qaChatContainer.appendChild(msg);

    // Smooth scroll to bottom
    requestAnimationFrame(() => {
        qaChatContainer.scrollTo({
            top: qaChatContainer.scrollHeight,
            behavior: 'smooth'
        });
    });

    return id;
}

async function fetchSuggestedQuestions() {
    try {
        const res = await fetch(`${API_BASE}/suggested_questions`);
        const data = await res.json();

        if (data.questions && data.questions.length > 0) {
            qaSuggestions.innerHTML = '';
            data.questions.forEach(q => {
                const chip = document.createElement('span');
                chip.className = 'chip fade-in-element';
                chip.textContent = q;
                chip.onclick = () => {
                    qaInput.value = q;
                    handleQASubmit();
                };
                qaSuggestions.appendChild(chip);
            });
        }
    } catch (e) {
        console.error("Failed to fetch suggestions", e);
    }
}

// --- Utilities ---

function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;

    let icon = 'ℹ️';
    if (type === 'success') icon = '✅';
    if (type === 'error') icon = '❌';

    toast.innerHTML = `<span>${icon}</span> <span>${message}</span>`;

    container.appendChild(toast);

    // Auto remove
    setTimeout(() => {
        toast.style.animation = 'slideIn 0.3s ease reverse forwards';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

function toggleSettings() {
    // Navigate to settings page instead of toggling panel
    window.location.href = 'settings.html';
}

// --- Settings Page Specifics ---
function loadSettingsUI() {
    const settings = getSettings();

    const voiceId = document.getElementById('voice-id');
    if (voiceId) voiceId.value = settings.voiceId;

    const stability = document.getElementById('stability');
    if (stability) {
        stability.value = settings.stability;
        document.getElementById('stability-val').textContent = settings.stability;
    }

    const similarity = document.getElementById('similarity');
    if (similarity) {
        similarity.value = settings.similarity;
        document.getElementById('similarity-val').textContent = settings.similarity;
    }

    const style = document.getElementById('style');
    if (style) {
        style.value = settings.styleStrength;
        document.getElementById('style-val').textContent = settings.styleStrength;
    }

    const speakerBoost = document.getElementById('speaker-boost');
    if (speakerBoost) speakerBoost.checked = settings.speakerBoost;
}

function saveSettingsUI() {
    const newSettings = {
        voiceId: document.getElementById('voice-id').value,
        stability: parseFloat(document.getElementById('stability').value),
        similarity: parseFloat(document.getElementById('similarity').value),
        styleStrength: parseFloat(document.getElementById('style').value),
        speakerBoost: document.getElementById('speaker-boost').checked
    };
    saveSettings(newSettings);
}

function toggleChat() {
    const widget = document.getElementById('chatbot-widget');
    widget.classList.toggle('hidden');

    // Auto focus input when opening
    if (!widget.classList.contains('hidden')) {
        setTimeout(() => document.getElementById('qa-input').focus(), 100);
    }
}

// Start
window.toggleChat = toggleChat;
init();
