/* crack_pk9_t8_q7.c — exact crib solver for PK9 under "Q(7) + T(8)" models.
 *
 * Motivation (2026-10-02): raw PK9 statistics (IoC(7)=0.0568, z(lag7)=+3.88,
 * z(lag28)=+3.64, repeated bigrams XG/GU and trigram UQG at lag 7) indicate a
 * near-period-7 keystream visible in the raw ciphertext, which requires the
 * substitution to be the LAST applied layer (tq).  The full Q(5)+Q(6)+Q(7)
 * sum-clock has period 210 > N and cannot show this with real-word wheels
 * (Monte Carlo 0/4000 per order).  This engine tests the reduced models
 * where only a period-7 wheel acts:
 *
 *   tq:  M = T8(P);  C[i] = M[i] + q7[i%7]     (T first, Q last)
 *   qt:  Z[i] = P[i] + q7[i%7];  C = T8(Z)     (Q first, T last)
 *
 * A crib of L letters pins q7's 7 residues with L-7 verification letters,
 * so a 30-letter crib gives 23 checks — false-positive rate ~26^-23 per
 * (crib, perm, offset) triple for wrong hypotheses.
 *
 * Modes:
 *   --all-keys CRIBFILE            crib at offset 0
 *   --all-keys-all-offsets CRIBFILE  crib at every offset
 *   --qt                            Q-first direction (default tq)
 *
 * Build: cc -O3 -march=native -fopenmp -o /tmp/crack_pk9_t8_q7 \
 *          kryptos/crack_pk9_t8_q7.c -lm
 * Run from repo root.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>

#define A 26
#define N 144
#define W 8
#define H 18
#define NPERM 40320
#define QSIZE (A*A*A*A)
#define MAXC 40000
#define MAXL 64

static const char *PK9_CT =
    "KSYAWFEYYOISZGEUFBLYATAIBYFAQBQYYVDWJKLJXMYIEPIFVHPQNHZGSUHUUDXLEHRHUMAL"
    "HEGLHXSJMUXGNUIVBXGUJHZRZGUSVHMLSCTSUQXHSUMQQIFUQGKHJGUQGLHDKEWSKAMHIJXD";

static const char ALPHA[A] = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
static int kidx[256], to_std[A];
static float *quad;
static unsigned char perms[NPERM][W];
static int ct[N];

static inline int qidx4(int a, int b, int c, int d) {
    return ((a * A + b) * A + c) * A + d;
}

static float *load_quads(void) {
    float *t = calloc(QSIZE, sizeof(*t));
    if (!t) exit(2);
    FILE *f = popen("gzip -cd -- 'buttcrack/data/english_quadgrams.txt.gz'", "r");
    if (!f) { fprintf(stderr, "cannot load quadgrams\n"); exit(2); }
    char line[128], g[8]; long long count, total = 0;
    while (fgets(line, sizeof(line), f)) {
        if (sscanf(line, "%7s %lld", g, &count) != 2 || strlen(g) != 4) continue;
        int a = g[0]-'A', b = g[1]-'A', c = g[2]-'A', d = g[3]-'A';
        if (a<0||a>=A||b<0||b>=A||c<0||c>=A||d<0||d>=A) continue;
        t[qidx4(a,b,c,d)] = (float)count; total += count;
    }
    if (pclose(f) != 0 || !total) { fprintf(stderr, "bad quadgram model\n"); exit(2); }
    float lt = (float)log10((double)total), fl = (float)log10(0.1/(double)total);
    for (int i = 0; i < QSIZE; i++) t[i] = t[i] > 0 ? log10f(t[i]) - lt : fl;
    return t;
}

static void make_perms(void) {
    unsigned char p[W];
    for (int i = 0; i < W; i++) p[i] = i;
    int n = 0;
    for (;;) {
        memcpy(perms[n++], p, W);
        int i = W - 2;
        while (i >= 0 && p[i] >= p[i+1]) i--;
        if (i < 0) break;
        int j = W - 1;
        while (p[j] <= p[i]) j--;
        unsigned char t = p[i]; p[i] = p[j]; p[j] = t;
        for (int a = i+1, b = W-1; a < b; a++, b--) { t = p[a]; p[a] = p[b]; p[b] = t; }
    }
    if (n != NPERM) { fprintf(stderr, "perm bug\n"); exit(2); }
}

static char cribs[MAXC][MAXL + 1];
static int ncribs, criblen[MAXC];

static void load_cribs(const char *path) {
    FILE *f = fopen(path, "r");
    if (!f) { perror(path); exit(2); }
    char line[256];
    while (fgets(line, sizeof(line), f)) {
        char buf[256]; int n = 0;
        for (char *s = line; *s && n < MAXL; s++)
            if (*s >= 'A' && *s <= 'Z') buf[n++] = *s;
        if (n < 10) continue;
        buf[n] = 0;
        if (ncribs >= MAXC) { fprintf(stderr, "too many cribs\n"); exit(2); }
        memcpy(cribs[ncribs], buf, n + 1);
        criblen[ncribs] = n;
        ncribs++;
    }
    fclose(f);
    if (!ncribs) { fprintf(stderr, "no cribs loaded\n"); exit(2); }
}

/* decrypt with perm + q7 wheel; returns plaintext (KRYPTOS indices) */
static void decrypt7(const unsigned char *order, const unsigned char *q7,
                     int qt_mode, unsigned char *plain) {
    unsigned char buf[N];
    if (qt_mode) {
        for (int r = 0; r < H; r++)
            for (int c = 0; c < W; c++)
                buf[8*r + c] = (unsigned char)ct[order[c]*H + r];
        for (int i = 0; i < N; i++)
            plain[i] = (unsigned char)((buf[i] + 26 - q7[i%7]) % 26);
    } else {
        for (int i = 0; i < N; i++)
            buf[i] = (unsigned char)((ct[i] + 26 - q7[i%7]) % 26);
        for (int r = 0; r < H; r++)
            for (int c = 0; c < W; c++)
                plain[8*r + c] = buf[order[c]*H + r];
    }
}

