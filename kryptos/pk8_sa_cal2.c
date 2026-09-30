/* Calibrated quadgram-SA attack on PK8-shaped 4-clock sum ciphers.
 *
 * Calibration protocol (mirrors pk8_basin_probe.py / pk8_emda.py):
 *   1. --synthetic: encrypt a known 153-letter English window with random
 *      {4,5,6,7} wheels and try to recover it.  Budgets are meaningless
 *      until the recovery rate here is known.
 *   2. --real: attack the actual PK8 ciphertext under the SAME budget.
 *      Failure after synthetic success refutes the hypothesis (alphabet,
 *      wheel set), not the search.
 *
 * Alphabet variants: --alpha k = Kryptos (default), --alpha a = standard A-Z.
 * Refuting one alphabet does not refute the other.
 *
 * gcc -O3 -o pk8_sa_cal2 pk8_sa_cal2.c -lm   (add -fopenmp if available)
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <stdint.h>
#include <time.h>
#ifdef _OPENMP
#include <omp.h>
#endif

#define N 153
#define FLOOR (-9.5f)

static const char *KTEXT = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
static const char *ATEXT = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";
static const char *PK8 = "COPVEJJVSVURTVIPYOTPLHGBTMAUCCPESIWIGZBWSJPKTRPUEKQFIFCLHMXTHIMHWOYIGURBOMPARCVXVKBDDVBVHDRHGCVNWWVLBMYWMWHICFIXZWBVZYCQGNOGJGUMLNPUTHQCXNWPQZOIRJZGSWVPY";

/* A 153-letter English window (from examples/english_samples.txt). */
static const char *SYNTH_PT =
    "THERAILWAYSTATIONATASHFORDWASCROWDEDWITHTRAVELLERSWAITINGFORTHEDELAYEXPRESSANDTHESTATIONMASTERWALKEDUPANDDOWNTHEPLATFORMWITHHISHANDSBEHINDHISBACKMUTTERINGABOUTTHEWEATHERANDTH";

static float quad[26][26][26][26];
static int ct_idx[N];
static int k2s[26]; /* cipher-index -> standard letter index */

static void load_quads(const char *path) {
    for (int a = 0; a < 26; a++) for (int b = 0; b < 26; b++)
        for (int c = 0; c < 26; c++) for (int d = 0; d < 26; d++)
            quad[a][b][c][d] = FLOOR;
    FILE *f = fopen(path, "r");
    if (!f) { fprintf(stderr, "cannot open %s\n", path); exit(1); }
    char q[32]; float sc;
    while (fscanf(f, "%31s %f", q, &sc) == 2) {
        if (strlen(q) == 4) {
            int a=q[0]-'A', b=q[1]-'A', c=q[2]-'A', d=q[3]-'A';
            if ((unsigned)a<26&&(unsigned)b<26&&(unsigned)c<26&&(unsigned)d<26)
                quad[a][b][c][d] = sc;
        }
    }
    fclose(f);
}

static inline uint32_t xs(uint32_t *s){uint32_t x=*s;x^=x<<13;x^=x>>17;x^=x<<5;*s=x;return x;}

typedef struct { int w[22]; } Wheels; /* q4[4] q5[5] q6[6] q7[7], q4[0]=0 gauge */

static void decrypt_pt(const Wheels *W, int *pt) {
    for (int i = 0; i < N; i++) {
        int k = (W->w[i%4] + W->w[4 + i%5] + W->w[9 + i%6] + W->w[15 + i%7]) % 26;
        pt[i] = k2s[(ct_idx[i] - k + 26) % 26];
    }
}
static inline float score_pt(const int *pt) {
    float s = 0.0f;
    for (int i = 0; i < N-3; i++) s += quad[pt[i]][pt[i+1]][pt[i+2]][pt[i+3]];
    return s / (N-3);
}

/* exact greedy coordinate polish */
static float polish(Wheels *W, int *pt) {
    float best = score_pt(pt);
    int improved = 1, guard = 0;
    while (improved && guard++ < 40) {
        improved = 0;
        for (int slot = 1; slot < 22; slot++) { /* slot 0 is gauge */
            int orig = W->w[slot];
            int bestv = orig; float bestf = best;
            for (int v = 0; v < 26; v++) {
                if (v == orig) continue;
                W->w[slot] = v;
                decrypt_pt(W, pt);
                float f = score_pt(pt);
                if (f > bestf) { bestf = f; bestv = v; }
            }
            W->w[slot] = bestv;
            if (bestf > best + 1e-6f) { best = bestf; improved = 1; }
            decrypt_pt(W, pt);
        }
    }
    return best;
}

static float sa_run(Wheels *W, uint32_t *rng, long steps, float t0, float t1, int *pt) {
    decrypt_pt(W, pt);
    float cur = score_pt(pt);
    Wheels Wb = *W; float bests = cur;
    double ratio = log((double)t1 / t0) / (double)steps;
    for (long st = 0; st < steps; st++) {
        float temp = (float)(t0 * exp(ratio * st));
        int slot = 1 + xs(rng) % 21;
        int old = W->w[slot];
        W->w[slot] = (old + 1 + xs(rng) % 25) % 26;
        decrypt_pt(W, pt);
        float f = score_pt(pt);
        if (f > cur || (float)(xs(rng) & 0xFFFFFF) / 0x1000000 < expf((f - cur) / temp)) {
            cur = f;
            if (f > bests) { bests = f; Wb = *W; }
        } else {
            W->w[slot] = old;
        }
    }
    *W = Wb;
    return bests;
}

