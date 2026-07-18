import re
from pathlib import Path

text = Path('docs/verification-plan.xml').read_text(encoding='utf-8')
ENTRY_RE = re.compile(r'<(V-M-(?:ADAPTERS|APP-BOOTSTRAP|APP-BUILD-META|APP-COMMON|APP-IDENTITY|APP-INPUT-RESOLVER|APP-LLM|BACKEND-OPENCV|BACKEND-PYAV|DESKTOP-BOOTSTRAP|DETECT-BENCHMARK|DETECT-METRICS|DETECT-PERF-DECISION|GITHUB-PROVIDER|GUI-ABOUT|GUI-HELP-MENU|GUI-PIPELINE-CTRL|GUI-PIPELINE-WORKER|GUI-TIMELINE-CTRL|GUI-UPDATE-CTRL|GUI-WINDOW-UI|MCP-ADAPTER|MCP-COMPOSITION|PERSIST-DETECTION|PORT-ALIGNMENT|PORT-DETECTOR|PORT-EXPORT|PORT-LLM|PORT-NOTES|PORT-PREVIEW))\b([^>]*)>([\s\S]*?)</\1>')
for m in ENTRY_RE.finditer(text):
    vid = m.group(1)
    attrs = m.group(2)
    body = m.group(3)
    has_mc = '<module-checks>' in body
    has_tf = '<file>' in body
    status_m = re.search(r'STATUS="([^"]+)"', attrs)
    status = status_m.group(1) if status_m else ''
    if not has_mc or not has_tf:
        print(f'{vid} status={status} module_checks={has_mc} test_files={has_tf}')
