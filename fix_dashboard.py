
import re

c = open('web/index.html', 'r', encoding='utf-8').read()

# The section currently is:
# <section id="dashboard" class="container hidden fade-in" ...>
#   <!-- Top Bar: Book Info & Settings -->
#   <div class="dashboard-header glass"> ... </div>
#   <div class="nb-layout" ...> ... </div>
# </section>
#
# We want to:
# 1. Change class="container hidden fade-in" -> class="nb-dashboard hidden fade-in"
# 2. Remove the entire .dashboard-header block
# 3. Keep the .nb-layout block

# Step 1: Change section class
c = c.replace(
    'id="dashboard" class="container hidden fade-in"',
    'id="dashboard" class="nb-dashboard hidden fade-in"'
)
print("Step 1 done, container->nb-dashboard")

# Step 2: Remove dashboard-header block
# Find start of comment and end of the closing </div>
header_start = c.find('<!-- Top Bar: Book Info & Settings -->')
if header_start == -1:
    header_start = c.find('<!-- Top Bar: Book Info')
print(f"Header comment found at pos {header_start}, line {c[:header_start].count(chr(10))+1}")

# Find the closing </div> of .dashboard-header
# It's 2 levels deep inside the section, before nb-layout
# We search for the </div> that closes dashboard-header
# The pattern is <div class="dashboard-header glass"> ... </div>
dh_open = c.find('<div class="dashboard-header glass">')
print(f"dashboard-header div at pos {dh_open}, line {c[:dh_open].count(chr(10))+1}")

# Count div depth to find matching close
i = dh_open
depth = 0
while i < len(c):
    open_tag = c.find('<div', i)
    close_tag = c.find('</div>', i)
    if open_tag == -1 and close_tag == -1:
        break
    if close_tag == -1 or (open_tag != -1 and open_tag < close_tag):
        depth += 1
        i = open_tag + 4
    else:
        depth -= 1
        i = close_tag + 6
        if depth == 0:
            dh_end = i
            break

print(f"dashboard-header closing </div> ends at pos {dh_end}, line {c[:dh_end].count(chr(10))+1}")

# Remove from the comment to the end of the closing </div>
# Include any whitespace between header_start and dh_open
remove_from = header_start
# But also check for preceding whitespace/newlines
while remove_from > 0 and c[remove_from-1] in ' \t':
    remove_from -= 1

# Also eat any trailing newlines after dh_end
remove_to = dh_end
while remove_to < len(c) and c[remove_to] in '\r\n':
    remove_to += 1

print(f"Removing chars {remove_from} to {remove_to}")
c = c[:remove_from] + c[remove_to:]
print("Step 2 done, removed dashboard-header")

# Also add hidden selects after the section open for JS compatibility
# The JS reads audio-provider and style-select - add them hidden
hidden_selects = '''
            <!-- Hidden selects for JS compatibility -->
            <select id="audio-provider" class="hidden" aria-hidden="true" style="display:none">
                <option value="deepgram">Deepgram (Fast)</option>
                <option value="elevenlabs">ElevenLabs (High Quality)</option>
                <option value="inbuilt">Inbuilt (Free)</option>
            </select>
            <select id="style-select" class="hidden" aria-hidden="true" style="display:none">
                <option value="storybook">Storybook</option>
                <option value="cinematic">Cinematic</option>
                <option value="anime">Anime</option>
                <option value="watercolor">Watercolor</option>
                <option value="cyberpunk">Cyberpunk</option>
                <option value="fantasy">Fantasy</option>
            </select>
'''

# Insert after the section opening tag
section_open_end = c.find('aria-label="Book Dashboard">') + len('aria-label="Book Dashboard">')
c = c[:section_open_end] + hidden_selects + c[section_open_end:]
print("Step 3 done, added hidden selects")

open('web/index.html', 'w', encoding='utf-8').write(c)
print(f"Done! Total lines: {c.count(chr(10))}")
print("Verify - nb-dashboard in file:", 'nb-dashboard' in c)
print("Verify - dashboard-header in file:", 'dashboard-header' in c)
