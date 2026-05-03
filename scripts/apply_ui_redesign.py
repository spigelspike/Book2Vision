"""
UI/UX Redesign Script for Book2Vision
Applies modern styling enhancements while preserving all existing features.
"""
import os
import re

# Read the existing CSS
css_path = os.path.join(os.path.dirname(__file__), 'web', 'style.css')
with open(css_path, 'r', encoding='utf-8') as f:
    css_content = f.read()

# ============================================================================
# ENHANCED CSS ADDITIONS
# ============================================================================

NEW_CSS_ENHANCEMENTS = '''

/* ============================================================================
   UI/UX REDESIGN ENHANCEMENTS - v2.0
   Modern, polished interface with improved visual hierarchy
============================================================================ */

/* --- Enhanced Dashboard Grid (Better Proportions) --- */
.dashboard-grid {
  display: grid;
  grid-template-columns: 260px 1fr 380px;
  gap: var(--space-lg);
  align-items: stretch;
}

@media (max-width: 1400px) {
  .dashboard-grid {
    grid-template-columns: 240px 1fr 320px;
    gap: var(--space-md);
  }
}

@media (max-width: 1100px) {
  .dashboard-grid {
    grid-template-columns: 1fr;
    gap: var(--space-lg);
  }
  
  .panel-left, .panel-image {
    min-height: auto;
  }
}

/* --- Enhanced Audio Player (Hero Section) --- */
.audio-player-ui {
  padding: var(--space-lg) var(--space-xl);
  position: relative;
  overflow: hidden;
  background: linear-gradient(145deg, rgba(25, 25, 30, 0.9), rgba(15, 15, 18, 0.95));
  border: 1px solid rgba(127, 90, 240, 0.15);
  box-shadow: 
    0 20px 60px rgba(0, 0, 0, 0.5),
    inset 0 1px 0 rgba(255, 255, 255, 0.05);
}

.audio-player-ui::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(127, 90, 240, 0.5), transparent);
}

/* --- Waveform Visualizer Enhancement --- */
.audio-visualizer {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 4px;
  height: 80px;
  margin: var(--space-md) 0;
  padding: var(--space-sm) 0;
  position: relative;
}

.audio-visualizer .bar {
  width: 4px;
  min-height: 8px;
  background: linear-gradient(180deg, var(--primary), rgba(127, 90, 240, 0.4));
  border-radius: 4px;
  height: 15%;
  transition: height 0.15s ease-out;
  box-shadow: 0 0 8px rgba(127, 90, 240, 0.4);
}

.audio-player-ui.playing .audio-visualizer .bar {
  animation: audioWave 0.8s ease-in-out infinite;
}

.audio-visualizer .bar:nth-child(1) { animation-delay: 0s; }
.audio-visualizer .bar:nth-child(2) { animation-delay: 0.1s; }
.audio-visualizer .bar:nth-child(3) { animation-delay: 0.2s; }
.audio-visualizer .bar:nth-child(4) { animation-delay: 0.15s; }
.audio-visualizer .bar:nth-child(5) { animation-delay: 0.3s; }
.audio-visualizer .bar:nth-child(6) { animation-delay: 0.25s; }
.audio-visualizer .bar:nth-child(7) { animation-delay: 0.35s; }
.audio-visualizer .bar:nth-child(8) { animation-delay: 0.2s; }
.audio-visualizer .bar:nth-child(9) { animation-delay: 0.4s; }
.audio-visualizer .bar:nth-child(10) { animation-delay: 0.3s; }
.audio-visualizer .bar:nth-child(11) { animation-delay: 0.45s; }
.audio-visualizer .bar:nth-child(12) { animation-delay: 0.35s; }

@keyframes audioWave {
  0%, 100% { height: 15%; opacity: 0.6; }
  50% { height: 80%; opacity: 1; }
}

/* --- Modern Action Buttons --- */
.player-header .header-controls {
  display: flex;
  gap: 0.75rem;
}

.btn-action {
  background: rgba(127, 90, 240, 0.15);
  border: 1px solid rgba(127, 90, 240, 0.3);
  color: var(--text-main);
  padding: 0.6rem 1.2rem;
  border-radius: var(--radius-round);
  font-size: 0.85rem;
  font-weight: 500;
  cursor: pointer;
  transition: var(--transition);
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  position: relative;
  overflow: hidden;
}

.btn-action::before {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.1), transparent);
  transition: left 0.5s;
}

.btn-action:hover {
  background: rgba(127, 90, 240, 0.25);
  border-color: var(--primary);
  transform: translateY(-2px);
  box-shadow: 0 8px 20px rgba(127, 90, 240, 0.25);
}

.btn-action:hover::before {
  left: 100%;
}

.btn-action.active {
  background: var(--gradient-primary);
  border-color: transparent;
  box-shadow: 0 4px 15px rgba(127, 90, 240, 0.4);
}

/* --- Enhanced Progress Bar --- */
.progress-container {
  width: 100%;
  height: 8px;
  background: rgba(255, 255, 255, 0.08);
  border-radius: 4px;
  cursor: pointer;
  position: relative;
  margin: var(--space-sm) 0;
  transition: height 0.2s;
}

.progress-container:hover {
  height: 10px;
}

.progress-bar {
  height: 100%;
  background: linear-gradient(90deg, var(--primary), #9d7af5);
  border-radius: 4px;
  width: 0%;
  position: relative;
  box-shadow: 0 0 15px rgba(127, 90, 240, 0.5);
  transition: width 0.1s linear;
}

.progress-bar::after {
  content: '';
  position: absolute;
  right: -8px;
  top: 50%;
  transform: translateY(-50%);
  width: 16px;
  height: 16px;
  background: #fff;
  border-radius: 50%;
  box-shadow: 0 0 10px rgba(127, 90, 240, 0.8);
  opacity: 0;
  transition: opacity 0.2s, transform 0.2s;
}

.progress-container:hover .progress-bar::after {
  opacity: 1;
}

/* --- Enhanced Play Button --- */
.btn-play {
  width: 72px;
  height: 72px;
  border-radius: 50%;
  background: linear-gradient(135deg, #fff 0%, #e0e0e0 100%);
  color: var(--bg-dark);
  border: none;
  font-size: 1.75rem;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: var(--transition-bounce);
  box-shadow: 
    0 0 30px rgba(255, 255, 255, 0.2),
    0 10px 40px rgba(0, 0, 0, 0.3);
  position: relative;
}

.btn-play::before {
  content: '';
  position: absolute;
  inset: -4px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--primary), transparent);
  opacity: 0;
  transition: opacity 0.3s;
}

.btn-play:hover {
  transform: scale(1.1);
  box-shadow: 
    0 0 50px rgba(255, 255, 255, 0.3),
    0 15px 50px rgba(0, 0, 0, 0.4);
}

.btn-play:hover::before {
  opacity: 0.5;
}

/* --- Enhanced Entity Cards --- */
.entity-card {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  padding: var(--space-sm) var(--space-md);
  background: rgba(255, 255, 255, 0.02);
  border-radius: var(--radius-md);
  border: 1px solid transparent;
  transition: var(--transition);
  cursor: pointer;
  position: relative;
  overflow: hidden;
}

.entity-card::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 3px;
  background: var(--primary);
  opacity: 0;
  transition: opacity 0.3s;
}

.entity-card:hover {
  background: rgba(127, 90, 240, 0.08);
  border-color: rgba(127, 90, 240, 0.2);
  transform: translateX(4px);
}

.entity-card:hover::before {
  opacity: 1;
}

.entity-avatar {
  width: 52px;
  height: 52px;
  border-radius: 50%;
  object-fit: cover;
  border: 2px solid rgba(127, 90, 240, 0.3);
  background: linear-gradient(135deg, var(--bg-dark), #1a1a1a);
  transition: border-color 0.3s, box-shadow 0.3s;
}

.entity-card:hover .entity-avatar {
  border-color: var(--primary);
  box-shadow: 0 0 15px rgba(127, 90, 240, 0.4);
}

.entity-info h4 {
  font-size: 0.95rem;
  font-weight: 600;
  margin-bottom: 0.15rem;
  color: var(--text-main);
}

.entity-info p {
  font-size: 0.75rem;
  color: var(--text-muted);
  text-transform: capitalize;
}

/* --- Enhanced Visual Gallery --- */
.panel-image {
  padding: var(--space-md);
  min-height: 500px;
  display: flex;
  flex-direction: column;
  background: linear-gradient(145deg, rgba(20, 20, 25, 0.8), rgba(15, 15, 18, 0.9));
}

.image-display {
  flex: 1;
  background: rgba(0, 0, 0, 0.4);
  border-radius: var(--radius-md);
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: var(--space-sm);
  padding: var(--space-sm);
  overflow-y: auto;
  border: 1px dashed rgba(127, 90, 240, 0.2);
  max-height: 450px;
}

.image-display .image-wrapper {
  aspect-ratio: 16/10;
  border-radius: var(--radius-sm);
  overflow: hidden;
  cursor: pointer;
  transition: transform 0.3s, box-shadow 0.3s;
  position: relative;
}

.image-display .image-wrapper:hover {
  transform: scale(1.03);
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.5);
  z-index: 2;
}

.image-display .generated-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: opacity 0.5s;
}

.image-display .generated-img.placeholder {
  opacity: 0.3;
}

.image-display .generated-img.loaded {
  opacity: 1;
}

/* --- Enhanced Panel Headers --- */
.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-md);
  padding-bottom: var(--space-sm);
  border-bottom: 1px solid rgba(127, 90, 240, 0.15);
}

.panel-header h3 {
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 1.5px;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.panel-header h3::before {
  content: '';
  width: 8px;
  height: 8px;
  background: var(--primary);
  border-radius: 50%;
  box-shadow: 0 0 10px var(--primary);
}

/* --- Enhanced Dashboard Header --- */
.dashboard-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--space-md) var(--space-lg);
  margin-bottom: var(--space-lg);
  background: linear-gradient(90deg, rgba(127, 90, 240, 0.08), transparent 50%);
  border: 1px solid rgba(127, 90, 240, 0.1);
  border-radius: var(--radius-lg);
}

.book-info h2 {
  font-size: 1.5rem;
  font-weight: 700;
  margin-bottom: 0.25rem;
  background: linear-gradient(135deg, #fff, #b0b0b0);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.book-info p {
  font-size: 0.9rem;
  color: var(--text-muted);
}

/* --- Enhanced Controls Group --- */
.controls-group {
  display: flex;
  gap: var(--space-md);
  align-items: center;
}

.control-item {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.control-item label {
  font-size: 0.7rem;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 1px;
  font-weight: 600;
}

.glass-input {
  background: rgba(0, 0, 0, 0.4);
  border: 1px solid rgba(127, 90, 240, 0.2);
  color: var(--text-main);
  padding: 0.6rem 1rem;
  border-radius: var(--radius-sm);
  font-family: inherit;
  font-size: 0.85rem;
  outline: none;
  transition: var(--transition);
  min-width: 150px;
  cursor: pointer;
}

.glass-input:hover {
  border-color: rgba(127, 90, 240, 0.4);
}

.glass-input:focus {
  border-color: var(--primary);
  background: rgba(127, 90, 240, 0.1);
  box-shadow: 0 0 15px rgba(127, 90, 240, 0.2);
}

/* --- Smooth Transitions for Future Features --- */
.feature-card {
  background: var(--glass-bg);
  border: 1px solid var(--glass-border);
  border-radius: var(--radius-lg);
  padding: var(--space-lg);
  transition: var(--transition);
}

.feature-card:hover {
  border-color: rgba(127, 90, 240, 0.3);
  box-shadow: 0 20px 50px rgba(0, 0, 0, 0.4);
  transform: translateY(-5px);
}

/* --- Tooltip Enhancement --- */
[title] {
  position: relative;
}

/* --- Loading Skeleton Enhancement --- */
.skeleton-card {
  background: linear-gradient(90deg, rgba(255,255,255,0.03), rgba(255,255,255,0.08), rgba(255,255,255,0.03));
  background-size: 200% 100%;
  animation: skeleton 1.5s infinite;
  border-radius: var(--radius-md);
  height: 60px;
}

@keyframes skeleton {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

/* --- Enhanced Chatbot Button --- */
.chatbot-fab {
  width: 60px;
  height: 60px;
  border-radius: 50%;
  background: var(--gradient-primary);
  border: none;
  font-size: 1.5rem;
  cursor: pointer;
  box-shadow: 
    0 8px 30px rgba(127, 90, 240, 0.4),
    inset 0 1px 0 rgba(255, 255, 255, 0.2);
  transition: var(--transition-bounce);
  position: fixed;
  bottom: 2rem;
  right: 2rem;
  z-index: 1000;
}

.chatbot-fab:hover {
  transform: scale(1.1) rotate(10deg);
  box-shadow: 0 12px 40px rgba(127, 90, 240, 0.5);
}

/* --- Enhanced Badge --- */
.badge-count {
  background: rgba(127, 90, 240, 0.2);
  padding: 0.2rem 0.6rem;
  border-radius: var(--radius-round);
  font-size: 0.75rem;
  color: var(--primary);
  font-weight: 600;
  border: 1px solid rgba(127, 90, 240, 0.3);
}

/* --- Enhanced Button Small --- */
.btn-sm {
  background: rgba(127, 90, 240, 0.1);
  border: 1px solid rgba(127, 90, 240, 0.25);
  color: var(--text-main);
  padding: 0.5rem 1rem;
  border-radius: var(--radius-round);
  font-size: 0.8rem;
  font-weight: 500;
  cursor: pointer;
  transition: var(--transition);
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
}

.btn-sm:hover {
  background: rgba(127, 90, 240, 0.2);
  border-color: var(--primary);
  transform: translateY(-1px);
  box-shadow: 0 4px 15px rgba(127, 90, 240, 0.2);
}

.btn-sm .icon {
  font-size: 1rem;
}

/* --- Enhanced Panel Left --- */
.panel-left {
  padding: var(--space-md);
  min-height: 500px;
  background: linear-gradient(145deg, rgba(20, 20, 25, 0.8), rgba(15, 15, 18, 0.9));
  border: 1px solid rgba(127, 90, 240, 0.08);
}

.entities-grid {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  max-height: 420px;
  overflow-y: auto;
  padding-right: 0.5rem;
}

/* Custom Scrollbar */
.entities-grid::-webkit-scrollbar,
.image-display::-webkit-scrollbar {
  width: 6px;
}

.entities-grid::-webkit-scrollbar-track,
.image-display::-webkit-scrollbar-track {
  background: rgba(255, 255, 255, 0.02);
  border-radius: 3px;
}

.entities-grid::-webkit-scrollbar-thumb,
.image-display::-webkit-scrollbar-thumb {
  background: rgba(127, 90, 240, 0.3);
  border-radius: 3px;
}

.entities-grid::-webkit-scrollbar-thumb:hover,
.image-display::-webkit-scrollbar-thumb:hover {
  background: var(--primary);
}

/* --- Timeline/Infographic Ready Styles --- */
.timeline-container {
  padding: var(--space-md);
  background: var(--glass-bg);
  border-radius: var(--radius-lg);
  border: 1px solid var(--glass-border);
}

.timeline-event {
  display: flex;
  gap: var(--space-md);
  padding: var(--space-sm) 0;
  border-left: 2px solid var(--primary);
  padding-left: var(--space-md);
  position: relative;
}

.timeline-event::before {
  content: '';
  position: absolute;
  left: -6px;
  top: 50%;
  transform: translateY(-50%);
  width: 10px;
  height: 10px;
  background: var(--primary);
  border-radius: 50%;
  box-shadow: 0 0 10px var(--primary);
}

/* --- Comic Strip Ready Styles --- */
.comic-panel {
  border: 3px solid #000;
  border-radius: var(--radius-sm);
  overflow: hidden;
  position: relative;
  background: #fff;
}

.comic-panel img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.speech-bubble {
  position: absolute;
  background: #fff;
  color: #000;
  padding: var(--space-sm);
  border-radius: var(--radius-md);
  border: 2px solid #000;
  font-family: 'Comic Sans MS', cursive, sans-serif;
  font-size: 0.85rem;
  max-width: 150px;
}

.speech-bubble::after {
  content: '';
  position: absolute;
  bottom: -10px;
  left: 20px;
  border: 10px solid transparent;
  border-top-color: #000;
}

'''

# Append the new enhancements to the CSS file
# We add them at the end to ensure they override previous styles
with open(css_path, 'a', encoding='utf-8') as f:
    f.write(NEW_CSS_ENHANCEMENTS)

print("✅ Successfully added UI/UX enhancements to style.css!")
print(f"   Added approximately {len(NEW_CSS_ENHANCEMENTS.splitlines())} lines of enhanced styles.")
