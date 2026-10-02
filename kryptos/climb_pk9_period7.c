/* climb_pk9_period7.c — order-discrimination + near-period-7 attack on PK9.
 *
 * Motivation (2026-10-02): raw PK9 shows IoC(7)=0.0568, z(lag7)=+3.88,
 * z(lag28)=+3.64 while random wheels in EITHER order essentially never do
 * (Monte Carlo 0/4000 each).  All period-7 diagnostics are invariant to the
 * q7 wheel; under tq (T8 first) they are also invariant to sigma.  Elevated
 * IoC(7) on raw ciphertext therefore implies the keystream is close to
 * period 7, i.e. q5+q6 nearly constant, their constant part folding into q7.
 *
 * Attack: for every one of the 8! column orders sigma and both layer orders,
 * hill-climb q7[0..6] under the pure-period-7 model and score the implied
 * plaintext with English quadgrams.  Then refine the best (sigma, q7) seeds
 * with the full q5/q6/q7 wheel set (18 values) plus sigma column swaps.
 *
 *   tq (T8 then Q567):  M = T8(P);  C[i] = M[i] + s[i]
 *       decrypt: M = C - s;  P[8r+c] = M[order[c]*18 + r]
 *   qt (Q567 then T8):  Z[i] = P[i] + s[i];  C = T8(Z)
 *       decrypt: Z[8r+c] = C[order[c]*18 + r];  P = Z - s
 *
 * Build: cc -O3 -march=native -fopenmp -o /tmp/climb_pk9_period7 \
 *          kryptos/climb_pk9_period7.c -lm
 * Run from repo root:  /tmp/climb_pk9_period7 --tq      and/or  --qt
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
#define TOPK 12
#define SEEDS 300

static const char *PK9_CT =
    "KSYAWFEYYOISZGEUFBLYATAIBYFAQBQYYVDWJKLJXMYIEPIFVHPQNHZGSUHUUDXLEHRHUMAL"
    "HEGLHXSJMUXGNUIVBXGUJHZRZGUSVHMLSCTSUQXHSUMQQIFUQGKHJGUQGLHDKEWSKAMHIJXD";

static const char ALPHA[A] = "KRYPTOSABCDEFGHIJLMNQUVWXZ"; /* KRYPTOS-index -> letter */
static int kidx[256], to_std[A];
static float *quad;

typedef struct {
    float score;                 /* per-character quadgram score */
    int order;                   /* perm index */
    unsigned char order_arr[W];
    unsigned char q5[5], q6[6], q7[7];
    char plain[N + 1];
} Cand;

static unsigned char perms[NPERM][W];
static int ct[N];                /* ciphertext as KRYPTOS indices */
static unsigned char self_ct[N];   /* self-test ciphertext */

static inline int qidx(int a, int b, int c, int d) {
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
        int a = g[0] - 'A', b = g[1] - 'A', c = g[2] - 'A', d = g[3] - 'A';
        if (a < 0 || a >= A || b < 0 || b >= A || c < 0 || c >= A || d < 0 || d >= A) continue;
        t[qidx(a, b, c, d)] = (float)count; total += count;
    }
    if (pclose(f) != 0 || !total) { fprintf(stderr, "bad quadgram model\n"); exit(2); }
    float lt = (float)log10((double)total), fl = (float)log10(0.1 / (double)total);
    for (int i = 0; i < QSIZE; i++) t[i] = t[i] > 0 ? log10f(t[i]) - lt : fl;
    return t;
}

static void make_perms(void) {
    unsigned char p[W];
    for (int i = 0; i < W; i++) p[i] = i;
    int n = 0;
    for (;;) {
        memcpy(perms[n++], p, W);
        /* next permutation */
        int i = W - 2;
        while (i >= 0 && p[i] >= p[i + 1]) i--;
        if (i < 0) break;
        int j = W - 1;
        while (p[j] <= p[i]) j--;
        unsigned char t = p[i]; p[i] = p[j]; p[j] = t;
        for (int a = i + 1, b = W - 1; a < b; a++, b--) { t = p[a]; p[a] = p[b]; p[b] = t; }
    }
    if (n != NPERM) { fprintf(stderr, "perm count %d\n", n); exit(2); }
}

