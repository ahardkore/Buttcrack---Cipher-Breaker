"""Measure local PK9 ledger throughput without claiming a cryptanalytic result."""
from pathlib import Path
import json, time, sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from buttcrack.results_db import ResultDB

def main():
    db=ResultDB('kryptos/pk9-results.sqlite3'); rows=db.recent(100000)
    runtimes=[float(r[2]) for r in rows if r[2] is not None and float(r[2])>0]
    completed=sum(r[1]=='completed' for r in rows)
    report={'observations':len(rows),'completed_chunks':completed,'runtime_seconds_recorded':sum(runtimes),'throughput_chunks_per_hour':completed/(sum(runtimes)/3600) if runtimes else None,'measured_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ'),'status':'benchmark only; PK9 remains unsolved'}
    Path('kryptos/pk9-throughput.json').write_text(json.dumps(report,indent=2)+'\n'); print(json.dumps(report,indent=2))
if __name__=='__main__': main()
