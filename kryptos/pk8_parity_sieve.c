/* Parity sieve for PK8-shaped sum-clocks  {4,5,6,7}.
 *
 * The full-product annihilator  prod (1 - E^p)  has degree 22 with leading
 * coefficient +1, so the whole plaintext tail is an affine function of the
 * first 22 letters.  Work mod 2 (CRT factor of 26 = 2 * 13): the tail
 * *parities* are GF(2)-affine in the 22 seed parities, with constants from
 * the ciphertext.
 *
 * English parity is not random: vowels/consonant alternation makes the mod-2
 * stream of English strongly Markov, while wrong seeds give fair bits.  Score
 * each of the 2^22 seeds by a mod-2 fourth-order Markov chain trained on
 * English prose; the true seed should rank at or near the top.
 *
 * This is a measurement instrument: --synthetic prints the true seed's rank
 * (the decisive calibration), --real prints the top seeds for the real PK8.
 *
 * gcc -O3 -o pk8_parity_sieve pk8_parity_sieve.c -lm
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <stdint.h>

#define N 153
#define SEED_LEN 22
#define NTAPS 15

static const char *KTEXT = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
static const char *ATEXT = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";
static const char *PK8 = "COPVEJJVSVURTVIPYOTPLHGBTMAUCCPESIWIGZBWSJPKTRPUEKQFIFCLHMXTHIMHWOYIGURBOMPARCVXVKBDDVBVHDRHGCVNWWVLBMYWMWHICFIXZWBVZYCQGNOGJGUMLNPUTHQCXNWPQZOIRJZGSWVPY";

static const char *SYNTH_PT =
    "THERAILWAYSTATIONATASHFORDWASCROWDEDWITHTRAVELLERSWAITINGFORTHEDELAYEXPRESSANDTHESTATIONMASTERWALKEDUPANDDOWNTHEPLATFORMWITHHISHANDSBEHINDHISBACKMUTTERINGABOUTTHEWEATHERANDTH";

/* taps of (1-E^4)(1-E^5)(1-E^6)(1-E^7): offset -> coeff (mod 26), lead +1 at 22 */
static const int TAP_OFF[NTAPS] = {0, 4, 5, 6, 7, 9, 10, 11, 12, 13, 15, 16, 17, 18, 22};
static const int TAP_CO[NTAPS]  = {1, -1, -1, -1, -1, 1, 1, 2, 1, 1, -1, -1, -1, -1, 1};

static int ct_idx[N];

/* Markov chain: logc[ctx][bit] = log P(bit | previous ORDER-1 bits) */
static int ORDER = 3;      /* total chain order (1 + context bits) */
static double (*logc)[2];  /* [1 << (ORDER-1)][2] */

static void train_markov(const char *corpus_path) {
    int nctx = 1 << (ORDER - 1);
    logc = malloc(sizeof(double) * 2 * nctx);
    /* parity of standard letters via the kryptos ordering position is what
       matters; but parity classes come from the *cipher* alphabet.  We need
       the parity of each PLAINTEXT letter as seen through the alphabet,
       i.e. the index of that letter in the alphabet, mod 2.  Train on the
       corpus text converted to alphabet-index parities. */
    static long cnt[64][2];
    FILE *f = fopen(corpus_path, "r");
    if (!f) { fprintf(stderr, "cannot open corpus %s\n", corpus_path); exit(1); }
    int hist[5] = {0}; int nhist = 0;
    int ch;
    extern const char *g_alpha; extern const int *g_par;
    while ((ch = fgetc(f)) != EOF) {
        if (ch < 'A' || ch > 'Z') {
            if (ch >= 'a' && ch <= 'z') ch -= 32; else continue;
        }
        int bit = g_par[ch - 'A'];
        if (nhist >= ORDER - 1) {
            int ctx = 0;
            for (int k = 0; k < ORDER - 1; k++) ctx = (ctx << 1) | hist[k];
            cnt[ctx][bit]++;
        }
        memmove(hist, hist + 1, (ORDER - 2 > 0 ? ORDER - 2 : 1) * sizeof(int));
        hist[ORDER - 2] = bit;
        if (nhist < ORDER) nhist++;
    }
    fclose(f);
    for (int c = 0; c < nctx; c++) {
        double tot = cnt[c][0] + cnt[c][1] + 1.0;
        logc[c][0] = log((cnt[c][0] + 0.5) / tot);
        logc[c][1] = log((cnt[c][1] + 0.5) / tot);
    }
    /* report chain strength */
    double h = 0, n = 0;
    for (int c = 0; c < nctx; c++) for (int b = 0; b < 2; b++) {
        double w = cnt[c][b]; h += w * -logc[c][b]; n += w;
    }
    fprintf(stderr, "markov: conditional entropy of parity stream = %.3f bits\n",
            h / (n > 0 ? n : 1) / 0.6931471805599453);
}

