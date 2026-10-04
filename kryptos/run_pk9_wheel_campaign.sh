#!/bin/bash
# PK9 wheel-word sweep campaign (2 cores, staged by priority).
# Each stage logs its own header/footer so partial progress is useful.
set -u
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT"
export OMP_NUM_THREADS=${OMP_NUM_THREADS:-2}
BIN=${PK9_WHEEL_BIN:-/tmp/sweep_pk9_word_wheels}
LOG="$ROOT/kryptos/pk9_wheel_campaign.log"

# Make the campaign reproducible from a clean checkout.  A prebuilt binary is
# still honored, but a missing/stale binary is rebuilt automatically.
if [[ ! -x "$BIN" || kryptos/sweep_pk9_word_wheels.c -nt "$BIN" ]]; then
    cc -O3 -march=native -funroll-loops -fopenmp \
       -o "$BIN" kryptos/sweep_pk9_word_wheels.c -lm
fi

run() {
    echo "====================================================================" >> "$LOG"
    echo "[$(date -u +%H:%M:%S)] STAGE: $1" >> "$LOG"
    shift
    "$@" >> "$LOG" 2>&1
    echo "[$(date -u +%H:%M:%S)] stage done (exit $?)" >> "$LOG"
}

# Append rather than truncate: interrupted campaigns retain their audit trail.
echo "PK9 wheel-word sweep campaign started $(date -u)" >> "$LOG"

# R5: story wheels x ALL 40320 T8 perms, qt order (notation-verified order)
run "R5 story-wheels x all-T8 qt" \
    "$BIN" kryptos/pk9_vocab_story5.txt kryptos/pk9_vocab_story6.txt kryptos/pk9_vocab_story7.txt \
    --order qt --top 10

# R6: broad craft wheels x story 8-letter T8 keywords, both orders
run "R6 broad-wheels x story-T8 both" \
    "$BIN" kryptos/pk9_vocab_broad5.txt kryptos/pk9_vocab_broad6.txt kryptos/pk9_vocab_broad7.txt \
    --t8-words kryptos/pk9_vocab_story8.txt --order both --top 10

# R7: broad craft wheels x theophilus 8-letter T8 keywords, qt order
run "R7 broad-wheels x theophilus-T8 qt" \
    "$BIN" kryptos/pk9_vocab_broad5.txt kryptos/pk9_vocab_broad6.txt kryptos/pk9_vocab_broad7.txt \
    --t8-words kryptos/theophilus_w8.txt --order qt --top 10

# R5b: story wheels x ALL 40320 T8 perms, tq order (insurance)
run "R5b story-wheels x all-T8 tq" \
    "$BIN" kryptos/pk9_vocab_story5.txt kryptos/pk9_vocab_story6.txt kryptos/pk9_vocab_story7.txt \
    --order tq --top 10

# R8: PK8-plaintext-window wheels x ALL perms, qt order
run "R8 pk8win-wheels x all-T8 qt" \
    "$BIN" kryptos/pk9_vocab_pk8win5.txt kryptos/pk9_vocab_pk8win6.txt kryptos/pk9_vocab_pk8win7.txt \
    --order qt --top 10

echo "[$(date -u)] CAMPAIGN COMPLETE" >> "$LOG"