/* score a KRYPTOS-index plaintext, per character */
static inline float score_plain(const unsigned char *p) {
    float s = 0;
    for (int i = 0; i <= N - 4; i++)
        s += quad[qidx(to_std[p[i]], to_std[p[i+1]], to_std[p[i+2]], to_std[p[i+3]])];
    return s / N;
}

/* decrypt with given order + wheels; fills plain[N] (KRYPTOS indices) */
static void decrypt(const unsigned char *order, const unsigned char *q5,
                    const unsigned char *q6, const unsigned char *q7,
                    int qt_mode, unsigned char *plain) {
    unsigned char buf[N];
    if (qt_mode) {
        /* Z[8r+c] = C[order[c]*H + r]; P = Z - s */
        for (int r = 0; r < H; r++)
            for (int c = 0; c < W; c++)
                buf[8 * r + c] = ct[order[c] * H + r];
        for (int i = 0; i < N; i++)
            plain[i] = (unsigned char)((buf[i] + 26 - q5[i % 5] - q6[i % 6] - q7[i % 7]) % 26);
    } else {
        /* M = C - s; P[8r+c] = M[order[c]*H + r] */
        for (int i = 0; i < N; i++)
            buf[i] = (unsigned char)((ct[i] + 26 - q5[i % 5] - q6[i % 6] - q7[i % 7]) % 26);
        for (int r = 0; r < H; r++)
            for (int c = 0; c < W; c++)
                plain[8 * r + c] = buf[order[c] * H + r];
    }
}

/* hill-climb q7 (pure period-7 model) for one order; returns score, fills best7 */
static float climb7_real(const unsigned char *order, int qt_mode, unsigned char *best7,
                         unsigned char *plain_out) {
    unsigned char q5z[5] = {0}, q6z[6] = {0}, q7[7] = {0}, plain[N];
    decrypt(order, q5z, q6z, q7, qt_mode, plain);
    float best = score_plain(plain);
    for (int pass = 0; pass < 6; pass++) {
        int improved = 0;
        for (int d = 0; d < 7; d++) {
            int cur = q7[d], bestv = cur;
            float bestf = best;
            for (int v = 0; v < 26; v++) {
                if (v == cur) continue;
                q7[d] = (unsigned char)v;
                decrypt(order, q5z, q6z, q7, qt_mode, plain);
                float f = score_plain(plain);
                if (f > bestf) { bestf = f; bestv = v; }
            }
            q7[d] = (unsigned char)bestv;
            if (bestv != cur) { best = bestf; improved = 1; }
        }
        if (!improved) break;
    }
    decrypt(order, q5z, q6z, q7, qt_mode, plain);
    memcpy(best7, q7, 7);
    if (plain_out) memcpy(plain_out, plain, N);
    return best;
}

/* full refinement: 18 wheels + sigma column swaps, seeded from period-7 climb */
static float refine(const unsigned char *order0, int qt_mode, unsigned char *q5,
                    unsigned char *q6, unsigned char *q7, unsigned char *plain_out,
                    unsigned char *order_out) {
    unsigned char order[W], plain[N], torder[W];
    memcpy(order, order0, W);
    unsigned char q5z[5] = {0}, q6z[6] = {0};
    decrypt(order, q5z, q6z, q7, qt_mode, plain);
    float best = score_plain(plain);
    int improved = 1;
    while (improved) {
        improved = 0;
        /* wheels */
        for (int d = 0; d < 5; d++)
            for (int v = 0; v < 26; v++) {
                if (v == q5[d]) continue;
                int old = q5[d]; q5[d] = (unsigned char)v;
                decrypt(order, q5, q6, q7, qt_mode, plain);
                float f = score_plain(plain);
                if (f > best) best = f; else q5[d] = (unsigned char)old;
            }
        for (int d = 0; d < 6; d++)
            for (int v = 0; v < 26; v++) {
                if (v == q6[d]) continue;
                int old = q6[d]; q6[d] = (unsigned char)v;
                decrypt(order, q5, q6, q7, qt_mode, plain);
                float f = score_plain(plain);
                if (f > best) best = f; else q6[d] = (unsigned char)old;
            }
        for (int d = 0; d < 7; d++)
            for (int v = 0; v < 26; v++) {
                if (v == q7[d]) continue;
                int old = q7[d]; q7[d] = (unsigned char)v;
                decrypt(order, q5, q6, q7, qt_mode, plain);
                float f = score_plain(plain);
                if (f > best) best = f; else q7[d] = (unsigned char)old;
            }
        /* sigma: swap pairs of columns */
        for (int a = 0; a < W; a++)
            for (int b = a + 1; b < W; b++) {
                memcpy(torder, order, W);
                unsigned char t = torder[a]; torder[a] = torder[b]; torder[b] = t;
                decrypt(torder, q5, q6, q7, qt_mode, plain);
                float f = score_plain(plain);
                if (f > best) { best = f; memcpy(order, torder, W); improved = 1; }
            }
        /* re-run wheel passes counts as improvement only if score rose */
        float before = best;
        (void)before;
    }
    decrypt(order, q5, q6, q7, qt_mode, plain);
    memcpy(order_out, order, W);
    if (plain_out) memcpy(plain_out, plain, N);
    return best;
}

