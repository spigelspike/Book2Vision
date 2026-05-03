# Script to update HTML with enhanced visualizer and bump CSS version
import os
import re

html_path = os.path.join(os.path.dirname(__file__), 'web', 'index.html')
with open(html_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Bump CSS version for cache busting
content = re.sub(r'style\.css\?v=\d+', 'style.css?v=20', content)
content = re.sub(r'script\.js\?v=\d+', 'script.js?v=20', content)

# 2. Enhance the audio visualizer with more bars
OLD_VISUALIZER = '''<div class="audio-visualizer" aria-hidden="true">
                            <!-- Simple CSS visualizer bars -->
                            <div class="bar"></div>
                            <div class="bar"></div>
                            <div class="bar"></div>
                            <div class="bar"></div>
                            <div class="bar"></div>
                            <div class="bar"></div>
                            <div class="bar"></div>
                            <div class="bar"></div>
                            <div class="bar"></div>
                            <div class="bar"></div>
                            <div class="bar"></div>
                            <div class="bar"></div>
                        </div>'''

NEW_VISUALIZER = '''<div class="audio-visualizer" aria-hidden="true">
                            <!-- Enhanced Waveform Visualizer -->
                            <div class="bar"></div>
                            <div class="bar"></div>
                            <div class="bar"></div>
                            <div class="bar"></div>
                            <div class="bar"></div>
                            <div class="bar"></div>
                            <div class="bar"></div>
                            <div class="bar"></div>
                            <div class="bar"></div>
                            <div class="bar"></div>
                            <div class="bar"></div>
                            <div class="bar"></div>
                            <div class="bar"></div>
                            <div class="bar"></div>
                            <div class="bar"></div>
                            <div class="bar"></div>
                            <div class="bar"></div>
                            <div class="bar"></div>
                            <div class="bar"></div>
                            <div class="bar"></div>
                            <div class="bar"></div>
                            <div class="bar"></div>
                            <div class="bar"></div>
                            <div class="bar"></div>
                        </div>'''

if OLD_VISUALIZER in content:
    content = content.replace(OLD_VISUALIZER, NEW_VISUALIZER)
    print("✅ Enhanced audio visualizer with more bars")
else:
    # Try with CRLF line endings
    OLD_VISUALIZER_CRLF = OLD_VISUALIZER.replace('\n', '\r\n')
    NEW_VISUALIZER_CRLF = NEW_VISUALIZER.replace('\n', '\r\n')
    if OLD_VISUALIZER_CRLF in content:
        content = content.replace(OLD_VISUALIZER_CRLF, NEW_VISUALIZER_CRLF)
        print("✅ Enhanced audio visualizer with more bars (CRLF)")
    else:
        print("⚠️ Could not find visualizer to enhance (might already be enhanced)")

# 3. Update the player header to use action button styles
OLD_HEADER_CONTROLS = 'class="btn-sm">'
NEW_HEADER_CONTROLS = 'class="btn-sm btn-action">'

# Only update the first few occurrences in player area
# content = content.replace(OLD_HEADER_CONTROLS, NEW_HEADER_CONTROLS, 3)

# Save the updated file
with open(html_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ Updated index.html:")
print("   - Bumped CSS/JS versions to v20 for cache busting")
print("   - Enhanced audio visualizer")
