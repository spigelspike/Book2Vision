
content = open('web/index.html', 'r', encoding='utf-8').read()

# Replace the entire dashboard section with the new NotebookLM-style layout
old = '''        <!-- Dashboard (Hidden initially) -->

        <section id="dashboard" class="container hidden fade-in" aria-label="Book Dashboard">



            <!-- Top Bar: Book Info & Settings -->

            <div class="dashboard-header glass">

                <div class="book-info">

                    <h2 id="book-title">Book Title</h2>

                    <p id="book-author">Author Name</p>

                </div>



                <div class="controls-group">

                    <div class="control-item">

                        <label for="audio-provider">Audio Provider</label>

                        <select id="audio-provider" class="glass-input">

                            <option value="deepgram">Deepgram (Fast)</option>

                            <option value="elevenlabs">ElevenLabs (High Quality)</option>

                            <option value="inbuilt">Inbuilt (Free)</option>

                        </select>

                    </div>



                    <div class="control-item">

                        <label for="style-select">Art Style</label>

                        <select id="style-select" class="glass-input">

                            <option value="storybook">Storybook</option>

                            <option value="cinematic">Cinematic</option>

                            <option value="anime">Anime</option>

                            <option value="watercolor">Watercolor</option>

                            <option value="cyberpunk">Cyberpunk</option>

                            <option value="fantasy">Fantasy</option>

                        </select>

                    </div>



                    <button class="btn-icon" onclick="toggleSettings()" title="Advanced Settings"
                        aria-label="Advanced Settings">&#9775;</button>

                </div>'''

new = '''        <!-- Dashboard (Hidden initially) -->

        <section id="dashboard" class="nb-dashboard hidden fade-in" aria-label="Book Dashboard">

            <!-- ── Hidden settings selects (used by JS, not shown in new layout) ── -->
            <select id="audio-provider" class="hidden" aria-hidden="true">
                <option value="deepgram">Deepgram (Fast)</option>
                <option value="elevenlabs">ElevenLabs (High Quality)</option>
                <option value="inbuilt">Inbuilt (Free)</option>
            </select>
            <select id="style-select" class="hidden" aria-hidden="true">
                <option value="storybook">Storybook</option>
                <option value="cinematic">Cinematic</option>
                <option value="anime">Anime</option>
                <option value="watercolor">Watercolor</option>
                <option value="cyberpunk">Cyberpunk</option>
                <option value="fantasy">Fantasy</option>
            </select>'''

content = content.replace(old, new)

