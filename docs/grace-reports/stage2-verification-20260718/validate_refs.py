import re
from pathlib import Path
import xml.etree.ElementTree as ET

text = Path('docs/verification-plan.xml').read_text(encoding='utf-8')
ids = re.findall(r'<(V-M-[A-Z0-9-]+)\b', text)
from collections import Counter
dups = {k: v for k, v in Counter(ids).items() if v > 1}
print(f'Total V-M entries: {len(ids)}')
print(f'Unique V-M IDs: {len(set(ids))}')
print(f'Duplicates: {dups}')

vmods = set()
for m in re.finditer(r'<V-M-[A-Z0-9-]+\b[^>]*MODULE="([^"]+)"', text):
    vmods.add(m.group(1))

kg = ET.parse('docs/knowledge-graph.xml').getroot()
kg_mods = {t.tag for t in kg.iter() if t.tag.startswith('M-')}
dangling = {m for m in vmods if m.startswith('M-') and m not in kg_mods}
print(f'Verification MODULE refs not in KG: {sorted(dangling)}')

# also check test file paths referenced in V-M entries
missing_tests = []
for m in re.finditer(r'<V-M-[A-Z0-9-]+\b[^>]*>([\s\S]*?)</V-M-[A-Z0-9-]+>', text):
    body = m.group(1)
    for f in re.findall(r'<file>([^<]+)</file>', body):
        if f.strip() and not (Path('.') / f.strip()).exists():
            missing_tests.append(f.strip())
print(f'Test files referenced but missing on disk: {len(missing_tests)}')
for t in sorted(set(missing_tests)):
    print(f'  {t}')
