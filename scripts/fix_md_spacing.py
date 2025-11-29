#!/usr/bin/env python3
import re
from pathlib import Path

p = Path('docs/DEPLOYMENT.md')
text = p.read_text()
lines = text.splitlines()
out = []
in_fence = False
fence_delim = None
fence_start_idx = None

def choose_lang(fence_lines):
    s = '\n'.join(fence_lines)
    if re.search(r"\bpython\b|def\b|import\b|from\b|print\(|async\b|await\b", s, re.I):
        return 'python'
    if re.search(r"\b(node|npm|npx|apt|apt-get|sudo|git|curl|wget|systemctl|service|npm|cd|bash|sh)\b", s, re.I):
        return 'bash'
    if re.search(r"\[Unit\]|ExecStart=|WantedBy=|Service\b|\[Service\]", s):
        return 'ini'
    if re.search(r"=|:|static ip_address|interface|dhcpcd", s, re.I):
        return 'conf'
    return 'text'

i = 0
while i < len(lines):
    line = lines[i]
    # detect fence start/end (allow more than 3 backticks)
    m = re.match(r"^(?P<ticks>`{3,})(?P<lang>[^\s`]*)\s*$", line)
    if m:
        ticks = m.group('ticks')
        lang = m.group('lang')
        if not in_fence:
            # starting a fence
            # ensure blank line before
            if out and out[-1].strip() != '':
                out.append('')
            fence_delim = ticks
            fence_start_idx = i
            # if no lang, look ahead to pick one
            if lang == '':
                # collect content until closing fence
                j = i+1
                fence_lines = []
                while j < len(lines):
                    if re.match(rf"^{ticks}\s*$", lines[j]):
                        break
                    fence_lines.append(lines[j])
                    j += 1
                chosen = choose_lang(fence_lines)
                out.append(f"{ticks}{chosen}")
            else:
                out.append(line)
            in_fence = True
            i += 1
            continue
        else:
            # closing fence
            out.append(line)
            in_fence = False
            fence_delim = None
            # ensure blank line after
            if i+1 < len(lines) and lines[i+1].strip() != '':
                out.append('')
            i += 1
            continue
    if in_fence:
        out.append(line)
        i += 1
        continue
    # not in fence
    # headings: ensure blank line before headings (except if out empty)
    if re.match(r"^#+\s+", line):
        # convert additional H1s to H2 (only allow first line of file to be H1)
        if line.startswith('# ') and len(out) > 0:
            line = '##' + line[1:]
        if out and out[-1].strip() != '':
            out.append('')
        out.append(line)
        # ensure a blank line after heading if next line not blank and not another heading
        if i+1 < len(lines) and lines[i+1].strip() != '' and not re.match(r"^#+\s+", lines[i+1]):
            out.append('')
        i += 1
        continue
    out.append(line)
    i += 1

new_text = '\n'.join(out) + '\n'
# write backup
bak = p.with_suffix('.md.bak')
if not bak.exists():
    bak.write_text(text)
p.write_text(new_text)
print('Fixed spacing and fences in', p)