# Also fix the nb-layout block - restructure center panel properly
# Replace center panel section to have chat first (scrollable), then audio pinned at bottom
old_center = '''                <!-- CENTER PANEL: Audio + Chat -->
                <div class="nb-panel nb-panel-center" id="nb-panel-center">
                    <div class="nb-center-inner">

                        <!-- Audio Player (original markup preserved) -->
                        <div class="audio-player-ui glass nb-audio-block">
                            <div class="bg-waveform" aria-hidden="true">
                                <span></span><span></span><span></span>
                            </div>
                            <div class="player-header">
                                <h3>Audiobook Player</h3>
                                <div class="header-controls" style="display:flex;gap:0.5rem;">
                                    <button id="btn-audio" class="btn-sm">
                                        <span class="icon" aria-hidden="true">&#9834;</span> Generate Audiobook
                                    </button>
                                    <button id="btn-podcast" class="btn-sm btn-podcast">
                                        <span class="icon" aria-hidden="true">&#127897;&#65039;</span> Generate Podcast
                                    </button>
                                </div>
                            </div>
                            <!-- Podcast Player -->
                            <div id="podcast-player-ui" class="podcast-player hidden fade-in" aria-label="Podcast Player">
                                <div class="podcast-header">
                                    <span style="font-size:1.2rem;" aria-hidden="true">&#127908;</span>
                                    <div style="flex:1;margin-left:0.5rem;">
                                        <div style="font-weight:700;font-size:0.9rem;">Booked &amp; Busy</div>
                                        <div style="font-size:0.75rem;opacity:0.8;">with Jax &amp; Emma</div>
                                    </div>
                                    <button class="btn-icon-sm" onclick="closePodcast()" aria-label="Close Podcast">&#10005;</button>
                                </div>
                                <div class="podcast-visualizer" aria-hidden="true">
                                    <div class="speaker-avatar" id="podcast-avatar">&#9997;&#127996;</div>
                                    <div class="podcast-wave">
                                        <span></span><span></span><span></span><span></span><span></span>
                                    </div>
                                </div>
                                <div class="podcast-transcript" id="podcast-transcript" aria-live="polite">
                                    Generating script...
                                </div>
                            </div>
                            <div class="audio-visualizer" aria-hidden="true">
                                <div class="bar"></div><div class="bar"></div><div class="bar"></div>
                                <div class="bar"></div><div class="bar"></div><div class="bar"></div>
                                <div class="bar"></div><div class="bar"></div><div class="bar"></div>
                                <div class="bar"></div><div class="bar"></div><div class="bar"></div>
                                <div class="bar"></div><div class="bar"></div><div class="bar"></div>
                                <div class="bar"></div><div class="bar"></div><div class="bar"></div>
                                <div class="bar"></div><div class="bar"></div><div class="bar"></div>
                                <div class="bar"></div><div class="bar"></div><div class="bar"></div>
                            </div>
                            <div class="progress-container" id="progress-container" role="slider"
                                aria-label="Audio Progress" aria-valuemin="0" aria-valuemax="100" aria-valuenow="0"
                                tabindex="0">
                                <div class="progress-bar" id="audio-progress"></div>
                                <div class="progress-hover" id="progress-hover"></div>
                            </div>
                            <div class="time-display">
                                <span id="current-time">0:00</span> / <span id="total-time">0:00</span>
                            </div>
                            <div class="player-controls">
                                <button class="btn-control" onclick="skip(-15)" aria-label="Rewind 15 seconds">&#8634; 15s</button>
                                <button class="btn-play" id="btn-play-pause" aria-label="Play or Pause">&#9654;</button>
                                <button class="btn-control" onclick="skip(15)" aria-label="Forward 15 seconds">15s &#8635;</button>
                            </div>
                            <audio id="audio-player" hidden></audio>
                        </div>

                        <!-- Inline Chat -->
                        <div class="nb-chat-inline">
                            <div class="nb-chat-thread" id="qa-chat-container" aria-live="polite">
                                <div class="chat-message system">
                                    Ask any question about the plot, characters, or themes!
                                </div>
                            </div>
                            <div class="qa-suggestions" id="qa-suggestions"></div>
                            <div class="nb-chat-input-row">
                                <input type="text" id="qa-input" placeholder="Ask a question about the book..."
                                    class="glass-input qa-input" autocomplete="off" aria-label="Chat input">
                                <button class="btn-send" id="btn-send-qa" aria-label="Send message">&#10148;</button>
                            </div>
                        </div>

                    </div>
                </div>'''

