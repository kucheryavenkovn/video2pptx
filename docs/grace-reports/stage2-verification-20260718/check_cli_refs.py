import re
from pathlib import Path

text = Path('docs/verification-plan.xml').read_text(encoding='utf-8')
for m in re.finditer(r'<(V-M-[A-Z0-9-]+)\b([^>]*)>([\s\S]*?)</\1>', text):
    vid = m.group(1)
    attrs = m.group(2)
    body = m.group(3)
    files = re.findall(r'<file>([^<]+)</file>', body)
    if any('test_cli.py' in f and 'test_cli_e2e' not in f for f in files):
        mid_m = re.search(r'MODULE="([^"]+)"', attrs)
        mid = mid_m.group(1) if mid_m else ''
        print(f'{vid} MODULE={mid} references test_cli.py')
