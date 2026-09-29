#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>
#include <time.h>

#define N 144
#define P 28

const char *KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
const char *STD = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";
const char *PK9_CT = "KSYAWFEYYOISZGEUFBLYATAIBYFAQBQYYVDWJKLJXMYIEPIFVHPQNHZGSUHUUDXLEHRHUMALHEGLHXSJMUXGNUIVBXGUJHZRZGUSVHMLSCTSUQXHSUMQQIFUQGKHJGUQGLHDKEWSKAMHIJXD";

static const float eng_freq[26] = {
    0.08167f, 0.01492f, 0.02782f, 0.04253f, 0.12702f, 0.02228f, 0.02015f,
    0.06094f, 0.06966f, 0.00153f, 0.00772f, 0.04025f, 0.02406f, 0.06749f,
    0.07507f, 0.01929f, 0.00095f, 0.05987f, 0.06327f, 0.09056f, 0.02758f,
    0.00978f, 0.02360f, 0.00150f, 0.01974f, 0.00074f
};

static float log_freq[26];
static int c_idx_kr[N];
static int c_idx_std[N];

// Precomputed lookup table: ll_table[alphabet][mode][j][shift]
// alphabet: 0=Kryptos, 1=Standard
// mode: 0=Vigenere (C - K), 1=Beaufort (K - C)
static float ll_table[2][2][28][26];

void init_tables() {
    for (int i = 0; i < 26; i++) {
        log_freq[i] = logf(eng_freq[i]);
    }
    for (int i = 0; i < N; i++) {
        c_idx_kr[i] = strchr(KRYPTOS, PK9_CT[i]) - KRYPTOS;
        c_idx_std[i] = PK9_CT[i] - 'A';
    }

    // Build lookup tables
    for (int alpha = 0; alpha < 2; alpha++) {
        const char *alph = (alpha == 0) ? KRYPTOS : STD;
        const int *c_idx = (alpha == 0) ? c_idx_kr : c_idx_std;

        for (int mode = 0; mode < 2; mode++) {
            for (int j = 0; j < 28; j++) {
                for (int s = 0; s < 26; s++) {
                    float sum_ll = 0.0f;
                    for (int i = j; i < N; i += 28) {
                        int c = c_idx[i];
                        int p;
                        if (mode == 0) p = (c - s + 26) % 26; // C - K
                        else p = (s - c + 26) % 26; // K - C
                        int std_char = alph[p] - 'A';
                        sum_ll += log_freq[std_char];
                    }
                    ll_table[alpha][mode][j][s] = sum_ll;
                }
            }
        }
    }
}

// Load words
typedef struct {
    char word[8];
    int kr[7];
    int std[7];
} WordInfo;

static WordInfo *w4 = NULL;
static int num_w4 = 0;
static WordInfo *w7 = NULL;
static int num_w7 = 0;

void load_words() {
    FILE *f4 = fopen("words_4.txt", "r");
    if (!f4) { printf("Cannot open words_4.txt\n"); exit(1); }
    char buf[64];
    w4 = malloc(10000 * sizeof(WordInfo));
    while (fgets(buf, sizeof(buf), f4)) {
        buf[strcspn(buf, "\r\n")] = '\0';
        if (strlen(buf) == 4) {
            strncpy(w4[num_w4].word, buf, 5);
            for (int i = 0; i < 4; i++) {
                w4[num_w4].std[i] = buf[i] - 'A';
                w4[num_w4].kr[i] = strchr(KRYPTOS, buf[i]) - KRYPTOS;
            }
            num_w4++;
        }
    }
    fclose(f4);

    FILE *f7 = fopen("words_7.txt", "r");
    if (!f7) { printf("Cannot open words_7.txt\n"); exit(1); }
    w7 = malloc(50000 * sizeof(WordInfo));
    while (fgets(buf, sizeof(buf), f7)) {
        buf[strcspn(buf, "\r\n")] = '\0';
        if (strlen(buf) == 7) {
            strncpy(w7[num_w7].word, buf, 8);
            for (int i = 0; i < 7; i++) {
                w7[num_w7].std[i] = buf[i] - 'A';
                w7[num_w7].kr[i] = strchr(KRYPTOS, buf[i]) - KRYPTOS;
            }
            num_w7++;
        }
    }
    fclose(f7);

    printf("Loaded %d 4-letter words and %d 7-letter words (%ld pairs).\n",
           num_w4, num_w7, (long)num_w4 * num_w7);
}

