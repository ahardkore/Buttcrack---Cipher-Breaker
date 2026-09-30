/* Calibrated joint SA attack on PK9-shaped ciphers.
 *
 * Model: plaintext --T1(18 wide, 8 tall)--> --T2(8 wide, 18 tall)--> Z,
 *        Z[t] + s[t mod 28] = C[t]   (additive, over the chosen alphabet)
 * State: p1 in S18, p2 in S8, s in Z26^28 (s[0] taken as gauge-free; no
 *        gauge fixed: a constant added to all shifts is absorbed into the
 *        plaintext and is preferred not to exist by the quadgram score).
 *
 * Calibration protocol (same discipline as pk8_sa_cal2.c):
 *   --synthetic: random (p1,p2,s) over a known English window; report the
 *   recovery rate at a given budget.  Only budgets that recover synthetics
 *   mean anything when applied to --real PK9.
 *
 * gcc -O3 -fopenmp -o pk9_sa_cal2 pk9_sa_cal2.c -lm
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

#define N 144
#define W1 18
#define H1 8
#define W2 8
#define H2 18
#define FLOOR (-9.5f)

static const char *KTEXT = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
static const char *ATEXT = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";
static const char *PK9 = "KSYAWFEYYOISZGEUFBLYATAIBYFAQBQYYVDWJKLJXMYIEPIFVHPQNHZGSUHUUDXLEHRHUMALHEGLHXSJMUXGNUIVBXGUJHZRZGUSVHMLSCTSUQXHSUMQQIFUQGKHJGUQGLHDKEWSKAMHIJXD";

static const char *SYNTH_PT =
    "THERAILWAYSTATIONATASHFORDWASCROWDEDWITHTRAVELLERSWAITINGFORTHEDELAYEXPRESSANDTHESTATIONMASTERWALKEDUPANDDOWNTHEPLATFORMWITHHISHANDSBEHINDHISBACKxx";

static float quad[26][26][26][26];
static int ct_idx[N];
static int k2s[26], l2k[26];

static void load_quads(const char *path) {
    for (int a = 0; a < 26; a++) for (int b = 0; b < 26; b++)
        for (int c = 0; c < 26; c++) for (int d = 0; d < 26; d++)
            quad[a][b][c][d] = FLOOR;
    FILE *f = fopen(path, "r");
    if (!f) { fprintf(stderr, "cannot open %s\n", path); exit(1); }
    char q[32]; float sc;
    while (fscanf(f, "%31s %f", q, &sc) == 2)
        if (strlen(q) == 4) {
            int a=q[0]-'A', b=q[1]-'A', c=q[2]-'A', d=q[3]-'A';
            if ((unsigned)a<26&&(unsigned)b<26&&(unsigned)c<26&&(unsigned)d<26)
                quad[a][b][c][d] = sc;
        }
    fclose(f);
}

static inline uint32_t xs(uint32_t *s){uint32_t x=*s;x^=x<<13;x^=x>>17;x^=x<<5;*s=x;return x;}

typedef struct { int p1[W1], p2[W2], s[28]; } State;

static int z_cache[N], mid_cache[N], pt_cache[N];

/* Z -> invert T2 -> mid -> invert T1 -> pt ; all in standard-letter indices */
static float eval_state(const State *S) {
    for (int t = 0; t < N; t++)
        z_cache[t] = k2s[(ct_idx[t] - S->s[t % 28] + 26) % 26];
    int idx = 0;
    for (int c = 0; c < W2; c++)
        for (int r = 0; r < H2; r++) mid_cache[r * W2 + S->p2[c]] = z_cache[idx++];
    idx = 0;
    for (int c = 0; c < W1; c++)
        for (int r = 0; r < H1; r++) pt_cache[r * W1 + S->p1[c]] = mid_cache[idx++];
    float s = 0.0f;
    for (int i = 0; i < N - 3; i++)
        s += quad[pt_cache[i]][pt_cache[i+1]][pt_cache[i+2]][pt_cache[i+3]];
    return s / (N - 3);
}

static void shuffle_perm(int *p, int w, uint32_t *rng) {
    for (int i = w - 1; i > 0; i--) {
        int j = xs(rng) % (i + 1);
        int t = p[i]; p[i] = p[j]; p[j] = t;
    }
}