new_center = '''                <!-- CENTER PANEL: Chat (primary) + Pinned Audio at bottom -->
                <div class="nb-panel nb-panel-center" id="nb-panel-center">
                    <!-- Panel header -->
                    <div class="nb-panel-header nb-center-header">
                        <div class="nb-center-title">
                            <h2 id="book-title" class="nb-book-title">Book Title</h2>
                            <span id="book-author" class="nb-book-author">Author Name</span>
                        </div>
                        <div class="nb-header-actions">
                            <button class="nb-icon-btn" onclick="toggleSettings()" title="Settings" aria-label="Settings">
                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>
                            </button>
                        </div>
                    </div>

                    <!-- Scrollable chat thread -->
                    <div class="nb-chat-thread" id="qa-chat-container" aria-live="polite">
                        <div class="chat-message system">
                            Ask any question about the plot, characters, or themes!
                        </div>
                    </div>

                    <!-- Suggestion chips -->
                    <div class="qa-suggestions" id="qa-suggestions"></div>

                    <!-- Chat input bar -->
                    <div class="nb-chat-input-bar">
                        <input type="text" id="qa-input" placeholder="Start typing..."
                            class="glass-input qa-input" autocomplete="off" aria-label="Chat input">
                        <span class="nb-source-count">1 source</span>
                        <button class="nb-send-btn" id="btn-send-qa" aria-label="Send message">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/></svg>
                        </button>
                    </div>

                    <!-- PINNED AUDIO PLAYER at very bottom of center column -->
                    <div class="nb-audio-dock" id="nb-audio-dock">
                        <!-- Podcast Player (hidden initially) -->
                        <div id="podcast-player-ui" class="podcast-player hidden fade-in" aria-label="Podcast Player">
                            <div class="podcast-header">
                                <span style="font-size:1.1rem;" aria-hidden="true">&#127908;</span>
                                <div style="flex:1;margin-left:0.5rem;">
                                    <div style="font-weight:700;font-size:0.85rem;">Booked &amp; Busy</div>
                                    <div style="font-size:0.72rem;opacity:0.7;">with Jax &amp; Emma</div>
                                </div>
                                <button class="btn-icon-sm" onclick="closePodcast()" aria-label="Close Podcast">&#10005;</button>
                            </div>
                            <div class="podcast-visualizer" aria-hidden="true">
                                <div class="speaker-avatar" id="podcast-avatar">&#9997;&#127996;</div>
                                <div class="podcast-wave">
                                    <span></span><span></span><span></span><span></span><span></span>
                                </div>
                            </div>
                            <div class="podcast-transcript" id="podcast-transcript" aria-live="polite">Generating script...</div>
                        </div>

                        <!-- Waveform visualizer -->
                        <div class="nb-dock-wave" aria-hidden="true">
                            <div class="audio-visualizer">
                                <div class="bar"></div><div class="bar"></div><div class="bar"></div>
                                <div class="bar"></div><div class="bar"></div><div class="bar"></div>
                                <div class="bar"></div><div class="bar"></div><div class="bar"></div>
                                <div class="bar"></div><div class="bar"></div><div class="bar"></div>
                                <div class="bar"></div><div class="bar"></div><div class="bar"></div>
                                <div class="bar"></div><div class="bar"></div><div class="bar"></div>
                                <div class="bar"></div><div class="bar"></div><div class="bar"></div>
                                <div class="bar"></div><div class="bar"></div><div class="bar"></div>
                            </div>
                        </div>

                        <!-- Progress + time -->
                        <div class="nb-dock-progress">
                            <span id="current-time" class="nb-time">0:00</span>
                            <div class="progress-container" id="progress-container" role="slider"
                                aria-label="Audio Progress" aria-valuemin="0" aria-valuemax="100" aria-valuenow="0"
                                tabindex="0">
                                <div class="progress-bar" id="audio-progress"></div>
                                <div class="progress-hover" id="progress-hover"></div>
                            </div>
                            <span id="total-time" class="nb-time">0:00</span>
                        </div>

                        <!-- Controls row -->
                        <div class="nb-dock-controls">
                            <div class="nb-dock-left">
                                <button id="btn-audio" class="btn-sm nb-dock-gen-btn">
                                    <span aria-hidden="true">&#9834;</span> Generate
                                </button>
                                <button id="btn-podcast" class="btn-sm btn-podcast nb-dock-gen-btn">
                                    <span aria-hidden="true">&#127897;&#65039;</span> Podcast
                                </button>
                            </div>
                            <div class="nb-dock-center-controls">
                                <button class="btn-control" onclick="skip(-15)" aria-label="Rewind 15 seconds">
                                    <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M12 5V1L7 6l5 5V7c3.31 0 6 2.69 6 6s-2.69 6-6 6-6-2.69-6-6H4c0 4.42 3.58 8 8 8s8-3.58 8-8-3.58-8-8-8z"/><text x="9" y="15" font-size="7" fill="currentColor">15</text></svg>
                                </button>
                                <button class="btn-play" id="btn-play-pause" aria-label="Play or Pause">&#9654;</button>
                                <button class="btn-control" onclick="skip(15)" aria-label="Forward 15 seconds">
                                    <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M12 5V1l5 5-5 5V7c-3.31 0-6 2.69-6 6s2.69 6 6 6 6-2.69 6-6h2c0 4.42-3.58 8-8 8s-8-3.58-8-8 3.58-8 8-8z"/><text x="9" y="15" font-size="7" fill="currentColor">15</text></svg>
                                </button>
                            </div>
                            <div class="nb-dock-right">
                                <!-- speed/volume placeholders for future -->
                            </div>
                        </div>

                        <audio id="audio-player" hidden></audio>
                    </div>
                </div>'''

content = content.replace(old_center, new_center)

# Fix the right panel to show Studio (not just Visuals)
old_right = '''                <!-- RIGHT PANEL: Visuals -->
                <div class="nb-panel nb-panel-right glass" id="nb-panel-right">
                    <div class="nb-panel-header">
                        <h3><span>&#127912;</span> <span class="nb-panel-label">Visuals</span></h3>
                        <div class="nb-header-actions">
                            <button class="nb-collapse-btn" id="btn-collapse-right" aria-label="Collapse panel">&#9654;</button>
                        </div>
                    </div>
                    <div class="nb-panel-body">
                        <div class="nb-visuals-generate">
                            <button id="btn-visuals" class="btn-sm nb-generate-btn">
                                <span class="icon" aria-hidden="true">&#127912;</span> Generate Visuals
                            </button>
                        </div>
                        <div class="carousel-container">
                            <button class="carousel-btn prev" onclick="prevImage()" aria-label="Previous Image">&#10094;</button>
                            <div class="image-display" id="image-display" aria-label="Generated Visuals">
                                <div class="placeholder-content">
                                    <div class="icon-large" aria-hidden="true">&#128444;&#65039;</div>
                                    <p>Generate visuals to see the story come to life.</p>
                                </div>
                            </div>
                            <button class="carousel-btn next" onclick="nextImage()" aria-label="Next Image">&#10095;</button>
                            <div class="carousel-counter" id="carousel-counter">0/0</div>
                        </div>
                        <div class="carousel-indicators" id="carousel-indicators"></div>
                    </div>
                </div>'''

