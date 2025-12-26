// ============================================
// CONFIGURATION & STATE
// ============================================

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

// Default Settings
const DEFAULT_SETTINGS = {
    voiceId: "21m00Tcm4TlvDq8ikWAM",
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
    setupEventListeners();
    // Initialize settings if not present
    if (!localStorage.getItem('b2v_settings')) {
        localStorage.setItem('b2v_settings', JSON.stringify(DEFAULT_SETTINGS));
    }

    // Page-specific logic
    const path = window.location.pathname;
    if (path.includes('library.html')) {
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
    if (btnPodcast) btnPodcast.addEventListener('click', generatePodcast);

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
    // Only fetch if we don't already have the full text
    if (!currentStoryText || currentStoryText.length < 500) {
        try {
            const res = await fetch(`${API_BASE}/story`);
            const data = await res.json();
            currentStoryText = data.body; // Update with full text for better audio/QA
        } catch (e) {
            console.warn("Failed to fetch full story text, using summary.");
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
        card.className = 'entity-card fade-in-element';
        const imgId = `img-${name.replace(/[^a-zA-Z0-9]/g, '')}`;

        card.innerHTML = `
            <img src="https://ui-avatars.com/api/?name=${encodeURIComponent(name)}&background=random" class="entity-img" id="${imgId}">
            <div style="font-weight:600; font-size: 0.95rem;">${name}</div>
            <div style="font-size:0.75rem; opacity:0.7; margin-top: -0.3rem;">${role}</div>
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
        const res = await fetch(`${API_BASE}/generate/audio`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                text: currentStoryText.substring(0, 3000), // Send only what's needed (preview)
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

    // Prevent race conditions from rapid clicking
    if (isTogglingAudio) return;
    isTogglingAudio = true;

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
        ui.classList.remove('playing');
        isTogglingAudio = false;
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

// --- Visuals ---

// ============================================
// VISUAL GENERATION
// ============================================

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
}

// --- Podcast ---

let podcastPlaylist = [];
let currentPodcastIndex = 0;

async function generatePodcast() {
    const originalText = btnPodcast.innerHTML;
    btnPodcast.innerHTML = '<span class="icon">⏳</span> Scripting...';
    btnPodcast.disabled = true;

    // Stop Audiobook if playing
    if (isPlaying) {
        toggleAudio();
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
    msg.className = `chat-message ${type} fade-in-element`;
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

// --- Library ---

// ============================================
// LIBRARY MANAGEMENT
// ============================================

let libraryBooks = [];

async function fetchLibrary() {
    try {
        // Show skeletons
        const grid = document.getElementById('library-grid');
        if (grid) {
            grid.innerHTML = Array(6).fill(0).map(() => `
                <div class="book-card glass skeleton-card" style="height: 200px;"></div>
            `).join('');
        }

        const res = await fetch(`${API_BASE}/library`);
        const data = await res.json();
        libraryBooks = data.books;
        renderLibrary();
    } catch (e) {
        showToast("Failed to load library", "error");
    }
}

function renderLibrary() {
    const grid = document.getElementById('library-grid');
    if (!grid) return; // Guard clause for non-library pages

    const searchTerm = document.getElementById('library-search').value.toLowerCase();
    const sortMethod = document.getElementById('library-sort').value;

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
        card.className = 'book-card glass fade-in-element';

        // Format date
        const date = new Date(book.upload_date * 1000).toLocaleDateString();

        let thumbContent = `<div class="book-card-icon">📖</div>`;
        if (book.thumbnail) {
            thumbContent = `<img src="/api/assets/${book.thumbnail}" alt="${book.title}" class="book-card-img">`;
        }

        card.innerHTML = `
            <div class="book-card-thumb">
                ${thumbContent}
            </div>
            <div class="book-card-info">
                <h3 class="book-card-title">${book.title}</h3>
                <p class="book-card-author">${book.author}</p>
                <p class="book-card-date">Added ${date}</p>
            </div>
            <div class="book-card-actions">
                <button class="btn-sm" onclick="openBook('${book.id}')">Open</button>
                <button class="btn-icon-sm" onclick="deleteBook('${book.id}')" title="Delete">🗑️</button>
            </div>
        `;
        grid.appendChild(card);
    });
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
