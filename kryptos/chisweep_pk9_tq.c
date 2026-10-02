/* chisweep_pk9_tq.c — sigma-free wheel attack on PK9 under the TQ order.
 *
 * Key fact (validated on planted controls): under tq,
 *      C[i] = M[i] + q5[i%5] + q6[i%6] + q7[i%7],  M = T8(P),
 * the letter MULTISET of P-hat[i] = C[i] - q5[i%5] - q6[i%6] - q7[i%7]
 * equals the plaintext's multiset regardless of the T8 permutation, because
 * a transposition only permutes positions.  The chi-square of that multiset
 * against English letter frequencies is therefore a wheel-only statistic:
 * planted true wheels give chi2 ~= 23-60 while the best of 2000 random
 * wheel sets gives 262+ (10x separation).
 *
 * Modes:
 *   --words V5 V6 V7 [--threshold 120]
 *        enumerate every wheel-word triple, keep those below threshold,
 *        then verify survivors over all 8! T8 orders with quadgrams.
 *   --climb [restarts] [--threshold 120]
 *        multi-restart coordinate descent on the chi2 landscape over all
 *        (possibly non-word) wheels; distinct minima below threshold are
 *        verified over all 8! orders with quadgrams.
 *
 * Build: cc -O3 -march=native -fopenmp -o /tmp/chisweep_pk9_tq \
 *          kryptos/chisweep_pk9_tq.c -lm
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
#define NV 18
#define NPERM 40320
#define QSIZE (A*A*A*A)
#define MAXV 40000
#define MAXCAND 30000

static const char *PK9_CT =
    "KSYAWFEYYOISZGEUFBLYATAIBYFAQBQYYVDWJKLJXMYIEPIFVHPQNHZGSUHUUDXLEHRHUMAL"
    "HEGLHXSJMUXGNUIVBXGUJHZRZGUSVHMLSCTSUQXHSUMQQIFUQGKHJGUQGLHDKEWSKAMHIJXD";
static const char ALPHA[A] = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
static int kidx[256], to_std[A];
static float *quad;
static unsigned char perms[NPERM][W];
static int ct[N];
static double engk[A];            /* English freq indexed by KRYPTOS index */

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
}

/* chi-square of the implied plaintext multiset against English */
static inline double wheel_chi2(const unsigned char *x) {
    int cnt[A] = {0};
    for (int i = 0; i < N; i++) {
        int p = ct[i] - x[i % 5] - x[5 + (i % 6)] - x[11 + (i % 7)];
        p %= A; if (p < 0) p += A;
        cnt[p]++;
    }
    double s = 0;
    for (int v = 0; v < A; v++) {
        double e = engk[v] * N;
        double d = cnt[v] - e;
        s += d * d / e;
    }
    return s;
}

static void decrypt_tq(const unsigned char *order, const unsigned char *x,
                       unsigned char *plain) {
    for (int i = 0; i < N; i++) {
        int m = order[i % W] * H + i / W;
        plain[i] = (unsigned char)((ct[m] + 3 * A - x[m % 5] - x[5 + m % 6] - x[11 + m % 7]) % A);
    }
}
static float score_plain(const unsigned char *p) {
    float s = 0;
    for (int i = 0; i <= N - 4; i++)
        s += quad[qidx4(to_std[p[i]], to_std[p[i+1]], to_std[p[i+2]], to_std[p[i+3]])];
    return s / N;
}

/* ---- candidate set -------------------------------------------------- */
typedef struct { unsigned char x[NV]; double chi2; } Cand;
static Cand cands[MAXCAND];
static int ncand;

static int cand_insert(const unsigned char *x, double chi2) {
    /* canonical: gauge q5[0]=q6[0]=0 */
    unsigned char c[NV];
    int a = x[0], b = x[5];
    for (int v = 0; v < 5; v++) c[v] = (unsigned char)((x[v] + A - a) % A);
    for (int v = 5; v < 11; v++) c[v] = (unsigned char)((x[v] + A - b) % A);
    for (int v = 11; v < 18; v++) c[v] = (unsigned char)((x[v] + a + b) % A);
    for (int i = 0; i < ncand; i++)
        if (!memcmp(cands[i].x, c, NV)) return 0;
    if (ncand >= MAXCAND) return 0;
    memcpy(cands[ncand].x, c, NV);
    cands[ncand].chi2 = chi2;
    ncand++;
    return 1;
}

