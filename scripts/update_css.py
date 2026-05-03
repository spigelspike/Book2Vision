
import os

file_path = r"c:\Users\share\Desktop\PROJECT\book2visionn\web\style.css"

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Target block to replace
target_block = """/* 3. Visuals: Restore Slider Layout */
.image-display {
  display: flex;
  flex-wrap: wrap;
  /* Allow wrapping */
  justify-content: center;
  align-items: center;
  overflow: visible;
  /* Remove scroll */
  scroll-snap-type: none;
  gap: var(--space-md);
  background: transparent;
  /* Remove dark bg */
  border: none;
  /* Remove border */
}

.image-wrapper {
  min-width: auto;
  /* Remove full width forcing */
  height: auto;
  max-width: 100%;
  scroll-snap-align: none;
}

.generated-img {
  max-height: 500px;
  /* Limit height */
  width: auto;
  /* Maintain aspect ratio */
  border-radius: var(--radius-md);
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.4);
}"""

# New content
new_content_block = """/* 3. Visuals: Restore Slider Layout */
.image-display {
  display: flex;
  flex-wrap: nowrap;
  /* Prevent wrapping */
  justify-content: flex-start;
  /* Align start for scrolling */
  align-items: center;
  overflow-x: auto;
  /* Enable horizontal scroll */
  scroll-snap-type: x mandatory;
  gap: 0;
  /* Remove gap for full width slider */
  background: #000;
  border: 1px dashed var(--glass-border);
}

.image-wrapper {
  min-width: 100%;
  /* Force full width */
  height: 100%;
  scroll-snap-align: center;
  padding: var(--space-sm);
  display: flex;
  align-items: center;
  justify-content: center;
}

.generated-img {
  max-height: 90%;
  max-width: 90%;
  width: auto;
  height: auto;
  object-fit: contain;
  border-radius: var(--radius-md);
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.4);
}

/* --- Music Player Visualizer Animation --- */
@keyframes sound {
  0% {
    height: 10%;
  }

  50% {
    height: 100%;
  }

  100% {
    height: 10%;
  }
}

.audio-player-ui.playing .bar {
  animation: sound 1.2s linear infinite;
}

.audio-player-ui.playing .bar:nth-child(1) {
  animation-delay: 0.1s;
}

.audio-player-ui.playing .bar:nth-child(2) {
  animation-delay: 0.3s;
}

.audio-player-ui.playing .bar:nth-child(3) {
  animation-delay: 0.5s;
}

.audio-player-ui.playing .bar:nth-child(4) {
  animation-delay: 0.2s;
}

.audio-player-ui.playing .bar:nth-child(5) {
  animation-delay: 0.4s;
}

.audio-player-ui.playing .bar:nth-child(6) {
  animation-delay: 0.6s;
}

.audio-player-ui.playing .bar:nth-child(7) {
  animation-delay: 0.1s;
}

.audio-player-ui.playing .bar:nth-child(8) {
  animation-delay: 0.3s;
}

.audio-player-ui.playing .bar:nth-child(9) {
  animation-delay: 0.5s;
}

.audio-player-ui.playing .bar:nth-child(10) {
  animation-delay: 0.2s;
}

.audio-player-ui.playing .bar:nth-child(11) {
  animation-delay: 0.4s;
}

.audio-player-ui.playing .bar:nth-child(12) {
  animation-delay: 0.6s;
}"""

# Perform replacement
if target_block in content:
    new_content = content.replace(target_block, new_content_block)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print("Successfully replaced CSS content.")
else:
    print("Target block not found in file.")
    # Debug: print a part of the file to see what's wrong
    start_idx = content.find("/* 3. Visuals: Restore Slider Layout */")
    if start_idx != -1:
        print(f"Found start at {start_idx}. Next 500 chars:")
        print(content[start_idx:start_idx+500])
