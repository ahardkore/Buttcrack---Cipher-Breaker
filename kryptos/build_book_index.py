"""Build a working alphabetical index from the manuscript glossary terms."""
from pathlib import Path
import re
root=Path(__file__).parent
text=(root/'KRYPTOS_SCHOLARLY_MANUSCRIPT.md').read_text(encoding='utf-8')
section=text.split('## 108. Glossary',1)[-1].split('## 109.',1)[0]
terms=[]
for line in section.splitlines():
    m=re.match(r'\*\*([^:]+):\*\*', line)
    if m: terms.append(m.group(1).strip())
terms=sorted(set(terms), key=str.casefold)
out=['# Working index','', 'Generated from glossary headings. Page numbers are inserted during final typesetting.', '']
out += [f'- **{term}** — glossary and relevant chapter search' for term in terms]
(root/'INDEX_WORKING.md').write_text('\n'.join(out)+'\n', encoding='utf-8')
print(f'wrote INDEX_WORKING.md ({len(terms)} terms)')