static void print_cand(const char *tag, const Cand *c) {
    char ord[3 * W]; int o = 0;
    for (int i = 0; i < W; i++) o += sprintf(ord + o, "%d,", c->order_arr[i]);
    ord[o - 1] = 0;
    char q5s[32] = "", q6s[32] = "", q7s[32] = "";
    for (int i = 0; i < 5; i++) sprintf(q5s + strlen(q5s), "%d,", c->q5[i]);
    for (int i = 0; i < 6; i++) sprintf(q6s + strlen(q6s), "%d,", c->q6[i]);
    for (int i = 0; i < 7; i++) sprintf(q7s + strlen(q7s), "%d,", c->q7[i]);
    q5s[strlen(q5s) - 1] = 0; q6s[strlen(q6s) - 1] = 0; q7s[strlen(q7s) - 1] = 0;
    printf("%s score=%.4f order=%s\n  q5=[%s] q6=[%s] q7=[%s]\n  P=%s\n", tag,
           c->score, ord, q5s, q6s, q7s, c->plain);
}



/* English letter frequencies (standard alphabet order) for chi-square */
static const double ENG_FREQ[26] = {
    0.08167, 0.01492, 0.02782, 0.04253, 0.12702, 0.02228, 0.02015, 0.06094,
    0.06966, 0.00153, 0.00772, 0.04025, 0.02406, 0.06749, 0.07507, 0.01929,
    0.00095, 0.05987, 0.06327, 0.09056, 0.02758, 0.00978, 0.02360, 0.00150,
    0.01974, 0.00074};

/* chi-square score of a KRYPTOS-index buffer against English (lower better) */
static double chi2_buf(const unsigned char *b, int n) {
    int cnt[A] = {0};
    for (int i = 0; i < n; i++) cnt[b[i]]++;
    double s = 0;
    for (int v = 0; v < A; v++) {
        double e = ENG_FREQ[to_std[v]] * n;
        double d = cnt[v] - e;
        s += d * d / (e + 1e-9);
    }
    return s;
}

/* build the "shift-class buffer": for each i<N, buf[i] = index whose keystream
 * class is i%7 (tq: the C stream itself; qt: the Z stream after untranspose).
 * For chi-init we need, per class d, the letters C[i] (tq) or Z[i] (qt). */
static void class_letters(const unsigned char *order, int qt_mode,
                          unsigned char out[7][N], int cnt[7]) {
    memset(cnt, 0, 7 * sizeof(int));
    if (qt_mode) {
        unsigned char z[N];
        for (int r = 0; r < H; r++)
            for (int c = 0; c < W; c++)
                z[8 * r + c] = ct[order[c] * H + r];
        for (int i = 0; i < N; i++) { int d = i % 7; out[d][cnt[d]++] = z[i]; }
    } else {
        for (int i = 0; i < N; i++) { int d = i % 7; out[d][cnt[d]++] = ct[i]; }
    }
}

/* per-coset Caesar chi-square init for q7 (pure period-7 model) */
static void chi_init7(const unsigned char *order, int qt_mode, unsigned char *q7) {
    unsigned char letters[7][N];
    int cnt[7];
    class_letters(order, qt_mode, letters, cnt);
    for (int d = 0; d < 7; d++) {
        double best = 1e18; int bestv = 0;
        for (int v = 0; v < 26; v++) {
            unsigned char tmp[N];
            for (int i = 0; i < cnt[d]; i++) tmp[i] = (unsigned char)((letters[d][i] + 26 - v) % 26);
            double c = chi2_buf(tmp, cnt[d]);
            if (c < best) { best = c; bestv = v; }
        }
        q7[d] = (unsigned char)bestv;
    }
}