static int cmp_cand(const void *pa, const void *pb) {
    const Cand *a = pa, *b = pb;
    return a->chi2 < b->chi2 ? -1 : a->chi2 > b->chi2 ? 1 : 0;
}

/* ---- verify candidates over all perms ---------------------------------- */
static void verify_cands(int maxverify) {
    qsort(cands, ncand, sizeof(Cand), cmp_cand);
    int nv = ncand < maxverify ? ncand : maxverify;
    fprintf(stderr, "verifying %d of %d candidates over %d perms...\n", nv, ncand, NPERM);
    float bestf = -1e30f;
#pragma omp parallel
    {
        float locf = -1e30f;
        unsigned char plain[N];
#pragma omp for schedule(dynamic, 1)
        for (int ci = 0; ci < nv; ci++) {
            for (int p = 0; p < NPERM; p++) {
                decrypt_tq(perms[p], cands[ci].x, plain);
                float f = score_plain(plain);
                if (f > locf) {
                    locf = f;
#pragma omp critical
                    {
                        if (f > bestf) {
                            bestf = f;
                            char pb[N + 1];
                            for (int k = 0; k < N; k++) pb[k] = ALPHA[plain[k]];
                            pb[N] = 0;
                            char ord[3 * W]; int o = 0;
                            for (int c = 0; c < W; c++) o += sprintf(ord + o, "%d,", perms[p][c]);
                            ord[o - 1] = 0;
                            printf("BEST %.4f chi2=%.1f cand#%d order=%s\n  q5=[%d,%d,%d,%d,%d] q6=[%d,%d,%d,%d,%d,%d] q7=[%d,%d,%d,%d,%d,%d,%d]\n  P=%s\n",
                                   f, cands[ci].chi2, ci, ord,
                                   cands[ci].x[0], cands[ci].x[1], cands[ci].x[2], cands[ci].x[3], cands[ci].x[4],
                                   cands[ci].x[5], cands[ci].x[6], cands[ci].x[7], cands[ci].x[8], cands[ci].x[9], cands[ci].x[10],
                                   cands[ci].x[11], cands[ci].x[12], cands[ci].x[13], cands[ci].x[14], cands[ci].x[15], cands[ci].x[16], cands[ci].x[17],
                                   pb);
                            fflush(stdout);
                        }
                    }
                }
            }
        }
    }
}

/* ---- word vocab --------------------------------------------------------- */
static int load_words(const char *path, unsigned char w[MAXV][NV], int len) {
    FILE *f = fopen(path, "r");
    if (!f) { perror(path); exit(2); }
    char line[64]; int n = 0;
    while (fgets(line, sizeof(line), f)) {
        char s[32]; int k = 0;
        for (char *p = line; *p && k < 31; p++) if (*p >= 'A' && *p <= 'Z') s[k++] = *p;
        s[k] = 0;
        if (k != len || n >= MAXV) continue;
        for (int i = 0; i < len; i++) w[n][i] = (unsigned char)kidx[(unsigned char)s[i]];
        n++;
    }
    fclose(f);
    if (!n) { fprintf(stderr, "no %d-letter words in %s\n", len, path); exit(2); }
    return n;
}