static float score_plain(const unsigned char *p) {
    float s = 0;
    for (int i = 0; i <= N-4; i++)
        s += quad[qidx4(to_std[p[i]], to_std[p[i+1]], to_std[p[i+2]], to_std[p[i+3]])];
    return s / N;
}

int main(int argc, char **argv) {
    const char *cribfile = NULL;
    int qt_mode = 0, all_offsets = 0;
    for (int i = 1; i < argc; i++) {
        if (!strcmp(argv[i], "--qt")) qt_mode = 1;
        else if (!strcmp(argv[i], "--all-keys-all-offsets")) { cribfile = argv[++i]; all_offsets = 1; }
        else if (!strcmp(argv[i], "--all-keys")) cribfile = argv[++i];
        else { fprintf(stderr, "usage: %s [--qt] --all-keys[-all-offsets] CRIBFILE\n", argv[0]); return 1; }
    }
    if (!cribfile) { fprintf(stderr, "need a crib file\n"); return 1; }
    for (int i = 0; i < A; i++) { kidx[(int)ALPHA[i]] = i; to_std[i] = ALPHA[i] - 'A'; }
    for (int i = 0; i < N; i++) ct[i] = kidx[(unsigned char)PK9_CT[i]];
    quad = load_quads();
    make_perms();
    load_cribs(cribfile);

    long long placements = 0, survivors = 0;
    float best_score = -1e30f;
    char best_plain[N+1] = "";
    int best_perm = -1, best_crib = -1, best_off = -1;
    unsigned char best_q7[7];
    int maxoff = all_offsets ? N - 1 : 1;
    long long total = (long long)ncribs * NPERM * (all_offsets ? N - criblen[0] + 1 : 1);
    fprintf(stderr, "mode=%s cribs=%d offsets=%s total=%.3g\n",
            qt_mode ? "qt" : "tq", ncribs, all_offsets ? "all" : "prefix", (double)total);

    double t0 = omp_get_wtime();
#pragma omp parallel for schedule(dynamic, 4) reduction(+:placements, survivors)
    for (int ci = 0; ci < ncribs; ci++) {
        const char *crib = cribs[ci];
        int L = criblen[ci];
        int offs = all_offsets ? N - L + 1 : 1;
        int cribv[MAXL];
        for (int j = 0; j < L; j++) cribv[j] = kidx[(unsigned char)crib[j]];
        for (int p = 0; p < NPERM; p++) {
            const unsigned char *order = perms[p];
            for (int o = 0; o < offs; o++) {
                placements++;
                int q7[7]; memset(q7, -1, sizeof(q7));
                int ok = 1;
                for (int j = 0; j < L; j++) {
                    int i = o + j;
                    int m = order[i % W] * H + i / W;
                    int d = qt_mode ? (i % 7) : (m % 7);
                    int v = (ct[m] - cribv[j] + 26) % 26;
                    if (q7[d] < 0) q7[d] = v;
                    else if (q7[d] != v) { ok = 0; break; }
                }
                if (!ok) continue;
                /* full crib consistent: decrypt and score */
                unsigned char q7u[7], plain[N];
                for (int d = 0; d < 7; d++) q7u[d] = (unsigned char)(q7[d] < 0 ? 0 : q7[d]);
                decrypt7(order, q7u, qt_mode, plain);
                float f = score_plain(plain);
                if (f > best_score || best_perm < 0) {
#pragma omp critical
                    if (f > best_score || best_perm < 0) {
                        best_score = f; best_perm = p; best_crib = ci; best_off = o;
                        memcpy(best_q7, q7u, 7);
                        for (int k = 0; k < N; k++) best_plain[k] = ALPHA[plain[k]];
                        best_plain[N] = 0;
                    }
                }
#pragma omp atomic
                survivors++;
            }
        }
    }
    printf("cribs=%d placements=%lld full-crib survivors=%lld elapsed=%.1fs\n",
           ncribs, placements, survivors, omp_get_wtime() - t0);
    printf("best score=%.4f perm#%d crib#%d offset=%d q7=[", best_score, best_perm, best_crib, best_off);
    for (int d = 0; d < 7; d++) printf("%d%s", best_q7[d], d < 6 ? "," : "");
    printf("]\norder=");
    if (best_perm >= 0) for (int c = 0; c < W; c++) printf("%d%s", perms[best_perm][c], c < 7 ? "," : "");
    printf("\nP=%s\n", best_plain);
    if (best_crib >= 0) printf("crib=%s\n", cribs[best_crib]);
    return 0;
}
