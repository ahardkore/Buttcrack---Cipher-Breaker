"""Record a completed/interrupted campaign chunk in the SQLite ledger."""
from __future__ import annotations
import argparse, hashlib, os, re, time
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from buttcrack.results_db import ResultDB

p=argparse.ArgumentParser(); p.add_argument('database'); p.add_argument('start',type=int); p.add_argument('end',type=int); p.add_argument('status'); p.add_argument('--runtime',type=float,default=None); p.add_argument('--log'); p.add_argument('--campaign',default='pk9-resumable-qt'); args=p.parse_args()
ct='KSYAWFEYYOISZGEUFBLYATAIBYFAQBQYYVDWJKLJXMYIEPIFVHPQNHZGSUHUUDXLEHRHUMALHEGLHXSJMUXGNUIVBXGUJHZRZGUSVHMLSCTSUQXHSUMQQIFUQGKHJGUQGLHDKEWSKAMHIJXD'
db=ResultDB(args.database)
score=None; candidate=None
if args.log and Path(args.log).exists():
    lines=Path(args.log).read_text(errors='replace').splitlines()
    for i,line in enumerate(lines):
        m=re.search(r'^\[\s*\d+\]\s+(-?\d+\.\d+)', line)
        if m:
            value=float(m.group(1))
            following=lines[i+1].strip() if i+1<len(lines) else ''
            # Candidate lines are indented plaintext lines, not metadata.
            if following and not following.startswith('[') and len(following)>=20:
                if score is None or value > score: score, candidate = value, following
runtime=args.runtime
db.add(ciphertext_hash=hashlib.sha256(ct.encode()).hexdigest(), attack='pk9-wheel-qt', parameters={'perm_start':args.start,'perm_end':args.end,'chunk_size':args.end-args.start}, score=score, candidate=candidate, status=args.status, runtime_seconds=runtime, cpu_count=os.cpu_count(), verification='not_checked', campaign={'id':args.campaign,'range_start':args.start,'range_end':args.end}, chunk_id=f'{args.campaign}:{args.start}-{args.end}')
print(f'recorded chunk {args.start}:{args.end} status={args.status} score={score}')
