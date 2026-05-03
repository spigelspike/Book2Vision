// ============================================
// CONFIGURATION & STATE
// ============================================

const API_BASE = "/api";

// ── Auth Header Helper ────────────────────────────────────────────────────
// Attaches the Supabase JWT to API calls so the backend can identify the user
async function getAuthHeaders(extra = {}) {
    try {
        if (typeof supabaseClient !== 'undefined') {
            const { data } = await supabaseClient.auth.getSession();
            const token = data?.session?.access_token;
            if (token) return { 'Authorization': `Bearer ${token}`, ...extra };
        }
    } catch (e) { /* supabase not available on this page */ }
    return { ...extra };
}

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
const btnPodcast = document.getElementById('btn-podcast');
const podcastPlayerUi = document.getElementById('podcast-player-ui');
const podcastAvatar = document.getElementById('podcast-avatar');
const podcastTranscript = document.getElementById('podcast-transcript');
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
let isTogglingAudio = false;
let visualsGenerated = false;
let currentImageIndex = 0;
let totalImages = 0;

// Default Settings
const DEFAULT_SETTINGS = {
    audioProvider: "pollinations",
    voiceId: "pNInz6obpgDQGcFmaJgB", // Adam (deep voice)
    stability: 0.5,
    similarity: 0.75,
    styleStrength: 0.0,
    speakerBoost: false
};

// --- Initialization ---

// ============================================
// INITIALIZATION
// ============================================

function init() {
    console.log('Script initialized');
    setupEventListeners();
    // Initialize settings if not present
    if (!localStorage.getItem('b2v_settings')) {
        localStorage.setItem('b2v_settings', JSON.stringify(DEFAULT_SETTINGS));
    }

    // Page-specific logic
    const path = window.location.pathname;
    console.log('Current path:', path);
    if (path.includes('library.html')) {
        console.log('Library page detected, calling fetchLibrary()');
        fetchLibrary();
    } else {
        // Home page: Check for bookId param
        const urlParams = new URLSearchParams(window.location.search);
        const bookId = urlParams.get('bookId');
        if (bookId) {
            loadBookFromId(bookId);
        }
    }
}