new_right = '''                <!-- RIGHT PANEL: Studio -->
                <div class="nb-panel nb-panel-right glass" id="nb-panel-right">
                    <div class="nb-panel-header">
                        <h3><span>&#127916;</span> <span class="nb-panel-label">Studio</span></h3>
                        <div class="nb-header-actions">
                            <button class="nb-collapse-btn" id="btn-collapse-right" aria-label="Collapse panel">&#9654;</button>
                        </div>
                    </div>
                    <div class="nb-panel-body">

                        <!-- Generate section -->
                        <p class="nb-section-label">GENERATE</p>
                        <div class="nb-studio-grid">
                            <button class="nb-studio-card" id="btn-audio">
                                <span class="nb-studio-icon">&#9834;</span>
                                <span>Audiobook</span>
                                <span class="nb-card-arrow">&#8250;</span>
                            </button>
                            <button class="nb-studio-card btn-podcast" id="btn-podcast">
                                <span class="nb-studio-icon">&#127897;&#65039;</span>
                                <span>Podcast</span>
                                <span class="nb-card-arrow">&#8250;</span>
                            </button>
                            <button class="nb-studio-card" id="btn-visuals">
                                <span class="nb-studio-icon">&#127912;</span>
                                <span>Visuals</span>
                                <span class="nb-card-arrow">&#8250;</span>
                            </button>
                            <button class="nb-studio-card" onclick="exportAll && exportAll()">
                                <span class="nb-studio-icon">&#128228;</span>
                                <span>Export All</span>
                                <span class="nb-card-arrow">&#8250;</span>
                            </button>
                        </div>

                        <!-- Art style + audio provider inline -->
                        <p class="nb-section-label" style="margin-top:1rem;">SETTINGS</p>
                        <div class="nb-settings-row">
                            <div class="nb-setting-item">
                                <label for="audio-provider-vis">Audio</label>
                                <select id="audio-provider-vis" class="glass-input nb-setting-select" onchange="document.getElementById('audio-provider').value=this.value">
                                    <option value="deepgram">Deepgram</option>
                                    <option value="elevenlabs">ElevenLabs</option>
                                    <option value="inbuilt">Inbuilt</option>
                                </select>
                            </div>
                            <div class="nb-setting-item">
                                <label for="style-select-vis">Art Style</label>
                                <select id="style-select-vis" class="glass-input nb-setting-select" onchange="document.getElementById('style-select').value=this.value">
                                    <option value="storybook">Storybook</option>
                                    <option value="cinematic">Cinematic</option>
                                    <option value="anime">Anime</option>
                                    <option value="watercolor">Watercolor</option>
                                    <option value="cyberpunk">Cyberpunk</option>
                                    <option value="fantasy">Fantasy</option>
                                </select>
                            </div>
                        </div>

                        <!-- Visuals section -->
                        <p class="nb-section-label" style="margin-top:1rem;">VISUALS</p>
                        <div class="carousel-container nb-carousel">
                            <button class="carousel-btn prev" onclick="prevImage()" aria-label="Previous Image">&#10094;</button>
                            <div class="image-display" id="image-display" aria-label="Generated Visuals">
                                <div class="placeholder-content">
                                    <div class="icon-large" aria-hidden="true">&#128444;&#65039;</div>
                                    <p>Generate visuals to see the story come to life.</p>
                                </div>
                            </div>
                            <button class="carousel-btn next" onclick="nextImage()" aria-label="Next Image">&#10095;</button>
                            <div class="carousel-counter" id="carousel-counter">0/0</div>
                        </div>
                        <div class="carousel-indicators" id="carousel-indicators"></div>

                    </div>
                </div>'''

content = content.replace(old_right, new_right)

open('web/index.html', 'w', encoding='utf-8').write(content)
print('Done. Lines:', content.count('\n'))
