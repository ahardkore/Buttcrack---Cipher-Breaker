#!/usr/bin/env bash
# Resumable PK9 QT sweep. Each chunk exits independently, so a killed process
# loses at most one chunk and progress is visible in the log.
set -u
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT"
export OMP_NUM_THREADS=${OMP_NUM_THREADS:-2}
BIN=${PK9_WHEEL_BIN:-/tmp/sweep_pk9_word_wheels}
LOG="$ROOT/kryptos/pk9_resumable.log"
DB="${PK9_RESULT_DB:-$ROOT/kryptos/pk9-results.sqlite3}"
if [[ ! -x "$BIN" || kryptos/sweep_pk9_word_wheels.c -nt "$BIN" ]]; then
  cc -O3 -march=native -funroll-loops -fopenmp -o "$BIN" kryptos/sweep_pk9_word_wheels.c -lm
fi
start=${PK9_START:-0}; end=${PK9_END:-40320}; chunk=${PK9_CHUNK:-100}
for ((a=start; a<end; a+=chunk)); do
  b=$((a+chunk)); (( b > end )) && b=$end
  echo "[$(date -u +%FT%TZ)] chunk $a:$b" >> "$LOG"
  chunk_log=$(mktemp)
  started=$(date +%s)
  "$BIN" kryptos/pk9_vocab_story5.txt kryptos/pk9_vocab_story6.txt \
    kryptos/pk9_vocab_story7.txt --order qt --perm-range "$a" "$b" --top 10 \
    > "$chunk_log" 2>&1
  rc=$?
  runtime=$(($(date +%s)-started))
  cat "$chunk_log" >> "$LOG"
  echo "[$(date -u +%FT%TZ)] chunk $a:$b exit=$rc runtime=${runtime}s" >> "$LOG"
  status=completed; (( rc != 0 )) && status=interrupted
  python3 kryptos/record_chunk.py "$DB" "$a" "$b" "$status" --campaign "${PK9_CAMPAIGN_ID:-pk9-resumable-qt}" --runtime "$runtime" --log "$chunk_log" >> "$LOG" 2>&1 || true
  rm -f "$chunk_log"
  (( rc != 0 )) && exit "$rc"
done
echo "[$(date -u +%FT%TZ)] resumable QT sweep complete" >> "$LOG"