int main(int argc, char **argv) {
    double threshold = 120.0;
    int restarts = 20000, maxverify = 2000;
    const char *v5p = NULL, *v6p = NULL, *v7p = NULL;
    int words_mode = 0;
    for (int i = 1; i < argc; i++) {
        if (!strcmp(argv[i], "--words")) { words_mode = 1; v5p = argv[++i]; v6p = argv[++i]; v7p = argv[++i]; }
        else if (!strcmp(argv[i], "--climb")) words_mode = 0;
        else if (!strcmp(argv[i], "--threshold")) threshold = atof(argv[++i]);
        else if (!strcmp(argv[i], "--restarts")) restarts = atoi(argv[++i]);
        else if (!strcmp(argv[i], "--maxverify")) maxverify = atoi(argv[++i]);
        else { fprintf(stderr, "usage: see source\n"); return 1; }
    }
    static const double ENG[26] = {
        0.08167, 0.01492, 0.02782, 0.04253, 0.12702, 0.02228, 0.02015, 0.06094,
        0.06966, 0.00153, 0.00772, 0.04025, 0.02406, 0.06749, 0.07507, 0.01929,
        0.00095, 0.05987, 0.06327, 0.09056, 0.02758, 0.00978, 0.02360, 0.00150,
        0.01974, 0.00074};
    for (int i = 0; i < A; i++) { kidx[(int)ALPHA[i]] = i; to_std[i] = ALPHA[i] - 'A'; engk[i] = ENG[to_std[i]]; }
    for (int i = 0; i < N; i++) ct[i] = kidx[(unsigned char)PK9_CT[i]];
    quad = load_quads();
    make_perms();
    double t0 = omp_get_wtime();

    if (words_mode) {
        static unsigned char w5[MAXV][NV], w6[MAXV][NV], w7[MAXV][NV];
        int n5 = load_words(v5p, w5, 5), n6 = load_words(v6p, w6, 6), n7 = load_words(v7p, w7, 7);
        printf("vocab: %d x %d x %d = %.3g triples\n", n5, n6, n7, (double)n5 * n6 * n7);
        long long below = 0;
#pragma omp parallel for schedule(dynamic, 64) reduction(+:below)
        for (int i = 0; i < n5; i++) {
            unsigned char x[NV];
            for (int j = 0; j < n6; j++) {
                for (int k = 0; k < n7; k++) {
                    memcpy(x, w5[i], 5); memcpy(x + 5, w6[j], 6); memcpy(x + 11, w7[k], 7);
                    double c = wheel_chi2(x);
                    if (c < threshold) {
#pragma omp critical
                        { if (cand_insert(x, c)) below++; }
                    }
                }
            }
        }
        printf("word triples below chi2<%.0f: %lld distinct (of %.3g), %.1fs\n",
               threshold, below, (double)n5 * n6 * n7, omp_get_wtime() - t0);
    } else {
        printf("climb mode: %d restarts\n", restarts);
        unsigned rng = 987654321u;
        int found = 0;
#pragma omp parallel
        {
            unsigned lr = rng + omp_get_thread_num() * 7919u;
#pragma omp for schedule(dynamic, 1) reduction(+:found)
            for (int r = 0; r < restarts; r++) {
                unsigned char x[NV];
                for (int v = 0; v < NV; v++) { lr = lr * 1103515245u + 12345u; x[v] = (unsigned char)((lr >> 16) % A); }
                double best = wheel_chi2(x);
                int improved = 1;
                while (improved) {
                    improved = 0;
                    for (int d = 0; d < NV; d++) {
                        if (d == 0 || d == 5) continue;   /* gauge-fixed */
                        int cur = x[d], bv = cur;
                        double bf = best;
                        for (int v2 = 0; v2 < A; v2++) {
                            if (v2 == cur) continue;
                            x[d] = (unsigned char)v2;
                            double c = wheel_chi2(x);
                            if (c < bf) { bf = c; bv = v2; }
                        }
                        x[d] = (unsigned char)bv;
                        if (bv != cur) { best = bf; improved = 1; }
                    }
                }
                if (best < threshold) {
#pragma omp critical
                    { if (cand_insert(x, best)) found++; }
                }
            }
        }
        printf("climb: %d distinct minima below chi2<%.0f (%d restarts), %.1fs\n",
               found, threshold, restarts, omp_get_wtime() - t0);
    }
    verify_cands(maxverify);
    printf("done %.1fs\n", omp_get_wtime() - t0);
    return 0;
}
