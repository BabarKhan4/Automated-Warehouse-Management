#!/usr/bin/env python3
"""
scripts/add_feature.py

Small helper: append a feature entry into the README's Features section.
Usage:
    ./scripts/add_feature.py "Short feature title" "Optional longer description"

Behavior:
- Ensures a `## Features` section exists in README.md (creates one if missing).
- Appends a bullet entry under that section with the current date and
  a short description.
- Avoids duplicate exact titles.
"""
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
README = ROOT / 'README.md'

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: add_feature.py "Feature Title" "Optional longer description"')
        sys.exit(2)
    title = sys.argv[1].strip()
    desc = sys.argv[2].strip() if len(sys.argv) > 2 else ''

    if not README.exists():
        print('README.md not found in repo root')
        sys.exit(1)

    content = README.read_text(encoding='utf-8')

    # Find or create Features section
    marker = '## Features'
    if marker not in content:
        # Append a Features section at the end
        content = content.rstrip() + '\n\n## Features\n\n'

    parts = content.split(marker)
    head = parts[0]
    tail = marker + parts[1]

    # Insert a bullet at the top of the Features section (after the header)
    lines = tail.splitlines()
    # lines[0] == '## Features'
    insert_idx = 1
    # skip any blank lines immediately after header
    while insert_idx < len(lines) and lines[insert_idx].strip() == '':
        insert_idx += 1

    bullets = lines[:insert_idx]
    rest = lines[insert_idx:]

    # avoid duplicate exact title
    existing = '\n'.join(rest)
    if title in existing:
        print('Feature title already present; not adding duplicate')
        sys.exit(0)

    date = datetime.utcnow().strftime('%Y-%m-%d')
    bullet = f'- {title} ({date})'
    if desc:
        bullet += f": {desc}"

    bullets.append(bullet)

    new_tail = '\n'.join(bullets + [''] + rest)
    new_content = head + new_tail

    README.write_text(new_content, encoding='utf-8')
    print(f'Added feature to README: {title}')