void sweep_model(int alpha, int mode, const char *alpha_name, const char *mode_name) {
    printf("\n=== Sweeping %s Alphabet | Mode: %s ===\n", alpha_name, mode_name);

    float global_best_ll = -9999.0f;
    char best_w4[8], best_w7[8];

    double t0 = omp_get_wtime();

    #pragma omp parallel
    {
        float loc_best = -9999.0f;
        char loc_w4[8], loc_w7[8];

        #pragma omp for schedule(dynamic, 64)
        for (int i4 = 0; i4 < num_w4; i4++) {
            const int *k4 = (alpha == 0) ? w4[i4].kr : w4[i4].std;

            for (int i7 = 0; i7 < num_w7; i7++) {
                const int *k7 = (alpha == 0) ? w7[i7].kr : w7[i7].std;

                float ll = 0.0f;
                #pragma GCC unroll 28
                for (int j = 0; j < 28; j++) {
                    int s = (k4[j % 4] + k7[j % 7]) % 26;
                    ll += ll_table[alpha][mode][j][s];
                }

                if (ll > loc_best) {
                    loc_best = ll;
                    strcpy(loc_w4, w4[i4].word);
                    strcpy(loc_w7, w7[i7].word);
                }
            }
        }

        #pragma omp critical
        {
            if (loc_best > global_best_ll) {
                global_best_ll = loc_best;
                strcpy(best_w4, loc_w4);
                strcpy(best_w7, loc_w7);
            }
        }
    }

    double elapsed = omp_get_wtime() - t0;
    float per_char = global_best_ll / N;

    // Compute monogram IoC and letter distribution for best pair
    int counts[26] = {0};
    const char *alph = (alpha == 0) ? KRYPTOS : STD;
    const int *c_idx = (alpha == 0) ? c_idx_kr : c_idx_std;
    int k4_best[4], k7_best[7];
    for (int i = 0; i < 4; i++) k4_best[i] = (alpha == 0) ? (strchr(KRYPTOS, best_w4[i]) - KRYPTOS) : (best_w4[i] - 'A');
    for (int i = 0; i < 7; i++) k7_best[i] = (alpha == 0) ? (strchr(KRYPTOS, best_w7[i]) - KRYPTOS) : (best_w7[i] - 'A');

    char z_text[N + 1];
    for (int i = 0; i < N; i++) {
        int s = (k4_best[i % 4] + k7_best[i % 7]) % 26;
        int p = (mode == 0) ? ((c_idx[i] - s + 26) % 26) : ((s - c_idx[i] + 26) % 26);
        char ch = alph[p];
        z_text[i] = ch;
        counts[ch - 'A']++;
    }
    z_text[N] = '\0';

    int sp = 0;
    for (int c = 0; c < 26; c++) sp += counts[c] * (counts[c] - 1);
    float ioc = (float)sp / (N * (N - 1));

    int rare = counts['J'-'A'] + counts['Q'-'A'] + counts['X'-'A'] + counts['Z'-'A'];

    printf("Done in %.3f s (%.1f M pairs/sec)\n", elapsed, (double)num_w4 * num_w7 / elapsed / 1e6);
    printf("Best Pair: W4='%s', W7='%s'\n", best_w4, best_w7);
    printf("Unigram LL: %.2f (%.4f / char, English baseline: -2.45)\n", global_best_ll, per_char);
    printf("Monogram IoC: %.5f (English baseline: ~0.0667)\n", ioc);
    printf("E count: %d (%.1f%%), Rare (J,Q,X,Z): %d (%.1f%%)\n",
           counts['E'-'A'], (float)counts['E'-'A']/N*100.0f, rare, (float)rare/N*100.0f);
    printf("Z excerpt: %.40s...\n", z_text);
}

int main() {
    init_tables();
    load_words();

    // Sweep all 4 models:
    sweep_model(0, 0, "Kryptos", "Vigenere (C - K)");
    sweep_model(0, 1, "Kryptos", "Beaufort (K - C)");
    sweep_model(1, 0, "Standard", "Vigenere (C - K)");
    sweep_model(1, 1, "Standard", "Beaufort (K - C)");

    return 0;
}