static float sa_run(State *S, uint32_t *rng, long steps, float t0, float t1) {
    float cur = eval_state(S);
    State Sb = *S; float best = cur;
    double ratio = log((double)t1 / t0) / (double)steps;
    for (long st = 0; st < steps; st++) {
        float temp = (float)(t0 * exp(ratio * st));
        int mv = xs(rng) % 100;
        if (mv < 45) { /* swap two columns of p1 */
            int a = xs(rng) % W1, b = xs(rng) % W1;
            if (a == b) continue;
            int t = S->p1[a]; S->p1[a] = S->p1[b]; S->p1[b] = t;
            float f = eval_state(S);
            if (f > cur || (float)(xs(rng) & 0xFFFFFF) / 0x1000000 < expf((f - cur) / temp)) {
                cur = f; if (f > best) { best = f; Sb = *S; }
            } else { t = S->p1[a]; S->p1[a] = S->p1[b]; S->p1[b] = t; }
        } else if (mv < 60) { /* swap two columns of p2 */
            int a = xs(rng) % W2, b = xs(rng) % W2;
            if (a == b) continue;
            int t = S->p2[a]; S->p2[a] = S->p2[b]; S->p2[b] = t;
            float f = eval_state(S);
            if (f > cur || (float)(xs(rng) & 0xFFFFFF) / 0x1000000 < expf((f - cur) / temp)) {
                cur = f; if (f > best) { best = f; Sb = *S; }
            } else { t = S->p2[a]; S->p2[a] = S->p2[b]; S->p2[b] = t; }
        } else { /* shift moves: half fine (+-1), half uniform jumps */
            int c = xs(rng) % 28;
            int old = S->s[c];
            int delta = (xs(rng) & 1) ? (xs(rng) % 3) - 1 : xs(rng) % 26;
            if (!delta) continue;
            S->s[c] = (old + delta + 26) % 26;
            float f = eval_state(S);
            if (f > cur || (float)(xs(rng) & 0xFFFFFF) / 0x1000000 < expf((f - cur) / temp)) {
                cur = f; if (f > best) { best = f; Sb = *S; }
            } else S->s[c] = old;
        }
    }
    *S = Sb;
    return best;
}

/* greedy polish: all 26 values for each of 28 shifts; all swap-pairs of p2;
   then a few passes of random-pair swap descents on p1 */
static float polish(State *S, uint32_t *rng) {
    float best = eval_state(S);
    for (int c = 0; c < 28; c++) {
        int orig = S->s[c], bv = orig; float bf = best;
        for (int v = 0; v < 26; v++) {
            if (v == orig) continue;
            S->s[c] = v;
            float f = eval_state(S);
            if (f > bf) { bf = f; bv = v; }
        }
        S->s[c] = bv; if (bf > best + 1e-6f) best = bf;
    }
    for (int a = 0; a < W2; a++) for (int b = a + 1; b < W2; b++) {
        int t = S->p2[a]; S->p2[a] = S->p2[b]; S->p2[b] = t;
        float f = eval_state(S);
        if (f > best) { best = f; } else { t = S->p2[a]; S->p2[a] = S->p2[b]; S->p2[b] = t; }
    }
    for (int round = 0; round < 12; round++) {
        int improved = 0;
        for (int a = 0; a < W1; a++) for (int b = a + 1; b < W1; b++) {
            int t = S->p1[a]; S->p1[a] = S->p1[b]; S->p1[b] = t;
            float f = eval_state(S);
            if (f > best + 1e-6f) { best = f; improved = 1; }
            else { t = S->p1[a]; S->p1[a] = S->p1[b]; S->p1[b] = t; }
        }
        if (!improved) break;
    }
    (void)rng;
    return best;
}

