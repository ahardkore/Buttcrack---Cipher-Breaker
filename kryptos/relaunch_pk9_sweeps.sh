#!/bin/bash
# Self-healing PK9 sweep relauncher (2026-10-02, v2).
#
# The sandbox occasionally restarts at turn boundaries: /tmp (binaries, corpora,
# logs) is wiped and background jobs die. This script makes relaunch cheap and
# SAFE against false "completed" markers:
#   - engines MUST run from the REPO ROOT (they load buttcrack/data/english_quadgrams.txt.gz
#     via a relative path and exit 2 otherwise);
#   - a stage is only marked "stage done" if the engine exited 0 AND its output
#     contains the engine's completion signature (not merely a zero exit code);
#   - stages already marked done in kryptos/pk9_overnight_pipeline.log are skipped.
#
# Usage:
#   bash kryptos/relaunch_pk9_sweeps.sh prepare   # rebuild engines + corpora (idempotent)
#   bash kryptos/relaunch_pk9_sweeps.sh pipeline  # P1-P4 wheel sweeps + P6 tq all-offsets
#   bash kryptos/relaunch_pk9_sweeps.sh full      # full 16,985-crib qt all-offsets (78.8B)
# Run pipeline/full via start_process, not plain background bash.
set -u
cd /home/user/Buttcrack---Cipher-Breaker
LOG=kryptos/pk9_overnight_pipeline.log
FULLLOG=kryptos/pk9_full_qt_all_offsets.log
CC="cc -O3 -march=native -fopenmp"

build() { [ -x "$2" ] || $CC -o "$2" "kryptos/$1" -lm; }

prepare() {
    build crack_pk9_q567_t8_crib.c     /tmp/crack_pk9_q567_t8_crib
    build crack_pk9_tq_grouped_cribs.c /tmp/crack_pk9_tq_grouped
    build sweep_pk9_word_wheels.c      /tmp/sweep_pk9_word_wheels
    [ -s /tmp/pk9_letter30_corrected.txt ] || python3 kryptos/generate_pk9_letter_corrected_story.py /tmp/pk9_letter30_corrected.txt
    [ -s /tmp/pk9_letter30_v2.txt ]        || python3 kryptos/generate_pk9_letter_v2.py /tmp/pk9_letter30_v2.txt
    [ -s /tmp/pk9_letter30_v2f.txt ]       || awk 'length($0)>=28' /tmp/pk9_letter30_v2.txt > /tmp/pk9_letter30_v2f.txt
    [ -s /tmp/pk9_top3000.txt ]            || head -3000 /tmp/pk9_letter30_corrected.txt > /tmp/pk9_top3000.txt
    wc -l /tmp/pk9_letter30_corrected.txt /tmp/pk9_letter30_v2.txt /tmp/pk9_letter30_v2f.txt /tmp/pk9_top3000.txt
}

# stage_complete NAME: exit 0 if the persistent log shows NAME completed with
# a genuine "stage done" marker between its STAGE header and the next separator.
stage_complete() {
    awk -v stage="STAGE: $1" '
        index($0, stage) { inside=1; done=0; next }
        inside && /^====================================================================$/ { exit (done ? 0 : 1) }
        inside && /stage done/ { done=1 }
        END { exit (done ? 0 : 1) }
    ' "$LOG"
}

run_stage() { # run_stage NAME SIGNATURE_REGEX cmd...
    local name="$1" sig="$2"; shift 2
    if stage_complete "$name"; then
        echo "[$(date -u '+%F %T')] SKIP (already done): $name" >> "$LOG"
        return 0
    fi
    echo "====================================================================" >> "$LOG"
    echo "[$(date -u '+%F %T')] STAGE: $name" >> "$LOG"
    local cap; cap=$(mktemp)
    "$@" > "$cap" 2>&1
    local rc=$?
    cat "$cap" >> "$LOG"
    rm -f "$cap"
    local stamp; stamp=$(date -u '+%F %T')
    if [ "$rc" -eq 0 ] && grep -Eq "$sig" <(tail -40 "$LOG"); then
        echo "[$stamp] stage done (exit 0, signature verified)" >> "$LOG"
    else
        echo "[$stamp] stage FAILED (exit $rc or missing signature) - will retry on next relaunch" >> "$LOG"
    fi
}

pipeline() {
    export OMP_NUM_THREADS=2
    local SW=/tmp/sweep_pk9_word_wheels TQ=/tmp/crack_pk9_tq_grouped
    echo "PK9 pipeline relaunch v2 $(date -u) (completed stages skipped; success signatures enforced)" >> "$LOG"
    # sweep engine prints a final "candidates: NNN in Xs (Y M/s)" summary on success
    local SW_SIG='candidates: [0-9]+ in [0-9.]+s'
    # tq engine prints "offset 115/115 done: ..." when the all-offsets sweep finishes
    local TQ_SIG='offset 115/115 done:'
    run_stage "P1 story-wheels x all-T8 qt" "$SW_SIG" \
        $SW kryptos/pk9_vocab_story5.txt kryptos/pk9_vocab_story6.txt kryptos/pk9_vocab_story7.txt --order qt --top 10
    run_stage "P2 broad-wheels x story-T8 qt" "$SW_SIG" \
        $SW kryptos/pk9_vocab_broad5.txt kryptos/pk9_vocab_broad6.txt kryptos/pk9_vocab_broad7.txt --t8-words kryptos/pk9_vocab_story8.txt --order qt --top 10
    run_stage "P3 pk8win-wheels x all-T8 qt" "$SW_SIG" \
        $SW kryptos/pk9_vocab_pk8win5.txt kryptos/pk9_vocab_pk8win6.txt kryptos/pk9_vocab_pk8win7.txt --order qt --top 10
    run_stage "P4 broad-wheels x theophilus-T8 qt" "$SW_SIG" \
        $SW kryptos/pk9_vocab_broad5.txt kryptos/pk9_vocab_broad6.txt kryptos/pk9_vocab_broad7.txt --t8-words kryptos/theophilus_w8.txt --order qt --top 10
    run_stage "P6 tq all-offsets top-3000 cribs" "$TQ_SIG" \
        $TQ --all-keys-all-offsets /tmp/pk9_top3000.txt
    echo "[$(date -u '+%F %T')] PIPELINE COMPLETE (P1-P4, P6)" >> "$LOG"
}

full() {
    export OMP_NUM_THREADS=1
    echo "=== relaunch $(date -u) ===" >> "$FULLLOG"
    exec /tmp/crack_pk9_q567_t8_crib --all-keys-all-offsets /tmp/pk9_letter30_corrected.txt >> "$FULLLOG" 2>&1
}

case "${1:-}" in
    prepare)  prepare ;;
    pipeline) pipeline ;;
    full)     full ;;
    *) echo "usage: $0 prepare|pipeline|full"; exit 2 ;;
esac