int main(int argc, char **argv) {
    setvbuf(stdout, NULL, _IONBF, 0);
    const char *alpha = KTEXT;
    const char *quads_path = "kryptos/english_quads.tsv";
    int synthetic = 0, n_real_check = 0;
    long steps = 10000000;   /* per SA run */
    int restarts = 40, ils = 20;
    float t0 = 0.8f, t1 = 0.01f;
    uint32_t master_seed = 12345;
    int truth_w[22]; int have_truth = 0;

    for (int i = 1; i < argc; i++) {
        if (!strcmp(argv[i], "--alpha") && i+1 < argc) alpha = (argv[++i][0]=='a') ? ATEXT : KTEXT;
        else if (!strcmp(argv[i], "--quads") && i+1 < argc) quads_path = argv[++i];
        else if (!strcmp(argv[i], "--synthetic")) synthetic = 1;
        else if (!strcmp(argv[i], "--sanity")) n_real_check = 1;
        else if (!strcmp(argv[i], "--steps")) steps = atol(argv[++i]);
        else if (!strcmp(argv[i], "--restarts")) restarts = atoi(argv[++i]);
        else if (!strcmp(argv[i], "--ils")) ils = atoi(argv[++i]);
        else if (!strcmp(argv[i], "--seed")) master_seed = (uint32_t)atol(argv[++i]);
        else if (!strcmp(argv[i], "--t0")) t0 = (float)atof(argv[++i]);
        else if (!strcmp(argv[i], "--t1")) t1 = (float)atof(argv[++i]);
    }
    load_quads(quads_path);

    int l2k[26]; /* standard letter index -> cipher alphabet index */
    for (int i = 0; i < 26; i++) { k2s[i] = alpha[i] - 'A'; l2k[alpha[i]-'A'] = i; }

    const char *pt_source = (synthetic || n_real_check) ? SYNTH_PT : NULL;
    uint32_t g = master_seed;

    if (synthetic) { /* encrypt known plaintext with random wheels */
        Wheels W; W.w[0] = 0;
        for (int i = 1; i < 22; i++) W.w[i] = xs(&g) % 26;
        for (int i = 0; i < 22; i++) truth_w[i] = W.w[i];
        have_truth = 1;
        for (int i = 0; i < N; i++) {
            int k = (W.w[i%4] + W.w[4+i%5] + W.w[9+i%6] + W.w[15+i%7]) % 26;
            ct_idx[i] = (l2k[pt_source[i]-'A'] + k) % 26;
        }
    } else {
        for (int i = 0; i < N; i++) {
            const char *p = strchr(alpha, PK8[i]);
            if (!p) { fprintf(stderr, "cipher char not in alphabet: %c\n", PK8[i]); return 1; }
            ct_idx[i] = (int)(p - alpha);
        }
    }

    if (n_real_check) { /* wiring check: pins at truth must score at English level */
        Wheels W; memcpy(W.w, truth_w, sizeof truth_w);
        int pt[N]; decrypt_pt(&W, pt);
        printf("sanity: score at true wheels = %.4f (expect about -4.2)\nPT: ", score_pt(pt));
        for (int i = 0; i < N; i++) putchar('A' + pt[i]);
        putchar('\n');
        return 0;
    }

    float gbest = -1e9f; Wheels gW; int done = 0;
    double t_start = (double)time(NULL);

#ifdef _OPENMP
    #pragma omp parallel for schedule(dynamic) shared(gbest, gW, done)
#endif
    for (int r = 0; r < restarts; r++) {
        uint32_t rng = master_seed + 0x9e3779b9u * (r + 1);
        Wheels W; W.w[0] = 0;
        for (int i = 1; i < 22; i++) W.w[i] = xs(&rng) % 26;
        int pt[N];
        float bests = -1e9f;
        for (int c = 0; c < ils; c++) {
            float f = sa_run(&W, &rng, steps, t0, t1, pt);
            f = polish(&W, pt);
            if (f > bests) bests = f;
            else { /* ILS kick: randomize 3 coords, re-run a short anneal */
                for (int kx = 0; kx < 3; kx++) {
                    int slot = 1 + xs(&rng) % 21;
                    W.w[slot] = (W.w[slot] + 1 + xs(&rng) % 25) % 26;
                }
                f = sa_run(&W, &rng, steps / 4, 0.2f, 0.01f, pt);
                f = polish(&W, pt);
                if (f > bests) bests = f;
            }
        }
#ifdef _OPENMP
        #pragma omp critical
#endif
        {
            if (bests > gbest) {
                gbest = bests; gW = W;
                decrypt_pt(&gW, pt);
                printf("[best %.4f @restart %d | %.0fs] ", gbest, r, (double)time(NULL)-t_start);
                for (int i = 0; i < 60; i++) putchar('A' + pt[i]);
                putchar('\n');
            }
        }
        done++;
    }

    int pt[N]; decrypt_pt(&gW, pt);
    printf("\nFINAL best %.4f\nPT: ", gbest);
    for (int i = 0; i < N; i++) putchar('A' + pt[i]);
    putchar('\n');
    printf("wheels:");
    for (int i = 0; i < 22; i++) printf(" %d", gW.w[i]);
    putchar('\n');
    if (have_truth) {
        int acc = 0;
        for (int i = 0; i < N; i++) acc += (pt[i] == pt_source[i]-'A');
        printf("TRUTH: %s\naccuracy %.1f%% (%d/%d)\n", pt_source, 100.0*acc/N, acc, N);
        printf("RECOVERED: %s\n", acc*100 >= 99*N ? "YES" : "no");
    }
    return 0;
}