int main(int argc, char **argv) {
    setvbuf(stdout, NULL, _IONBF, 0);
    const char *alpha = KTEXT;
    const char *quads_path = "kryptos/english_quads.tsv";
    int synthetic = 0;
    long steps = 2000000;
    int restarts = 40, ils = 10;
    float t0 = 1.5f, t1 = 0.01f;
    uint32_t master_seed = 99;

    for (int i = 1; i < argc; i++) {
        if (!strcmp(argv[i], "--alpha") && i+1 < argc) alpha = (argv[++i][0]=='a') ? ATEXT : KTEXT;
        else if (!strcmp(argv[i], "--quads") && i+1 < argc) quads_path = argv[++i];
        else if (!strcmp(argv[i], "--synthetic")) synthetic = 1;
        else if (!strcmp(argv[i], "--steps")) steps = atol(argv[++i]);
        else if (!strcmp(argv[i], "--restarts")) restarts = atoi(argv[++i]);
        else if (!strcmp(argv[i], "--ils")) ils = atoi(argv[++i]);
        else if (!strcmp(argv[i], "--seed")) master_seed = (uint32_t)atol(argv[++i]);
        else if (!strcmp(argv[i], "--t0")) t0 = (float)atof(argv[++i]);
        else if (!strcmp(argv[i], "--t1")) t1 = (float)atof(argv[++i]);
    }
    load_quads(quads_path);
    for (int i = 0; i < 26; i++) { k2s[i] = alpha[i] - 'A'; l2k[alpha[i]-'A'] = i; }

    State truth; int have_truth = 0;
    uint32_t g = master_seed;
    if (synthetic) {
        for (int i = 0; i < W1; i++) truth.p1[i] = i; shuffle_perm(truth.p1, W1, &g);
        for (int i = 0; i < W2; i++) truth.p2[i] = i; shuffle_perm(truth.p2, W2, &g);
        for (int i = 0; i < 28; i++) truth.s[i] = xs(&g) % 26;
        have_truth = 1;
        /* encrypt: text -> T1 -> T2 -> Z -> +s  (inverse of eval_state) */
        int pt[N], mid[N], z[N];
        for (int i = 0; i < N; i++) pt[i] = SYNTH_PT[i] - 'A';
        int idx = 0;
        for (int c = 0; c < W1; c++)
            for (int r = 0; r < H1; r++) mid[idx++] = pt[r * W1 + truth.p1[c]];
        idx = 0;
        for (int c = 0; c < W2; c++)
            for (int r = 0; r < H2; r++) z[idx++] = mid[r * W2 + truth.p2[c]];
        for (int t = 0; t < N; t++)
            ct_idx[t] = (l2k[z[t]] + truth.s[t % 28]) % 26;
    } else {
        for (int i = 0; i < N; i++) {
            const char *p = strchr(alpha, PK9[i]);
            if (!p) { fprintf(stderr, "bad cipher char\n"); return 1; }
            ct_idx[i] = (int)(p - alpha);
        }
    }

    float gbest = -1e9f; State gS;
    double t_start = (double)time(NULL);
    int done = 0;

#ifdef _OPENMP
    #pragma omp parallel for schedule(dynamic) shared(gbest, gS)
#endif
    for (int r = 0; r < restarts; r++) {
        uint32_t rng = master_seed + 0x85ebca6bu * (r + 1);
        State S;
        for (int i = 0; i < W1; i++) S.p1[i] = i; shuffle_perm(S.p1, W1, &rng);
        for (int i = 0; i < W2; i++) S.p2[i] = i; shuffle_perm(S.p2, W2, &rng);
        for (int i = 0; i < 28; i++) S.s[i] = xs(&rng) % 26;
        float bests = -1e9f;
        for (int c = 0; c < ils; c++) {
            float f = sa_run(&S, &rng, steps, t0, t1);
            f = polish(&S, &rng);
            if (f > bests) bests = f;
            else {
                for (int k = 0; k < 4; k++) {
                    int pos = rng % 28; (void)pos;
                    int a = xs(&rng) % W1, b = xs(&rng) % W1;
                    int t = S.p1[a]; S.p1[a] = S.p1[b]; S.p1[b] = t;
                }
                f = sa_run(&S, &rng, steps / 4, 0.4f, 0.01f);
                f = polish(&S, &rng);
                if (f > bests) bests = f;
            }
        }
#ifdef _OPENMP
        #pragma omp critical
#endif
        {
            static int printed = 0;
            if (bests > gbest) {
                gbest = bests; gS = S;
                eval_state(&gS);
                printf("[best %.4f @restart %d | %.0fs] ", gbest, r, (double)time(NULL) - t_start);
                for (int i = 0; i < 60; i++) putchar('A' + pt_cache[i]);
                putchar('\n');
                if (++printed >= 200) exit(0);
            }
        }
        done++;
    }

    eval_state(&gS);
    printf("\nFINAL best %.4f\nPT: ", gbest);
    for (int i = 0; i < N; i++) putchar('A' + pt_cache[i]);
    putchar('\n');
    printf("p1:"); for (int i = 0; i < W1; i++) printf(" %d", gS.p1[i]);
    printf("\np2:"); for (int i = 0; i < W2; i++) printf(" %d", gS.p2[i]);
    printf("\ns :"); for (int i = 0; i < 28; i++) printf(" %d", gS.s[i]);
    putchar('\n');
    if (have_truth) {
        int acc = 0;
        for (int i = 0; i < N; i++) acc += (pt_cache[i] == SYNTH_PT[i] - 'A');
        printf("accuracy %.1f%%  RECOVERED: %s\n", 100.0*acc/N,
               acc * 100 >= 99 * N ? "YES" : "no");
    }
    return 0;
}