/* hill-climb q7 from chi-square init */
static float climb7_chi(const unsigned char *order, int qt_mode, unsigned char *best7,
                        unsigned char *plain_out) {
    unsigned char q5z[5] = {0}, q6z[6] = {0}, q7[7], plain[N];
    chi_init7(order, qt_mode, q7);
    decrypt(order, q5z, q6z, q7, qt_mode, plain);
    float best = score_plain(plain);
    for (int pass = 0; pass < 6; pass++) {
        int improved = 0;
        for (int d = 0; d < 7; d++) {
            int cur = q7[d], bestv = cur;
            float bestf = best;
            for (int v = 0; v < 26; v++) {
                if (v == cur) continue;
                q7[d] = (unsigned char)v;
                decrypt(order, q5z, q6z, q7, qt_mode, plain);
                float f = score_plain(plain);
                if (f > bestf) { bestf = f; bestv = v; }
            }
            q7[d] = (unsigned char)bestv;
            if (bestv != cur) { best = bestf; improved = 1; }
        }
        if (!improved) break;
    }
    decrypt(order, q5z, q6z, q7, qt_mode, plain);
    memcpy(best7, q7, 7);
    if (plain_out) memcpy(plain_out, plain, N);
    return best;
}

/* self-test: plant a known (sigma, q7) and confirm recovery */
static int self_test(int qt_mode) {
    unsigned char order[W] = {5, 2, 7, 0, 4, 1, 6, 3};
    unsigned char q7[7] = {3, 17, 8, 22, 1, 14, 6};
    const char *PT = "THEWHITESMITHSLETTERARRIVEDONATUESDAYMORNINGBRINGINGNEWSTHATTHE"
                     "GUTTERNEEDLEWASFINISHEDATLASTANDTHATIHADTOPICKITUPMYSELFBY"
                     "MIDNIGHTTOTAKETHEONEOFTENYEARSOFTENWORKANDONEOFMYOWNMAKINGDONE";
    unsigned char p[N], z[N];
    for (int i = 0; i < N; i++) p[i] = kidx[(unsigned char)PT[i]];
    if (qt_mode) {
        for (int i = 0; i < N; i++) z[i] = (unsigned char)((p[i] + q7[i % 7]) % 26);
        /* C[order[c]*H + r] = Z[8r + c] */
        for (int r = 0; r < H; r++)
            for (int c = 0; c < W; c++)
                self_ct[order[c] * H + r] = z[8 * r + c];
    } else {
        /* M[order[c]*H + r] = P[8r + c]; C = M + q7 */
        for (int r = 0; r < H; r++)
            for (int c = 0; c < W; c++)
                self_ct[order[c] * H + r] = (unsigned char)((p[8 * r + c] + q7[order[c] % 7 == 0 ? 0 : 0]) % 26);
        /* NOTE: keystream index is the M position, not the P position */
        for (int r = 0; r < H; r++)
            for (int c = 0; c < W; c++) {
                int mpos = order[c] * H + r;
                self_ct[mpos] = (unsigned char)((p[8 * r + c] + q7[mpos % 7]) % 26);
            }
    }
    /* swap ct -> self_ct, climb, swap back */
    unsigned char save[N];
    memcpy(save, ct, N);
    memcpy(ct, self_ct, N);
    unsigned char g7[7], plain[N];
    float f = climb7_chi(order, qt_mode, g7, plain);
    int ok = 1;
    for (int i = 0; i < N; i++) if (plain[i] != p[i]) ok = 0;
    printf("[self-test %s] recovered=%d score=%.4f q7=[", qt_mode ? "qt" : "tq", ok, f);
    for (int d = 0; d < 7; d++) printf("%d,", g7[d]);
    printf("]\n");
    if (!ok) {
        char buf[N + 1];
        for (int i = 0; i < N; i++) buf[i] = ALPHA[plain[i]];
        buf[N] = 0;
        printf("  got: %s\n", buf);
    }
    memcpy(ct, save, N);
    return ok;
}

static void init_cand(Cand *c) { memset(c, 0, sizeof(*c)); c->score = -1e30f; }

