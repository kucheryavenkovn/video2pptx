"""Link test files to their modules via MODULE_CONTRACT LINKS.

For each V-M entry, the test files it references should link back to the
entry's MODULE. The linter reports autonomy.verification-test-file-unlinked-module
when a governed test file's LINKS does not include the module ID.

This script:
1. Parses V-M entries to build (test_file -> set of module IDs that verify it)
2. For each governed test file, ensures its MODULE_CONTRACT LINKS includes all
   relevant module IDs.
3. Only edits LINKS lines (markup fix, no runtime logic change).

If a test file has no MODULE_CONTRACT at all, we do NOT fabricate one (that
would be structural invention). We only augment existing LINKS.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
VP_PATH = ROOT / "docs" / "verification-plan.xml"

# Build test_file -> set of module IDs from V-M entries
text = VP_PATH.read_text(encoding="utf-8")
ENTRY_RE = re.compile(r"<(V-M-[A-Z0-9-]+)\b([^>]*)>([\s\S]*?)</\1>")
test_to_modules: dict[str, set[str]] = {}
for m in ENTRY_RE.finditer(text):
    attrs = m.group(2)
    body = m.group(3)
    mid_m = re.search(r'MODULE="([^"]+)"', attrs)
    if not mid_m:
        continue
    mid = mid_m.group(1)
    # skip non-module refs like Phase-16/Step-1
    if not re.fullmatch(r"M-[A-Z0-9-]+", mid):
        continue
    for fblock in re.findall(r"<test-files>([\s\S]*?)</test-files>", body):
        for f in re.findall(r"<file>([^<]+)</file>", fblock):
            f = f.strip()
            if f:
                test_to_modules.setdefault(f, set()).add(mid)


def update_links_in_file(path: Path, modules: set[str]) -> tuple[bool, str]:
    """Add missing module IDs to the LINKS line of the file's MODULE_CONTRACT.
    Returns (changed, description)."""
    if not path.exists():
        return (False, "missing")
    txt = path.read_text(encoding="utf-8")
    # find a LINKS line within MODULE_CONTRACT
    sec_m = re.search(r"(# START_MODULE_CONTRACT[\s\S]*?# END_MODULE_CONTRACT)", txt)
    if not sec_m:
        return (False, "no MODULE_CONTRACT")
    sec = sec_m.group(1)
    # find LINKS line
    links_m = re.search(r"(#\s*LINKS:\s*)([^\n]*)", sec)
    if not links_m:
        return (False, "no LINKS line")
    current = links_m.group(2)
    # parse existing refs
    existing = set(re.findall(r"[VM]-[A-Z0-9-]+|[VM]-[A-Z0-9-]+/[A-Za-z0-9-]+", current))
    # also capture M-* tokens specifically, but NOT M-* inside V-M-* (verification IDs)
    # use negative lookbehind: M must not be preceded by V- or another letter/dash
    existing_m = set(re.findall(r"(?<![A-Z-])M-[A-Z0-9-]+", current))
    missing = set(modules) - existing_m
    if not missing:
        return (False, "already linked")
    # append missing module IDs
    prefix = current.rstrip()
    if prefix and not prefix.endswith(","):
        prefix = prefix + ","
    elif prefix and prefix.endswith(","):
        prefix = prefix + " "
    addition = ", ".join(sorted(missing))
    new_links = prefix + (" " if prefix and not prefix.endswith(" ") else "") + addition
    new_links_line = links_m.group(1) + new_links
    new_sec = sec[: links_m.start()] + new_links_line + sec[links_m.end():]
    new_txt = txt[: sec_m.start()] + new_sec + txt[sec_m.end():]
    path.write_text(new_txt, encoding="utf-8")
    return (True, f"added {sorted(missing)}")


updated = 0
skipped = 0
report = []
for tf, modules in sorted(test_to_modules.items()):
    p = ROOT / tf
    changed, desc = update_links_in_file(p, modules)
    if changed:
        updated += 1
        report.append(f"OK {tf}: {desc}")
    else:
        skipped += 1
        if desc == "no MODULE_CONTRACT":
            report.append(f"SKIP {tf}: {desc} (would require new contract)")

print(f"Updated: {updated}")
print(f"Skipped: {skipped}")
# Write report
(ROOT / "docs/grace-reports/stage2-verification-20260718" / "test-links-report.txt").write_text(
    "\n".join(report), encoding="utf-8"
)