const char *g_alpha;
int g_par_storage[26];
const int *g_par = g_par_storage;

/* LFSR machinery: tail[j] (positions 22..152) is affine in the 22 seed bits:
   tailbit[j] = popcount(mask[j] & seed) & 1  ^  cbit[j]                      */
static uint32_t mask[N - SEED_LEN];
static int cbit[N - SEED_LEN];


int main(int argc, char **argv) {
    const char *alpha = KTEXT;
    const char *corpus = "kryptos/theophilus_book3_english.txt";
    int synthetic = 0;
    uint32_t seed_fixed = 0; int have_seed = 0;
    for (int i = 1; i < argc; i++) {
        if (!strcmp(argv[i], "--alpha") && i+1 < argc) alpha = (argv[++i][0]=='a') ? ATEXT : KTEXT;
        else if (!strcmp(argv[i], "--corpus") && i+1 < argc) corpus = argv[++i];
        else if (!strcmp(argv[i], "--synthetic")) synthetic = 1;
        else if (!strcmp(argv[i], "--seed")) { seed_fixed = (uint32_t)strtoul(argv[++i], 0, 0); have_seed = 1; }
        else if (!strcmp(argv[i], "--order")) ORDER = atoi(argv[++i]);
    }
    if (ORDER < 2 || ORDER > 6) { fprintf(stderr, "bad order\n"); return 1; }
    g_alpha = alpha;
    for (int i = 0; i < 26; i++) g_par_storage[alpha[i] - 'A'] = i & 1;
    train_markov(corpus);

    /* build ciphertext indices; synthetic: encrypt with random wheels whose
       seed bits we record, so the true seed's rank can be measured */
    uint32_t rng = 20260930;
    int truth_seed = -1;
    if (synthetic) {
        int w[22]; w[0] = 0;
        uint32_t x = rng;
        for (int i = 1; i < 22; i++) { x ^= x << 13; x ^= x >> 17; x ^= x << 5; w[i] = x % 26; }
        int l2k[26]; for (int i = 0; i < 26; i++) l2k[alpha[i]-'A'] = i;
        for (int i = 0; i < N; i++) {
            int k = (w[i%4] + w[4+i%5] + w[9+i%6] + w[15+i%7]) % 26;
            ct_idx[i] = (l2k[SYNTH_PT[i]-'A'] + k) % 26;
        }
        truth_seed = 0;
        for (int i = 0; i < SEED_LEN; i++) truth_seed |= (g_par[SYNTH_PT[i]-'A'] << i);
        fprintf(stderr, "synthetic: true seed parity bits = %06x\n", truth_seed);
    } else {
        for (int i = 0; i < N; i++) {
            const char *p = strchr(alpha, PK8[i]);
            if (!p) { fprintf(stderr, "bad char %c\n", PK8[i]); return 1; }
            ct_idx[i] = (int)(p - alpha);
        }
    }

    /* Build the affine maps.  Everything mod 2: L(C)[t] parity known.
       Recurrence (from taps, lead +1 at 22):
         P[t+22] = L(C)[t] - sum_{k<last} co_k * P[t+off_k]   (mod 2)
       Track dependence of each position j on the 22 seed bits: basis for
       j<22 is unit vector e_j; for j>=22 combine.                            */
    uint32_t dep[N]; int cst[N];
    for (int j = 0; j < SEED_LEN; j++) { dep[j] = 1u << j; cst[j] = 0; }
    for (int t = 0; t < N - SEED_LEN; t++) {
        int j = t + SEED_LEN;
        /* L(C)[t] = sum_k co_k C[t+off_k]  (mod 26); parity of that */
        int rhs = 0;
        for (int k = 0; k < NTAPS; k++) rhs += ((TAP_CO[k] % 2) + 2) * (ct_idx[t + TAP_OFF[k]] & 1);
        int cbit_rhs = rhs & 1;
        uint32_t d = 0; int c = cbit_rhs;
        for (int k = 0; k < NTAPS - 1; k++) { /* all but the lead (22) */
            int ck = ((TAP_CO[k] % 2) + 2) % 2;
            if (!ck) continue;
            d ^= dep[t + TAP_OFF[k]];
            c ^= cst[t + TAP_OFF[k]];
        }
        dep[j] = d; cst[j] = c;  /* P[j] parity = popcnt(d & seed) ^ c */
    }
    int ntail = N - SEED_LEN;
    for (int t = 0; t < ntail; t++) { mask[t] = dep[t + SEED_LEN]; cbit[t] = cst[t + SEED_LEN]; }

    /* score all 2^22 seeds.  seed bit i = parity of plaintext letter i.     */
    enum { KEEP = 1000 };
    double keep_sc[KEEP]; uint32_t keep_sd[KEEP]; int nkeep = 0;
    for (int i = 0; i < KEEP; i++) keep_sc[i] = -1e300;
    uint32_t best_seed[3] = {0}; double best_sc[3] = {-1e300, -1e300, -1e300};
    double true_sc = have_seed ? 0.0 : 0; long better = 0; double sc_true = 0;
    for (uint32_t seed = have_seed ? seed_fixed : 0; seed < (1u << SEED_LEN); seed++) {
        /* score the first 22 bits directly, then the tail */
        register double sc = 0.0;
        int ctx = 0, filled = 0;
        for (int j = 0; j < N; j++) {
            int bit;
            if (j < SEED_LEN) bit = (seed >> j) & 1;
            else { uint32_t m = mask[j - SEED_LEN] & seed; bit = (__builtin_popcount(m) & 1) ^ cbit[j - SEED_LEN]; }
            if (filled >= ORDER - 1) sc += logc[ctx][bit];
            ctx = ((ctx << 1) | bit) & ((1 << (ORDER - 1)) - 1);
            filled++;
        }
        if (synthetic && (int)seed == truth_seed) sc_true = sc;
        if (synthetic && (int)seed != truth_seed && sc > sc_true) better++;
        if (sc > keep_sc[KEEP-1]) {   /* maintain top-KEEP list */
            int p = KEEP-1;
            while (p > 0 && keep_sc[p-1] < sc) { keep_sc[p] = keep_sc[p-1]; keep_sd[p] = keep_sd[p-1]; p--; }
            keep_sc[p] = sc; keep_sd[p] = seed; if (nkeep < KEEP) nkeep++;
        }
        if (sc > best_sc[0]) {
            best_sc[2] = best_sc[1]; best_seed[2] = best_seed[1];
            best_sc[1] = best_sc[0]; best_seed[1] = best_seed[0];
            best_sc[0] = sc; best_seed[0] = seed;
        } else if (sc > best_sc[1]) {
            best_sc[2] = best_sc[1]; best_seed[2] = best_seed[1];
            best_sc[1] = sc; best_seed[1] = seed;
        } else if (sc > best_sc[2]) {
            best_sc[2] = sc; best_seed[2] = seed;
        }
        if (have_seed) break;
    }
    printf("top seeds: %06x (%.2f)  %06x (%.2f)  %06x (%.2f)\n",
           best_seed[0], best_sc[0], best_seed[1], best_sc[1], best_seed[2], best_sc[2]);
    {   /* dump leaderboard */
        FILE *lf = fopen("kryptos/pk8_parity_top1000.tsv", "w");
        if (lf) {
            for (int i = 0; i < nkeep; i++) fprintf(lf, "%06x\t%.4f\n", keep_sd[i], keep_sc[i]);
            fclose(lf);
            fprintf(stderr, "wrote kryptos/pk8_parity_top1000.tsv (%d seeds)\n", nkeep);
        }
    }
    if (synthetic) {
        printf("true seed %06x score %.2f | wrong seeds scoring higher: %ld of %d\n",
               truth_seed, sc_true, better, (1 << SEED_LEN) - 1);
        printf("TRUE SEED RANK: %ld\n", better + 1);
    }
    return 0;
}