int main(int argc, char **argv) {
    int qt_mode = 0;
    for (int i = 1; i < argc; i++) {
        if (!strcmp(argv[i], "--qt")) qt_mode = 1;
        else if (!strcmp(argv[i], "--tq")) qt_mode = 0;
        else if (!strcmp(argv[i], "--self-test")) {
            for (int i2 = 0; i2 < A; i2++) { kidx[(int)ALPHA[i2]] = i2; to_std[i2] = ALPHA[i2] - 'A'; }
            quad = load_quads(); make_perms();
            int ok1 = self_test(0), ok2 = self_test(1);
            printf("self-test: tq %s, qt %s\n", ok1 ? "PASS" : "FAIL", ok2 ? "PASS" : "FAIL");
            return (ok1 && ok2) ? 0 : 1;
        }
        else { fprintf(stderr, "usage: %s --tq|--qt\n", argv[0]); return 1; }
    }
    for (int i = 0; i < A; i++) { kidx[(int)ALPHA[i]] = i; to_std[i] = ALPHA[i] - 'A'; }
    for (int i = 0; i < N; i++) ct[i] = kidx[(unsigned char)PK9_CT[i]];
    quad = load_quads();
    make_perms();

    Cand top[TOPK];
    for (int k = 0; k < TOPK; k++) init_cand(&top[k]);
    double t0 = omp_get_wtime();

#pragma omp parallel
    {
        Cand loc[TOPK];
        for (int k = 0; k < TOPK; k++) init_cand(&loc[k]);
#pragma omp for schedule(dynamic, 16)
        for (int p = 0; p < NPERM; p++) {
            unsigned char q7[7], plain[N];
            float f = climb7_chi(perms[p], qt_mode, q7, plain);
            if (f <= loc[TOPK - 1].score) continue;
            Cand c; init_cand(&c);
            c.score = f; c.order = p;
            memcpy(c.order_arr, perms[p], W);
            memcpy(c.q7, q7, 7);
            for (int i = 0; i < N; i++) c.plain[i] = ALPHA[plain[i]];
            loc[TOPK - 1] = c;
            for (int k = TOPK - 1; k > 0 && loc[k].score > loc[k - 1].score; k--) {
                Cand t = loc[k]; loc[k] = loc[k - 1]; loc[k - 1] = t;
            }
        }
#pragma omp critical
        {
            for (int k = 0; k < TOPK; k++) {
                if (loc[k].score <= -1e29f) break;
                if (loc[k].score > top[TOPK - 1].score) {
                    top[TOPK - 1] = loc[k];
                    for (int m = TOPK - 1; m > 0 && top[m].score > top[m - 1].score; m--) {
                        Cand t = top[m]; top[m] = top[m - 1]; top[m - 1] = t;
                    }
                }
            }
        }
    }

    printf("[%s] stage 1 (period-7 climb over all 8! orders): %.1fs\n",
           qt_mode ? "qt" : "tq", omp_get_wtime() - t0);
    for (int k = 0; k < TOPK && top[k].score > -1e29f; k++) print_cand("S1", &top[k]);

    /* stage 2: refine stage-1 top with full q5/q6 wheels + sigma swaps */
    t0 = omp_get_wtime();
    Cand best2; init_cand(&best2);
#pragma omp parallel
    {
        Cand bloc; init_cand(&bloc);
#pragma omp for schedule(dynamic, 1)
        for (int k = 0; k < TOPK; k++) {
            unsigned char q5[5] = {0}, q6[6] = {0}, q7[7], plain[N], order[W];
            memcpy(q7, top[k].q7, 7);
            float f = refine(top[k].order_arr, qt_mode, q5, q6, q7, plain, order);
            if (f > bloc.score) {
                bloc.score = f;
                memcpy(bloc.order_arr, order, W);
                memcpy(bloc.q5, q5, 5); memcpy(bloc.q6, q6, 6); memcpy(bloc.q7, q7, 7);
                for (int i = 0; i < N; i++) bloc.plain[i] = ALPHA[plain[i]];
            }
        }
#pragma omp critical
        if (bloc.score > best2.score) best2 = bloc;
    }
    printf("[%s] stage 2 (full-wheel refinement): %.1fs\n", qt_mode ? "qt" : "tq",
           omp_get_wtime() - t0);
    if (best2.score > -1e29f) print_cand("S2", &best2);
    return 0;
}