function setupEventListeners() {
    // Upload
    if (dropZone) {
        dropZone.addEventListener('click', () => fileInput.click());

        // Add keyboard support for accessibility
        dropZone.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                fileInput.click();
            }
        });

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
    if (btnAudio) btnAudio.addEventListener('click', () => {
        // If audio is already loaded/generated, just play it. Otherwise open picker.
        if (state.audiobookUrl) {
            audioPlayer.play();
            isPlaying = true;
            btnPlayPause.textContent = "⏸";
            document.querySelector('.audio-player-ui').classList.add('playing');
        } else {
            openAudioPicker('audiobook');
        }
    });
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
    if (btnVisuals) btnVisuals.addEventListener('click', openStylePicker);
    if (btnPodcast) btnPodcast.addEventListener('click', () => {
        if (document.getElementById('podcast-player-ui').classList.contains('hidden') === false && document.getElementById('podcast-player-ui').style.display !== 'none') {
            // Already showing, do nothing or just play
        } else {
            openAudioPicker('podcast');
        }
    });

    // Chatbot FAB + Close button
    if (chatbotFab) chatbotFab.addEventListener('click', toggleChat);
    const closeChatBtn = document.querySelector('.chatbot-header .btn-icon');
    if (closeChatBtn) closeChatBtn.addEventListener('click', toggleChat);

    // QA
    if (btnSendQa) btnSendQa.addEventListener('click', handleQASubmit);
    if (qaInput) {
        qaInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') handleQASubmit();
        });
    }

    // Provider Change Event
    const providerSelect = document.getElementById('audio-provider');
    if (providerSelect) {
        providerSelect.addEventListener('change', (e) => {
            const voiceCloneSettings = document.getElementById('voice-clone-settings');
            if (e.target.value === 'voice_clone') {
                voiceCloneSettings.classList.remove('hidden');
                voiceCloneSettings.style.display = 'flex';
                voiceCloneSettings.style.flexDirection = 'column';
            } else {
                voiceCloneSettings.classList.add('hidden');
                voiceCloneSettings.style.display = 'none';
            }
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

// ============================================
// UPLOAD & INGESTION
// ============================================

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
        console.error("Upload error:", error);
        showToast(`Upload Failed: ${error.message}`, "error");

        // Show error in status area too
        statusDetail.textContent = `Error: ${error.message}`;
        statusDetail.style.color = "var(--danger)";

        // Reset after delay
        setTimeout(() => {
            dropZone.classList.remove('hidden');
            uploadStatus.classList.add('hidden');
            statusDetail.style.color = ""; // Reset color
        }, 4000);
    }
}

function loadDashboard(data, filename) {
    heroSection.classList.add('hidden');
    dashboardSection.classList.remove('hidden');


    // Set Info
    bookTitle.textContent = filename || data.title || "Unknown Title";
    bookAuthor.textContent = data.author || "Unknown Author";

    // Store context
    currentStoryText = "";

    // Render Entities
    renderEntities(data.analysis.entities);

    // Fetch Suggested Questions
    fetchSuggestedQuestions();

    // Fetch full story text (background)
    // Fetch full story text (background)
    fetchStoryContent();

    // Inject Immersive Mode Button - REMOVED
    // injectImmersiveButton();

    // Check for existing podcast
    if (data.analysis.podcast && data.analysis.podcast.length > 0) {
        podcastPlaylist = data.analysis.podcast;
        btnPodcast.innerHTML = '<span class="icon">▶</span> Play Podcast';
        showToast("Podcast loaded from library!", "success");
    } else {
        podcastPlaylist = [];
        btnPodcast.innerHTML = '<span class="icon">🎙️</span> Generate Podcast';
    }
}

async function fetchStoryContent() {
    // Only fetch if we don't already have the full text
    if (!currentStoryText || currentStoryText.length < 500) {
        try {
            const res = await fetch(`${API_BASE}/story`);
            const data = await res.json();
            currentStoryText = data.body; // Update with full text for better audio/QA
        } catch (e) {
            console.warn("Failed to fetch full story text.");
        }
    }
}

function renderEntities(entities) {
    entitiesList.innerHTML = '';

    if (!entities || entities.length === 0) {
        entitiesList.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">👤</div>
                <p style="font-weight: 600; margin-bottom: 0.5rem;">No Characters Detected</p>
                <p style="font-size: 0.85rem; opacity: 0.7;">The AI couldn't identify any characters in this book. This is normal for non-fiction or technical content.</p>
            </div>
        `;
        entityCount.textContent = "0";
        return;
    }

    entityCount.textContent = entities.length;

    // Create all cards first with placeholder images
    const imagePromises = [];

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
        card.className = 'nb-source-item fade-in-element';
        const imgId = `img-${name.replace(/[^a-zA-Z0-9]/g, '')}`;

        card.innerHTML = `
            <div class="source-icon" id="${imgId}-wrap"><img src="https://ui-avatars.com/api/?name=${encodeURIComponent(name)}&background=random" class="entity-avatar" id="${imgId}" style="width:36px;height:36px;border-radius:var(--radius-sm);object-fit:cover;"></div>
            <div class="source-meta">
                <h4>${name}</h4>
                <p>${role}</p>
            </div>
            <span class="source-check">✓</span>
        `;
        entitiesList.appendChild(card);

        // Queue image fetch for parallel execution
        imagePromises.push(fetchEntityImage(name, imgId));
    });

    // Fetch all images in parallel
    Promise.all(imagePromises).catch(e => {
        console.warn("Some entity images failed to load:", e);
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
        } else {
            console.warn(`Entity image for ${name} returned null URL.`);
        }
    } catch (e) {
        // Silent fail for entity images
    }
}

// --- Audio ---

// ============================================
// AUDIO GENERATION & PLAYBACK
// ============================================

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
        const payload = {
            text: currentStoryText.substring(0, 3000), // Send only what's needed (preview)
            voice_id: settings.voiceId,
            stability: settings.stability,
            similarity_boost: settings.similarity,
            provider: provider,
        };

        const res = await fetch(`${API_BASE}/generate/audio`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
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
            showAudioDock();
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

    // Show the audio dock when user tries to play
    showAudioDock();

    // Prevent race conditions from rapid clicking
    if (isTogglingAudio) return;
    isTogglingAudio = true;

    if (audioPlayer.paused) {
        const playPromise = audioPlayer.play();
        if (playPromise !== undefined) {
            playPromise.then(() => {
                isPlaying = true;
                btnPlayPause.textContent = "⏸";
                if (ui) ui.classList.add('playing');
            }).catch(e => {
                if (e.name === 'AbortError') {
                    // Ignore abort errors caused by rapid pausing
                    console.log("Play interrupted by pause");
                } else {
                    console.error("Play failed:", e);
                    showToast("Could not play audio. " + e.message, "error");
                }
            }).finally(() => {
                isTogglingAudio = false;
            });
        } else {
            isTogglingAudio = false;
        }
    } else {
        audioPlayer.pause();
        isPlaying = false;
        btnPlayPause.textContent = "▶";
        if (ui) ui.classList.remove('playing');
        isTogglingAudio = false;
    }
}

/** Reveals the pinned audio dock at the bottom of the center panel */
function showAudioDock() {
    const dock = document.getElementById('nb-audio-dock');
    if (dock && !dock.classList.contains('visible')) {
        dock.classList.add('visible');
        dock.setAttribute('aria-hidden', 'false');
    }
}

function skip(seconds) {
    audioPlayer.currentTime += seconds;
}

function updateProgress() {
    if (!audioPlayer.duration || isNaN(audioPlayer.duration) || audioPlayer.duration === 0) {
        return; // Skip update if duration is invalid
    }
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

// ============================================
// VOICE CLONING (COLAB)
// ============================================

async function uploadVoiceSample(event) {
    const file = event.target.files[0];
    if (!file) return;

    if (!file.name.toLowerCase().endsWith('.wav')) {
        showToast("Please upload a .wav file for voice cloning.", "error");
        return;
    }

    const btn = document.getElementById('btn-upload-voice');
    const originalText = btn.textContent;
    btn.innerHTML = '<span class="icon">⏳</span> Uploading...';
    btn.disabled = true;

    const formData = new FormData();
    formData.append('voice_sample', file);

    try {
        const res = await fetch(`${API_BASE}/upload-voice-sample`, {
            method: 'POST',
            body: formData
        });

        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || "Upload failed");
        }

        btn.textContent = "✅ Sample Uploaded";
        btn.classList.add("btn-success");
        showToast("Voice sample uploaded successfully!", "success");
        setTimeout(() => {
            btn.textContent = "Upload Different Sample";
            btn.classList.remove("btn-success");
        }, 3000);

    } catch (e) {
        showToast(e.message, "error");
        btn.textContent = originalText;
    } finally {
        btn.disabled = false;
    }
}

async function setColabUrl() {
    const urlInput = document.getElementById('colab-url').value;
    if (!urlInput) return;

    try {
        const res = await fetch(`${API_BASE}/set-colab-url`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url: urlInput })
        });

        if (res.ok) {
            showToast("Colab URL linked successfully", "success");
        } else {
            showToast("Failed to link Colab URL", "error");
        }
    } catch (e) {
        console.error("Error setting Colab URL:", e);
    }
}

// --- Visuals ---

// ============================================
// VISUAL STYLE PICKER + GENERATION
// ============================================

/** Opens the art-style picker modal */
function openStylePicker() {
    const overlay = document.getElementById('style-picker-overlay');
    if (overlay) overlay.classList.add('open');
}

/** Closes the art-style picker modal.
 *  If called from the overlay click, only close if clicking the backdrop itself. */
function closeStylePicker(e) {
    if (e && e.target !== e.currentTarget) return; // clicked inside modal, not backdrop
    const overlay = document.getElementById('style-picker-overlay');
    if (overlay) overlay.classList.remove('open');
}



// --- Audio Picker Modal ---
let pendingAudioAction = null;

function openAudioPicker(type) {
    pendingAudioAction = type;
    const modal = document.getElementById('audio-picker-overlay');
    const title = document.getElementById('audio-picker-title');
    if (title) title.textContent = type === 'podcast' ? 'Generate Podcast' : 'Generate Audiobook';
    
    // Load current settings into modal
    const settings = getSettings();
    const providerSelect = document.getElementById('modal-audio-provider');
    const voiceInput = document.getElementById('modal-voice-id');
    
    if (providerSelect) providerSelect.value = settings.audioProvider || 'pollinations';
    if (voiceInput) voiceInput.value = settings.voiceId || 'nova';

    if (modal) {
        modal.style.display = 'flex';
        modal.classList.remove('hidden');
    }
}

function closeAudioPicker(e) {
    if (e && e.target !== document.getElementById('audio-picker-overlay')) return;
    const modal = document.getElementById('audio-picker-overlay');
    if (modal) {
        modal.style.display = 'none';
        modal.classList.add('hidden');
    }
}

function confirmAudioPicker() {
    const providerSelect = document.getElementById('modal-audio-provider');
    const voiceInput = document.getElementById('modal-voice-id');
    
    const newSettings = {
        ...getSettings(),
        audioProvider: providerSelect ? providerSelect.value : 'pollinations',
        voiceId: voiceInput ? voiceInput.value : 'nova'
    };
    saveSettings(newSettings);
    
    // Also update main settings inputs if they exist on the page
    const mainProviderSelect = document.getElementById('audio-provider');
    if (mainProviderSelect) mainProviderSelect.value = newSettings.audioProvider;
    
    closeAudioPicker();
    
    if (pendingAudioAction === 'podcast') {
        generatePodcast();
    } else {
        generateAudio();
    }
}

function pickStyleAndGenerate(style) {
    closeStylePicker();
    // Update the hidden <select> to keep state in sync
    const sel = document.getElementById('style-select');
    if (sel) sel.value = style;
    generateVisuals(style);
}

async function generateVisuals(styleOverride = null) {
    const originalText = btnVisuals.innerHTML;
    btnVisuals.innerHTML = '<span class="icon">⏳</span> Requesting...';
    btnVisuals.disabled = true;

    const style = (typeof styleOverride === 'string') ? styleOverride : document.getElementById('style-select').value;


    try {
        console.log("Sending request to /api/generate/visuals...");
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 10000); // 10s timeout

        const res = await fetch(`${API_BASE}/generate/visuals`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                style: style,
                seed: 42
            }),
            signal: controller.signal
        });
        clearTimeout(timeoutId);
        console.log("Response received:", res.status);

        if (!res.ok) throw new Error("Visuals generation failed");

        const data = await res.json();

        // Immediate feedback: Inject placeholders
        console.log("✅ Frontend received images:", data.images);
        injectImages(data.images, true);
        visualsGenerated = true;
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
        console.log(`💉 Injecting ${images.length} images into carousel`);
        images.forEach((imgUrl, index) => {
            const wrapper = document.createElement('div');
            wrapper.className = 'image-wrapper';

            const img = document.createElement('img');
            // Add timestamp to prevent caching of old failed attempts if any
            img.dataset.src = imgUrl;
            img.src = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 1 1'%3E%3C/svg%3E"; // Transparent placeholder
            img.className = 'generated-img placeholder';
            img.alt = `Scene ${index}`;

            // Skeleton structure for loading
            const skeleton = document.createElement('div');
            skeleton.className = 'skeleton-card';
            skeleton.style.width = '100%';
            skeleton.style.height = '100%';
            skeleton.style.position = 'absolute';
            skeleton.style.top = '0';
            skeleton.style.left = '0';

            wrapper.appendChild(img);
            wrapper.appendChild(skeleton); // Add skeleton overlay
            imageDisplay.appendChild(wrapper);

            // Start polling for this image
            pollForImage(img, imgUrl, skeleton);
        });
    } else {
        imageDisplay.innerHTML = '<div class="placeholder-content"><p>No images generated.</p></div>';
    }
}

function pollForImage(imgElement, url, spinner, attempts = 0) {
    const maxAttempts = 20; // Reduce from 60 to 20 with longer intervals
    const baseInterval = 2000; // Start at 2s
    const maxInterval = 10000; // Cap at 10s

    const img = new Image();
    img.onload = () => {
        imgElement.src = url;
        imgElement.classList.remove('placeholder');
        imgElement.classList.add('loaded', 'fade-in-image');
        if (spinner) spinner.remove(); // Remove skeleton/spinner
    };
    img.onerror = () => {
        if (attempts < maxAttempts) {
            // Exponential backoff: 2s, 3s, 4.5s, 6.75s, capped at 10s
            const nextInterval = Math.min(baseInterval * Math.pow(1.5, attempts), maxInterval);
            setTimeout(() => pollForImage(imgElement, url, spinner, attempts + 1), nextInterval);
        } else {
            // Add retry button on failure
            if (spinner) {
                spinner.innerHTML = '';
                spinner.className = 'image-error-state';

                const errorContent = document.createElement('div');
                errorContent.innerHTML = `
                    <div style="font-size: 1.5rem; margin-bottom: 0.5rem;">❌</div>
                    <button class="btn-retry" onclick="retryImage('${url}', '${imgElement.id}', this.parentElement.parentElement)">
                        Retry
                    </button>
                `;
                spinner.appendChild(errorContent);
            }
        }
    };
    // Add cache buster to check if file exists on server yet
    img.src = `${url}?t=${Date.now()}`;
    // Add cache buster to check if file exists on server yet
    img.src = `${url}?t=${Date.now()}`;
}

// --- Carousel Logic ---

function updateCarousel() {
    const display = document.getElementById('image-display');
    const images = display.getElementsByClassName('image-wrapper');
    totalImages = images.length;
    const indicatorsContainer = document.getElementById('carousel-indicators');
    const counter = document.getElementById('carousel-counter');

    console.log(`🎠 Updating Carousel: ${totalImages} images, Index: ${currentImageIndex}`);

    if (totalImages === 0) {
        if (indicatorsContainer) indicatorsContainer.innerHTML = '';
        if (counter) counter.textContent = "0/0";
        return;
    }

    // Loop
    if (currentImageIndex >= totalImages) currentImageIndex = 0;
    if (currentImageIndex < 0) currentImageIndex = totalImages - 1;

    // Update Images
    Array.from(images).forEach((img, index) => {
        if (index === currentImageIndex) {
            img.classList.add('active');
        } else {
            img.classList.remove('active');
        }
    });

    // Update Indicators
    if (indicatorsContainer) {
        // Rebuild if count mismatch
        if (indicatorsContainer.children.length !== totalImages) {
            indicatorsContainer.innerHTML = '';
            for (let i = 0; i < totalImages; i++) {
                const dot = document.createElement('div');
                dot.className = 'indicator';
                dot.onclick = () => {
                    currentImageIndex = i;
                    updateCarousel();
                };
                indicatorsContainer.appendChild(dot);
            }
        }

        // Set active
        Array.from(indicatorsContainer.children).forEach((dot, index) => {
            if (index === currentImageIndex) dot.classList.add('active');
            else dot.classList.remove('active');
        });
    }

    // Update Counter
    if (counter) {
        counter.textContent = `${currentImageIndex + 1}/${totalImages}`;
    }
}

function nextImage() {
    if (totalImages > 0) {
        currentImageIndex++;
        updateCarousel();
    }
}

function prevImage() {
    if (totalImages > 0) {
        currentImageIndex--;
        updateCarousel();
    }
}

// Override injectImages to init carousel
const originalInjectImages = injectImages;
injectImages = function (images, isAsync = false) {
    originalInjectImages(images, isAsync);
    currentImageIndex = 0;
    updateCarousel();
};

// --- Podcast ---

let podcastPlaylist = [];
let currentPodcastIndex = 0;

async function generatePodcast() {
    const originalText = btnPodcast.innerHTML;
    btnPodcast.innerHTML = '<span class="icon">⏳</span> Scripting...';
    btnPodcast.disabled = true;

    // Show the audio dock when podcast starts
    showAudioDock();

    // Stop Audiobook if playing
    if (isPlaying) {
        toggleAudio();
    }

    // Check if we already have a playlist
    if (podcastPlaylist.length > 0) {
        podcastPlayerUi.classList.remove('hidden');
        document.querySelector('.audio-visualizer').classList.add('hidden');
        document.getElementById('progress-container').classList.add('hidden');
        document.querySelector('.time-display').classList.add('hidden');
        document.querySelector('.player-controls').classList.add('hidden');

        playPodcastSequence(0);
        btnPodcast.disabled = false;
        btnPodcast.innerHTML = originalText;
        return;
    }

    // Show UI, Hide Audiobook Controls
    podcastPlayerUi.classList.remove('hidden');
    document.querySelector('.audio-visualizer').classList.add('hidden');
    document.getElementById('progress-container').classList.add('hidden');
    document.querySelector('.time-display').classList.add('hidden');
    document.querySelector('.player-controls').classList.add('hidden');

    podcastTranscript.textContent = "Producers are writing the script...";

    try {
        const res = await fetch(`${API_BASE}/generate/podcast`, {
            method: 'POST'
        });

        if (!res.ok) throw new Error("Podcast generation failed");

        const data = await res.json();
        podcastPlaylist = data.playlist;

        if (podcastPlaylist.length > 0) {
            podcastTranscript.textContent = "Recording audio...";
            playPodcastSequence(0);
        } else {
            throw new Error("No script generated.");
        }

    } catch (e) {
        showToast(e.message, "error");
        closePodcast(); // Revert UI on error
    } finally {
        btnPodcast.innerHTML = originalText;
        btnPodcast.disabled = false;
    }
}

let currentPodcastAudio = null;

function playPodcastSequence(index) {
    if (index >= podcastPlaylist.length) {
        podcastTranscript.textContent = "Thanks for listening!";
        podcastAvatar.textContent = "👋";
        return;
    }

    currentPodcastIndex = index;
    const segment = podcastPlaylist[index];

    // Update UI
    podcastTranscript.textContent = `"${segment.text}"`;
    podcastAvatar.textContent = segment.speaker === "Jax" ? "😎" : "👩‍🏫";
    podcastAvatar.style.background = segment.speaker === "Jax" ? "#FF6B6B" : "#4ECDC4";

    // Play Audio
    if (currentPodcastAudio) {
        currentPodcastAudio.pause();
        currentPodcastAudio = null;
    }
    currentPodcastAudio = new Audio(segment.url);
    currentPodcastAudio.play();

    currentPodcastAudio.onended = () => {
        playPodcastSequence(index + 1);
    };

    currentPodcastAudio.onerror = () => {
        console.error("Audio segment failed, skipping...");
        playPodcastSequence(index + 1);
    };
}

function closePodcast() {
    podcastPlayerUi.classList.add('hidden');

    // Stop Podcast Audio
    if (currentPodcastAudio) {
        currentPodcastAudio.pause();
        currentPodcastAudio = null;
    }
    podcastPlaylist = []; // Clear playlist

    // Show Audiobook Controls
    document.querySelector('.audio-visualizer').classList.remove('hidden');
    document.getElementById('progress-container').classList.remove('hidden');
    document.querySelector('.time-display').classList.remove('hidden');
    document.querySelector('.player-controls').classList.remove('hidden');
}
window.closePodcast = closePodcast;

// --- Q&A ---

// ============================================
// Q&A / CHAT
// ============================================

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
            errorMsg = "The question timed out. The book may be too long or the AI is busy. Try a simpler question.";
        } else {
            errorMsg += " " + e.message;
        }
        addChatMessage(errorMsg, 'ai');
    }
}

let msgCounter = 0;
function addChatMessage(text, type) {
    const msg = document.createElement('div');
    msg.className = `nb-chat-msg ${type}`;
    msg.textContent = text;
    const id = 'msg-' + Date.now() + '-' + (msgCounter++);
    msg.id = id;

    qaChatContainer.appendChild(msg);

    // Immediate scroll (faster than requestAnimationFrame)
    qaChatContainer.scrollTop = qaChatContainer.scrollHeight;

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
                chip.className = 'nb-chip';
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

function downloadAllContent() {
    showToast("Preparing download...", "info");
    window.location.href = `${API_BASE}/download_all`;
}

// --- Library ---

// ============================================
// LIBRARY MANAGEMENT
// ============================================

let libraryBooks = [];

async function fetchLibrary() {
    console.log('fetchLibrary() called');
    try {
        // Show skeletons
        const grid = document.getElementById('library-grid');
        if (grid) {
            console.log('Found library-grid element');
            grid.innerHTML = Array(6).fill(0).map(() => `
                <div class="book-card glass skeleton-card" style="height: 200px;"></div>
            `).join('');
        } else {
            console.error('library-grid element not found!');
            return;
        }

        console.log('Fetching from /api/library...');
        const res = await fetch(`${API_BASE}/library`);
        if (!res.ok) {
            const err = await res.json().catch(() => ({ detail: "Unknown error" }));
            throw new Error(err.detail || "Failed to fetch library");
        }
        const data = await res.json();
        console.log('Received library data:', data);
        libraryBooks = data.books;
        console.log(`libraryBooks set to ${libraryBooks.length} books`);
        renderLibrary();
    } catch (e) {
        console.error("Library fetch error:", e);
        showToast(`Library Error: ${e.message}`, "error");
        // Clear skeletons if failed
        const grid = document.getElementById('library-grid');
        if (grid) {
            grid.innerHTML = `
                <div class="library-empty-state glass">
                    <div class="icon-large">⚠️</div>
                    <h3>Could not load library</h3>
                    <p>${e.message}</p>
                    <button class="btn-primary" onclick="fetchLibrary()">Retry</button>
                </div>
            `;
        }
    }
}


// ============================================
// IMMERSIVE STORY MODE
// ============================================

let immersiveScenes = [];
let currentSceneIndex = 0;
let immersiveAudioPlayer = null;
let immersivePlaying = false;
let immersiveAutoAdvanceTimer = null;

async function startImmersiveMode() {
    const overlay = document.getElementById('immersive-overlay');
    const imgEl = document.getElementById('immersive-image');
    const videoEl = document.getElementById('immersive-video');
    const textEl = document.getElementById('immersive-text');
    const audioEl = document.getElementById('immersive-audio');

    if (!overlay) return;

    // Show overlay immediately
    overlay.classList.remove('hidden');

    if (!visualsGenerated) {
        textEl.textContent = "Please generate visuals first using the 'Generate Visuals' button.";
        setTimeout(() => {
            closeImmersiveMode();
            document.getElementById('btn-visuals').focus();
            showToast("Please generate visuals first!", "info");
        }, 2000);
        return;
    }

    textEl.textContent = "Loading story scenes...";

    try {
        // 1. Ensure visuals are generated (or at least requested)
        // We check if we have scenes from analysis
        // We assume analysis is done if dashboard is loaded

        // 2. Request Immersive Audio
        const settings = getSettings();
        const providerSelect = document.getElementById('audio-provider');
        const providerVal = providerSelect ? providerSelect.value : (settings.voiceId === "21m00Tcm4TlvDq8ikWAM" ? "elevenlabs" : "deepgram");
        
        const res = await fetch(`${API_BASE}/generate/immersive_audio`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                voice_id: settings.voiceId,
                provider: providerVal
            })
        });

        if (!res.ok) throw new Error("Failed to initialize immersive audio");
        const data = await res.json();

        // 3. Prepare Scenes Data
        // We need to merge analysis scenes with audio URLs and image URLs
        // We can reconstruct image URLs based on convention or fetch from state if we had an endpoint
        // For now, we assume convention: image_01_scene_{i+1:02d}.jpg

        // Fetch fresh analysis to get scenes text
        // (Actually we don't have an endpoint to get just analysis, but we have it in `loadDashboard` data... 
        //  Wait, `loadDashboard` didn't save analysis to global state, only summary. 
        //  We need to fetch story again or store it. 
        //  `fetchStoryContent` gets `/api/story` which returns entities and images but maybe not scenes structure?
        //  Let's check `server.py` `/api/story`.
        //  It returns `state.ingestion_result.get("body")`, `entities`, `images`.
        //  It does NOT return scenes.
        //  I should update `/api/story` or add a new endpoint to get scenes.
        //  OR, I can just use the audio/visuals we generated.
        //  But I need the text to display!

        //  Quick fix: Fetch `/api/upload` response again? No.
        //  I'll fetch `/api/story` and assume I can get scenes from it? No.

        //  I'll add a quick endpoint to get scenes or update `/api/story`.
        //  Let's assume I'll update `/api/story` in next step.
        //  For now, I'll try to fetch `/api/story` and hope I added scenes to it? No I didn't.

        //  I will use a placeholder for text if missing, or fetch from a new endpoint.
        //  Let's add `getScenes` to `script.js` which calls `/api/story` (I will update server to include scenes).

        const storyRes = await fetch(`${API_BASE}/story`);
        const storyData = await storyRes.json();
        const scenes = storyData.scenes || []; // I need to ensure server returns this

        immersiveScenes = scenes.map((scene, i) => ({
            image: `/api/assets/visuals/image_01_scene_${String(i + 1).padStart(2, '0')}.jpg`,
            audio: data.audio_urls[i],
            text: scene.excerpt || scene.description || "Scene " + (i + 1),
            narrator: scene.narrator_intro || ""
        }));

        if (immersiveScenes.length === 0) {
            textEl.textContent = "No scenes found. Please analyze the book first.";
            return;
        }

        // Start Sequence
        currentSceneIndex = 0;
        loadScene(0);

    } catch (e) {
        console.error(e);
        textEl.textContent = "Error loading immersive mode: " + e.message;
    }
}

function loadScene(index) {
    if (index < 0 || index >= immersiveScenes.length) return;

    currentSceneIndex = index;
    const scene = immersiveScenes[index];

    const imgEl = document.getElementById('immersive-image');
    const videoEl = document.getElementById('immersive-video');
    const textEl = document.getElementById('immersive-text');
    const audioEl = document.getElementById('immersive-audio');
    const counterEl = document.getElementById('immersive-counter');
    const playBtn = document.getElementById('btn-immersive-play');

    // Update UI
    counterEl.textContent = `Scene ${index + 1}/${immersiveScenes.length}`;
    textEl.textContent = ""; // Clear text for typing effect

    // Load Image/Video
    imgEl.style.opacity = 0;
    videoEl.classList.add('hidden');
    videoEl.pause();

    // Check if video exists for this scene
    if (scene.video) {
        imgEl.classList.add('hidden');
        videoEl.classList.remove('hidden');
        videoEl.src = scene.video;
        videoEl.load();
        // Video will auto-play if immersivePlaying is true via playImmersive()
    } else {
        videoEl.classList.add('hidden');
        imgEl.classList.remove('hidden');
        setTimeout(() => {
            imgEl.src = `${scene.image}?t=${Date.now()}`; // Cache bust
            imgEl.onload = () => { imgEl.style.opacity = 1; };
        }, 300);
    }

    // Play Audio
    audioEl.src = scene.audio;
    audioEl.load();

    // Auto-play
    playImmersive();

    // Typewriter text
    typeWriter(scene.narrator ? `[${scene.narrator}] ${scene.text}` : scene.text, textEl);
}

async function generateMotionForCurrentScene() {
    const btn = document.getElementById('btn-generate-motion');
    const scene = immersiveScenes[currentSceneIndex];

    if (scene.video) {
        showToast("Motion already generated for this scene!", "info");
        return;
    }

    if (!confirm("Generate motion video for this scene? This may take 1-2 minutes.")) return;

    btn.disabled = true;
    btn.innerHTML = "⏳";
    showToast("Generating motion... please wait", "info");

    try {
        // Extract filename from URL
        const filename = scene.image.split('/').pop().split('?')[0];

        const res = await fetch(`${API_BASE}/generate/scene_video`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                scene_index: currentSceneIndex,
                image_filename: filename,
                prompt: scene.text // Use scene text as prompt
            })
        });

        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || "Video generation failed");
        }

        const data = await res.json();

        // Update scene data
        scene.video = data.video_url;
        immersiveScenes[currentSceneIndex] = scene;

        showToast("Motion generated! Reloading scene...", "success");
        loadScene(currentSceneIndex);

    } catch (e) {
        console.error(e);
        showToast(`Motion generation failed: ${e.message}`, "error");
    } finally {
        btn.disabled = false;
        btn.innerHTML = "🎬";
    }
}

function playImmersive() {
    const audioEl = document.getElementById('immersive-audio');
    const videoEl = document.getElementById('immersive-video');
    const playBtn = document.getElementById('btn-immersive-play');

    const playPromise = audioEl.play();

    if (playPromise !== undefined) {
        playPromise.then(() => {
            immersivePlaying = true;
            playBtn.textContent = "⏸️";

            // Play video if available
            if (!videoEl.classList.contains('hidden')) {
                videoEl.play().catch(e => console.warn("Video play failed", e));
            }

            // Auto-advance when ended
            audioEl.onended = () => {
                immersivePlaying = false;
                playBtn.textContent = "▶️";
                if (!videoEl.classList.contains('hidden')) videoEl.pause();

                // Wait 2 seconds then next
                immersiveAutoAdvanceTimer = setTimeout(() => {
                    if (currentSceneIndex < immersiveScenes.length - 1) {
                        nextScene();
                    }
                }, 2000);
            };
        }).catch(e => {
            console.warn("Audio play failed", e);
            immersivePlaying = false;
            playBtn.textContent = "▶️";
        });
    }
}

function pauseImmersive() {
    const audioEl = document.getElementById('immersive-audio');
    const videoEl = document.getElementById('immersive-video');
    const playBtn = document.getElementById('btn-immersive-play');

    audioEl.pause();
    if (!videoEl.classList.contains('hidden')) videoEl.pause();

    immersivePlaying = false;
    playBtn.textContent = "▶️";
    if (immersiveAutoAdvanceTimer) clearTimeout(immersiveAutoAdvanceTimer);
}

function toggleImmersivePlay() {
    if (immersivePlaying) pauseImmersive();
    else playImmersive();
}

function nextScene() {
    if (currentSceneIndex < immersiveScenes.length - 1) {
        loadScene(currentSceneIndex + 1);
    }
}

function prevScene() {
    if (currentSceneIndex > 0) {
        loadScene(currentSceneIndex - 1);
    }
}

function closeImmersiveMode() {
    pauseImmersive();
    document.getElementById('immersive-overlay').classList.add('hidden');
}

function typeWriter(text, element, i = 0) {
    if (i === 0) element.textContent = "";
    if (i < text.length) {
        element.textContent += text.charAt(i);
        setTimeout(() => typeWriter(text, element, i + 1), 30);
    }
}

function injectImmersiveButton() {
    // Removed as per user request
}
window.startImmersiveMode = startImmersiveMode;
window.toggleImmersivePlay = toggleImmersivePlay;
window.nextScene = nextScene;
window.prevScene = prevScene;
window.closeImmersiveMode = closeImmersiveMode;

function renderLibrary() {
    const grid = document.getElementById('library-grid');
    if (!grid) {
        console.error('library-grid element not found');
        return; // Guard clause for non-library pages
    }

    const searchInput = document.getElementById('library-search');
    const sortSelect = document.getElementById('library-sort');

    const searchTerm = searchInput ? searchInput.value.toLowerCase() : '';
    const sortMethod = sortSelect ? sortSelect.value : 'date-desc';

    // Filter
    let filtered = libraryBooks.filter(book =>
        book.title.toLowerCase().includes(searchTerm) ||
        book.author.toLowerCase().includes(searchTerm)
    );

    // Sort
    filtered.sort((a, b) => {
        if (sortMethod === 'date-desc') return b.upload_date - a.upload_date;
        if (sortMethod === 'date-asc') return a.upload_date - b.upload_date;
        if (sortMethod === 'title-asc') return a.title.localeCompare(b.title);
        return 0;
    });

    grid.innerHTML = '';

    if (filtered.length === 0) {
        if (searchTerm) {
            grid.innerHTML = `
                <div class="library-empty-state glass">
                    <div class="icon-large">🔍</div>
                    <h3>No books found</h3>
                    <p>Try a different search term</p>
                </div>
            `;
        } else {
            grid.innerHTML = `
                <div class="library-empty-state glass">
                    <div class="icon-large">📚</div>
                    <h3>Your library is empty</h3>
                    <p>Upload a book to get started!</p>
                    <button class="btn-primary" onclick="window.location.href='index.html'">Upload Book</button>
                </div>
            `;
        }
        return;
    }

    filtered.forEach(book => {
        const card = document.createElement('div');
        card.className = 'book-card fade-in-element';

        // Format date
        const date = new Date(book.upload_date * 1000).toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric'
        });

        let thumbContent = `
            <div class="book-thumbnail no-image">
                <div class="poster-placeholder-text">${book.title}</div>
                <div style="font-size: 3rem; opacity: 0.3;">📖</div>
                <div style="font-size: 0.8rem; opacity: 0.5; margin-top: 0.5rem;">Cover generating...</div>
            </div>
        `;

        if (book.thumbnail) {
            thumbContent = `
                <div class="book-thumbnail">
                    <img src="/api/assets/${book.thumbnail}" alt="${book.title}" loading="lazy">
                    <div class="book-actions-overlay">
                        <button class="btn-action-round" onclick="openBook('${book.id}')" title="Read Book">▶</button>
                        <button class="btn-action-round" onclick="deleteBook('${book.id}')" style="background: rgba(239, 69, 101, 0.2); border-color: var(--danger);" title="Delete">×</button>
                    </div>
                </div>
            `;
        } else {
            // If no thumbnail, we still want the overlay for delete/open, but maybe different?
            // Actually, let's keep the "Create Poster" button visible if no image.
            // But we also need a way to open/delete if no image.
            // The design shows "Extracted PDF" cards WITH images.
            // My code above puts the button inside the no-image block.
        }

        card.innerHTML = `
            ${thumbContent}
            
            <div class="book-content">
                <h3 class="book-title" title="${book.title}">${book.title}</h3>
                <p class="book-author">${book.author}</p>
                
                <div class="book-footer">
                    <span class="book-date">${date}</span>
                    <a href="#" onclick="openBook('${book.id}'); return false;" class="btn-open-link">Open Library →</a>
                </div>
            </div>
        `;
        grid.appendChild(card);
    });
}

async function generatePoster(bookId, btn, event) {
    if (event) event.stopPropagation();

    const originalText = btn.innerHTML;
    btn.innerHTML = '<span>⏳</span> Creating...';
    btn.disabled = true;

    try {
        // First load the book to ensure state is set (if needed by backend)
        // Actually backend endpoint takes book_id from state, so we need to load it first?
        // My backend endpoint `generate_poster` checks `state.book_id`.
        // But `state.book_id` is global and might be different.
        // I should update backend to accept book_id in body or param, OR load it here.
        // Loading it is safer.

        await fetch(`${API_BASE}/library/load/${bookId}`, { method: 'POST' });

        const res = await fetch(`${API_BASE}/generate/poster`, {
            method: 'POST'
        });

        if (!res.ok) throw new Error("Poster generation failed");

        const data = await res.json();
        showToast("Cover created!", "success");

        // Refresh library to show new image
        fetchLibrary();

    } catch (e) {
        showToast(e.message, "error");
        btn.innerHTML = originalText;
        btn.disabled = false;
    }
}

function filterLibrary() {
    renderLibrary();
}

function sortLibrary() {
    renderLibrary();
}

function openBook(bookId) {
    // Redirect to home with bookId param
    window.location.href = `index.html?bookId=${bookId}`;
}

async function loadBookFromId(bookId) {
    try {
        // Show loading state
        if (typeof heroSection !== 'undefined') heroSection.classList.add('hidden');
        if (typeof dashboardSection !== 'undefined') dashboardSection.classList.add('hidden');

        showToast("Loading book from library...", "info");

        const res = await fetch(`${API_BASE}/library/load/${bookId}`, { method: 'POST' });

        if (!res.ok) throw new Error("Failed to load book");

        const data = await res.json();
        loadDashboard(data, data.filename);
        showToast("Book loaded successfully!", "success");

        // Clear URL param so refresh doesn't re-load
        window.history.replaceState({}, document.title, "index.html");

    } catch (e) {
        showToast(e.message, "error");
        if (typeof heroSection !== 'undefined') heroSection.classList.remove('hidden'); // Show hero on error
    }
}

async function deleteBook(bookId) {
    if (!confirm("Are you sure you want to delete this book? This cannot be undone.")) return;

    try {
        const res = await fetch(`${API_BASE}/library/${bookId}`, { method: 'DELETE' });
        if (!res.ok) throw new Error("Failed to delete book");

        showToast("Book deleted", "success");
        fetchLibrary(); // Refresh
    } catch (e) {
        showToast(e.message, "error");
    }
}

// --- Utilities ---

// ============================================
// UTILITIES
// ============================================

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
    if (voiceId) voiceId.value = settings.voiceId || "nova";

    const audioProvider = document.getElementById('audio-provider');
    if (audioProvider && settings.audioProvider) audioProvider.value = settings.audioProvider;

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
        audioProvider: document.getElementById('audio-provider') ? document.getElementById('audio-provider').value : "pollinations",
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

// Global retry function for image generation
window.retryImage = function (url, imgId, spinner) {
    spinner.innerHTML = ''; // Clear error
    spinner.className = 'skeleton-card'; // Reset to skeleton
    spinner.style.width = '100%';
    spinner.style.height = '100%';
    spinner.style.position = 'absolute';
    const imgElement = document.getElementById(imgId);
    pollForImage(imgElement, url, spinner, 0); // Start from attempt 0
};

init();

// ============================================
// THREE-PANEL LAYOUT LOGIC
// ============================================

(function initPanels() {
    const layout = document.getElementById('panels-layout');
    if (!layout) return;

    // ── Collapse / Expand ──
    const btnLeft = document.getElementById('btn-collapse-left');
    const btnRight = document.getElementById('btn-collapse-right');

    if (btnLeft) {
        btnLeft.addEventListener('click', () => {
            layout.classList.toggle('left-collapsed');
            btnLeft.textContent = layout.classList.contains('left-collapsed') ? '▶' : '◀';
        });
    }
    if (btnRight) {
        btnRight.addEventListener('click', () => {
            layout.classList.toggle('right-collapsed');
            btnRight.textContent = layout.classList.contains('right-collapsed') ? '◀' : '▶';
        });
    }

    // ── Drag-to-Resize ──
    function initResize(handleId, side) {
        const handle = document.getElementById(handleId);
        if (!handle) return;

        let startX, startW;

        handle.addEventListener('mousedown', (e) => {
            e.preventDefault();
            handle.classList.add('dragging');
            startX = e.clientX;
            const panel = side === 'left'
                ? document.getElementById('panel-left')
                : document.getElementById('panel-right');
            startW = panel.getBoundingClientRect().width;

            const onMove = (ev) => {
                const dx = side === 'left' ? ev.clientX - startX : startX - ev.clientX;
                const newW = Math.max(56, Math.min(500, startW + dx));
                layout.style.setProperty(side === 'left' ? '--left-w' : '--right-w', newW + 'px');
            };
            const onUp = () => {
                handle.classList.remove('dragging');
                document.removeEventListener('mousemove', onMove);
                document.removeEventListener('mouseup', onUp);
            };
            document.addEventListener('mousemove', onMove);
            document.addEventListener('mouseup', onUp);
        });
    }
    initResize('resize-left', 'left');
    initResize('resize-right', 'right');

    // ── Waveform Bars ──
    const waveform = document.getElementById('pinned-waveform');
    if (waveform) {
        for (let i = 0; i < 40; i++) {
            const bar = document.createElement('div');
            bar.className = 'wv-bar';
            bar.style.animationDelay = (Math.random() * 0.5).toFixed(2) + 's';
            bar.style.animationDuration = (0.5 + Math.random() * 0.5).toFixed(2) + 's';
            waveform.appendChild(bar);
        }
    }

    // ── Volume Slider ──
    const volSlider = document.getElementById('volume-slider');
    const ap = document.getElementById('audio-player');
    if (volSlider && ap) {
        volSlider.addEventListener('input', (e) => { ap.volume = parseFloat(e.target.value); });
    }

    // ── Speed Button ──
    const speeds = [0.5, 0.75, 1, 1.25, 1.5, 2];
    let speedIdx = 2;
    const btnSpeed = document.getElementById('btn-speed');
    if (btnSpeed && ap) {
        btnSpeed.addEventListener('click', () => {
            speedIdx = (speedIdx + 1) % speeds.length;
            ap.playbackRate = speeds[speedIdx];
            btnSpeed.textContent = speeds[speedIdx] + 'x';
        });
    }

    // ── Sync pinned player state ──
    const pinned = document.getElementById('nb-audio-pinned');
    if (ap && pinned) {
        ap.addEventListener('play', () => { pinned.classList.add('playing'); pinned.classList.remove('paused'); });
        ap.addEventListener('pause', () => { pinned.classList.remove('playing'); pinned.classList.add('paused'); });
    }

    // ── Source search filter ──
    const searchInput = document.getElementById('source-search');
    if (searchInput) {
        searchInput.addEventListener('input', () => {
            const q = searchInput.value.toLowerCase();
            const items = document.querySelectorAll('#entities-list .nb-source-item, #entities-list .entity-card');
            items.forEach(item => {
                const text = item.textContent.toLowerCase();
                item.style.display = text.includes(q) ? '' : 'none';
            });
        });
    }
})();



// ============================================
// CHARACTER PORTRAITS
// ============================================

async function generateCharacterPortraits() {
    const btn = document.getElementById('btn-portraits');
    if (!btn) return;

    const originalText = btn.innerHTML;
    btn.innerHTML = '<span class="icon">⏳</span> Generating...';
    btn.disabled = true;

    try {
        const res = await fetch(`${API_BASE}/generate/character-portraits`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                style: document.getElementById('style-select')?.value || 'anime',
                genre: 'fantasy'
            })
        });

        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || "Portrait generation failed");
        }

        const data = await res.json();
        showToast(`Generating ${data.count} character portraits...`, "success");

        // Poll for portraits and update entity cards
        if (data.portraits && data.portraits.length > 0) {
            data.portraits.forEach((url, index) => {
                pollForPortrait(url, index);
            });
        }
    } catch (e) {
        showToast(e.message, "error");
    } finally {
        btn.innerHTML = originalText;
        btn.disabled = false;
    }
}

function pollForPortrait(url, index, attempts = 0) {
    const maxAttempts = 20;
    const interval = 3000;

    const img = new Image();
    img.onload = () => {
        // Find matching entity card and update
        const entityCards = document.querySelectorAll('.entity-card');
        if (entityCards[index]) {
            const avatar = entityCards[index].querySelector('.entity-avatar');
            if (avatar) {
                avatar.src = url + '?t=' + Date.now();
                avatar.classList.add('portrait-loaded');
            }
        }
    };
    img.onerror = () => {
        if (attempts < maxAttempts) {
            setTimeout(() => pollForPortrait(url, index, attempts + 1), interval);
        }
    };
    img.src = url + '?t=' + Date.now();
}

async function viewCharacterSheet(name) {
    showToast(`Generating character sheet for ${name}...`, "info");

    try {
        const res = await fetch(`${API_BASE}/character/${encodeURIComponent(name)}/sheet`);
        const data = await res.json();

        if (data.sheet_url) {
            // Open in modal or new tab
            window.open(data.sheet_url, '_blank');
        } else {
            throw new Error("Sheet generation failed");
        }
    } catch (e) {
        showToast(e.message, "error");
    }
}

// Make functions globally available
window.generateCharacterPortraits = generateCharacterPortraits;
window.viewCharacterSheet = viewCharacterSheet;



// ============================================================================
// AUDIOBOOK SUBTITLES FEATURE
// ============================================================================

let subtitleText = '';
let subtitleWords = [];
let subtitleIndex = 0;
let subtitleContainer = null;

function initSubtitles(text) {
    subtitleText = text;
    subtitleWords = text.split(/\s+/);
    subtitleIndex = 0;

    // Create subtitle container if it doesn't exist
    subtitleContainer = document.getElementById('subtitle-display');
    if (!subtitleContainer) {
        subtitleContainer = document.createElement('div');
        subtitleContainer.id = 'subtitle-display';
        subtitleContainer.className = 'subtitle-display';

        // Insert after audio player
        const audioPlayer = document.querySelector('.audio-player-ui');
        if (audioPlayer) {
            audioPlayer.appendChild(subtitleContainer);
        }
    }

    subtitleContainer.innerHTML = '<span class="subtitle-text">Click play to see subtitles...</span>';
    subtitleContainer.style.display = 'block';
}

function updateSubtitles(audioProgress, audioDuration) {
    if (!subtitleContainer || !subtitleWords.length) return;

    // Calculate which word we should be at based on progress
    const progress = audioProgress / audioDuration;
    const targetIndex = Math.floor(progress * subtitleWords.length);

    // Show a window of words around the current position
    const windowSize = 12;
    const start = Math.max(0, targetIndex - Math.floor(windowSize / 2));
    const end = Math.min(subtitleWords.length, start + windowSize);

    const displayWords = subtitleWords.slice(start, end);
    const currentWordInWindow = targetIndex - start;

    // Highlight the current word
    const html = displayWords.map((word, i) => {
        if (i === currentWordInWindow) {
            return `<span class="current-word">${word}</span>`;
        }
        return `<span class="other-word">${word}</span>`;
    }).join(' ');

    subtitleContainer.innerHTML = `<span class="subtitle-text">${html}</span>`;
}

function hideSubtitles() {
    if (subtitleContainer) {
        subtitleContainer.style.display = 'none';
    }
}

// Make functions global
window.initSubtitles = initSubtitles;
window.updateSubtitles = updateSubtitles;
window.hideSubtitles = hideSubtitles;



// ============================================================================
// THREE-PANEL LAYOUT -- COLLAPSE and RESIZE
// ============================================================================

(function initPanels() {
    const layout = document.getElementById('nb-layout');
    if (!layout) return;

    const btnRight = document.getElementById('btn-collapse-right');

    if (btnRight) {
        btnRight.addEventListener('click', function() {
            layout.classList.toggle('right-collapsed');
            // Rotate the chevron SVG icon
            const svg = btnRight.querySelector('svg');
            if (svg) {
                svg.style.transition = 'transform 0.3s ease';
                svg.style.transform = layout.classList.contains('right-collapsed')
                    ? 'rotate(180deg)' : 'rotate(0deg)';
            }
        });
    }

    function makeDraggable(handleId, cssVar, side) {
        var handle = document.getElementById(handleId);
        if (!handle) return;
        var startX, startW;
        handle.addEventListener('mousedown', function(e) {
            e.preventDefault();
            startX = e.clientX;
            startW = parseInt(getComputedStyle(layout).getPropertyValue(cssVar)) || (side === 'left' ? 260 : 340);
            handle.classList.add('dragging');
            function onMove(e) {
                var delta = side === 'left' ? e.clientX - startX : startX - e.clientX;
                var newW = Math.max(52, Math.min(500, startW + delta));
                layout.style.setProperty(cssVar, newW + 'px');
                if (newW > 60) layout.classList.remove(side === 'left' ? 'left-collapsed' : 'right-collapsed');
            }
            function onUp() {
                handle.classList.remove('dragging');
                document.removeEventListener('mousemove', onMove);
                document.removeEventListener('mouseup', onUp);
            }
            document.addEventListener('mousemove', onMove);
            document.addEventListener('mouseup', onUp);
        });
    }

    makeDraggable('resize-left',  '--nb-left',  'left');
    makeDraggable('resize-right', '--nb-right', 'right');
})();

// ============================================================================
// ONBOARDING TOUR
// ============================================================================

(function() {
    // Tour state
    let tourActive = false;
    let tourStep = 0;
    let tourSteps = [];
    let spotlightEl = null;
    let tooltipEl = null;

    // Two sets of steps: one for the hero/upload page, one for the dashboard
    const HERO_STEPS = [
        {
            target: '#drop-zone',
            title: 'Upload Your Book',
            desc: 'Drag & drop a PDF, EPUB, or TXT file here — or click Browse to pick one. Our AI will instantly analyze the content.',
            pos: 'bottom'
        },
        {
            target: '.nav-links',
            title: 'Navigate Anywhere',
            desc: 'Switch between Home, your Library of saved books, and learn About the project.',
            pos: 'bottom'
        },
        {
            target: '.logo',
            title: 'You\'re All Set! 🚀',
            desc: 'Upload a book to unlock the full experience — AI audiobooks, visual scenes, podcasts, and an intelligent chat assistant.',
            pos: 'bottom'
        }
    ];

    const DASHBOARD_STEPS = [
        {
            target: '#nb-panel-left',
            title: 'Meet the Characters',
            desc: 'Every character detected in your book appears here with an AI-generated portrait. Scroll to explore them all.',
            pos: 'right'
        },
        {
            target: '#qa-chat-container',
            title: 'Ask Anything',
            desc: 'Chat with an AI that has read the entire book. Ask about plot twists, character motivations, themes — anything!',
            pos: 'left'
        },
        {
            target: '.nb-chat-input-bar',
            title: 'Type Your Question',
            desc: 'Just type a question and press Enter or click Send. You can also try the suggested questions.',
            pos: 'top'
        },
        {
            target: '.nb-studio-grid',
            title: 'Create Content',
            desc: 'Generate audiobooks, podcasts, visual scenes, or export everything. Each button opens a dedicated workflow.',
            pos: 'left'
        },
        {
            target: '#nb-panel-right',
            title: 'Your Creative Studio',
            desc: 'This panel is your control center for generating and previewing multimedia content from the book. Try Visuals first!',
            pos: 'left'
        }
    ];

    function getActiveSteps() {
        const dashboard = document.getElementById('dashboard');
        if (dashboard && !dashboard.classList.contains('hidden')) {
            return DASHBOARD_STEPS;
        }
        return HERO_STEPS;
    }

    function createSpotlight() {
        if (spotlightEl) spotlightEl.remove();
        spotlightEl = document.createElement('div');
        spotlightEl.className = 'tour-spotlight';
        document.body.appendChild(spotlightEl);
        // Click the dark area to dismiss
        spotlightEl.addEventListener('click', endTour);
    }

    function createTooltip() {
        if (tooltipEl) tooltipEl.remove();
        tooltipEl = document.createElement('div');
        tooltipEl.className = 'tour-tooltip';
        document.body.appendChild(tooltipEl);
    }

    function positionSpotlight(rect, pad) {
        pad = pad || 8;
        spotlightEl.style.top    = (rect.top - pad) + 'px';
        spotlightEl.style.left   = (rect.left - pad) + 'px';
        spotlightEl.style.width  = (rect.width + pad * 2) + 'px';
        spotlightEl.style.height = (rect.height + pad * 2) + 'px';
    }

    function positionTooltip(rect, pos) {
        tooltipEl.setAttribute('data-pos', pos);
        var gap = 16;
        var tw = 320; // tooltip width
        var th = tooltipEl.offsetHeight || 180;

        var top, left;
        switch (pos) {
            case 'bottom':
                top = rect.bottom + gap;
                left = rect.left;
                break;
            case 'top':
                top = rect.top - th - gap;
                left = rect.left;
                break;
            case 'right':
                top = rect.top;
                left = rect.right + gap;
                break;
            case 'left':
                top = rect.top;
                left = rect.left - tw - gap;
                break;
        }

        // Clamp to viewport
        left = Math.max(16, Math.min(left, window.innerWidth - tw - 16));
        top = Math.max(16, Math.min(top, window.innerHeight - th - 16));

        tooltipEl.style.top  = top + 'px';
        tooltipEl.style.left = left + 'px';
    }

    function renderTooltip(step, index, total) {
        var dotsHTML = '';
        for (var i = 0; i < total; i++) {
            dotsHTML += '<span class="tour-dot' + (i === index ? ' active' : '') + '"></span>';
        }

        var isLast = index === total - 1;

        tooltipEl.innerHTML = 
            '<div class="tour-tooltip-arrow"></div>' +
            '<div class="tour-step-num">Step ' + (index + 1) + ' of ' + total + '</div>' +
            '<div class="tour-title">' + step.title + '</div>' +
            '<div class="tour-desc">' + step.desc + '</div>' +
            '<div class="tour-nav">' +
                '<div class="tour-dots">' + dotsHTML + '</div>' +
                '<div style="display:flex;gap:0.5rem;align-items:center">' +
                    '<button class="tour-btn-skip" onclick="endTour()">Skip</button>' +
                    '<button class="tour-btn-next" onclick="nextTourStep()">' + (isLast ? 'Finish ✓' : 'Next →') + '</button>' +
                '</div>' +
            '</div>';
    }

    function showStep(index) {
        tourStep = index;
        var steps = getActiveSteps();
        if (index >= steps.length) { endTour(); return; }

        var step = steps[index];
        var el = document.querySelector(step.target);
        if (!el) { 
            // Skip invisible steps
            if (index < steps.length - 1) showStep(index + 1);
            else endTour();
            return;
        }

        // Scroll into view if needed
        el.scrollIntoView({ behavior: 'smooth', block: 'nearest' });

        // Small delay for scroll to settle
        setTimeout(function() {
            var rect = el.getBoundingClientRect();
            positionSpotlight(rect);
            renderTooltip(step, index, steps.length);
            positionTooltip(rect, step.pos);
            el.classList.add('tour-highlighted');
        }, 150);
    }

    // Public API
    window.startTour = function(force) {
        tourActive = true;
        tourStep = 0;
        tourSteps = getActiveSteps();
        createSpotlight();
        createTooltip();
        showStep(0);
    };

    window.nextTourStep = function() {
        // Remove highlight from current element
        var steps = getActiveSteps();
        if (tourStep < steps.length) {
            var prev = document.querySelector(steps[tourStep].target);
            if (prev) prev.classList.remove('tour-highlighted');
        }
        showStep(tourStep + 1);
    };

    window.endTour = function() {
        tourActive = false;
        // Cleanup highlights
        document.querySelectorAll('.tour-highlighted').forEach(function(el) {
            el.classList.remove('tour-highlighted');
        });
        if (spotlightEl) { spotlightEl.remove(); spotlightEl = null; }
        if (tooltipEl) { tooltipEl.remove(); tooltipEl = null; }
        // Mark as seen
        localStorage.setItem('b2v_tour_seen', '1');
    };

    // Auto-start tour for first-time visitors (after page load)
    window.addEventListener('load', function() {
        if (!localStorage.getItem('b2v_tour_seen')) {
            setTimeout(function() { startTour(); }, 800);
        }
    });

    // Handle window resize during tour
    window.addEventListener('resize', function() {
        if (tourActive && spotlightEl && tooltipEl) {
            var steps = getActiveSteps();
            if (tourStep < steps.length) {
                var el = document.querySelector(steps[tourStep].target);
                if (el) {
                    var rect = el.getBoundingClientRect();
                    positionSpotlight(rect);
                    positionTooltip(rect, steps[tourStep].pos);
                }
            }
        }
    });

    // Keyboard: Escape to close, Right arrow / Enter to advance
    document.addEventListener('keydown', function(e) {
        if (!tourActive) return;
        if (e.key === 'Escape') endTour();
        if (e.key === 'ArrowRight' || e.key === 'Enter') nextTourStep();
    });
})();
