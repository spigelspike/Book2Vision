
c = open('web/index.html','r', encoding='utf-8').read()

# Find the old section tag and the nb-layout that follows
sec_id = 'id="dashboard"'
s_idx = c.find(sec_id)
print('Dashboard section at line:', c[:s_idx].count('\n')+1)

# Find what's between section open and nb-layout
nb_idx = c.find('nb-layout')
print('nb-layout at line:', c[:nb_idx].count('\n')+1)
chunk = c[s_idx:nb_idx]
print('Between section and nb-layout:')
print(repr(chunk[:400]))
