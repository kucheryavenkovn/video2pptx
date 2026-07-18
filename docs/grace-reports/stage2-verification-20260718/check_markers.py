import re
from pathlib import Path

text = Path('docs/verification-plan.xml').read_text(encoding='utf-8')
ENTRY_RE = re.compile(r'(<V-M-[A-Z0-9-]+\b[^>]*>)([\s\S]*?)(</V-M-[A-Z0-9-]+>)')
for m in ENTRY_RE.finditer(text):
    open_tag, body = m.group(1), m.group(2)
    vid = open_tag.split()[0].lstrip('<')
    mid_m = re.search(r'MODULE="([^"]+)"', open_tag)
    mid = mid_m.group(1) if mid_m else ''
    if '<required-log-markers>' in body:
        markers = re.findall(r'<marker>([^<]+)</marker>', body)
        print(f'{vid} (M={mid}): {markers}')
