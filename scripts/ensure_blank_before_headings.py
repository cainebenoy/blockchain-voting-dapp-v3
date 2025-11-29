#!/usr/bin/env python3
import sys
from pathlib import Path
import re

if len(sys.argv) < 2:
    print('Usage: ensure_blank_before_headings.py <file1> [file2 ...]')
    sys.exit(1)

for pth in sys.argv[1:]:
    p = Path(pth)
    if not p.exists():
        print('File not found:', p)
        continue
    text = p.read_text()
    lines = text.splitlines()
    out = []
    in_fence = False
    fence_ticks = None
    for i, line in enumerate(lines):
        m = re.match(r"^(?P<t>`{3,}).*", line)
        if m:
            ticks = m.group('t')
            if not in_fence:
                in_fence = True
                fence_ticks = ticks
            else:
                # closing only if same ticks
                if ticks == fence_ticks:
                    in_fence = False
                    fence_ticks = None
            out.append(line)
            continue
        if not in_fence and re.match(r'^#{1,6}\s+', line):
            if out and out[-1].strip() != '':
                out.append('')
        out.append(line)
    new_text = '\n'.join(out) + '\n'
    backup = p.with_suffix(p.suffix + '.bak2')
    if not backup.exists():
        backup.write_text(text)
    p.write_text(new_text)
    print('Processed', p)
