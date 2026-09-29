#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>
#include <time.h>

#define N 504
#define W 42
#define H (N / W) // 12

static float bigram[26][26];

void load_bigrams() {
    FILE *f = fopen("english_bigrams.bin", "rb");
    if (!f) { printf("Cannot open english_bigrams.bin\n"); exit(1); }
    if (fread(bigram, sizeof(float), 26 * 26, f) != 26 * 26) {
        printf("Failed to read bigrams\n"); exit(1);
    }
    fclose(f);
}

const char *KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
const char *PK10_CT = "UBINFYJSFQXQVRLJJAJDGBXIWKDMAREZTGSHQWRXCHEPCLYSDNGYRRBTCVOZJYVLYWREJTCDOYVEYCJJVZKRMKTRPGVHRWMJSRCSHXZMJEVQKJYJJAYZKDFQBGRSWXATJMEXKFXAXKSIZXOERFESNVCGCNRHEOBCNCBUPXTJJRCIMDMRUVZWRDRRFXAPGPIGSPLILFIZSTDZYOVQGGDFUFZPUOJPJVWREUVRQIYPCEHGYUZUKWTFXELUNOKBANZFTFRMXZSXXQSBGPCWGXPFSCANSVUYLMTZIRCCCJJPBQAEPWVCDIMLOPOXQEGJKVQIVHEFAPQMVCYSQAFKCTYTPAOOJZCWIPGDPAFTINBFFHVXYEQXCEIDJJOUABBAHSWKHGMLJBXDSQEFBBDLTLJPLZPIPPTRGDRZIZPUPYJODOCSOYCZZWTKYWMBQTFMFEQZWVPQYLJTMEYKYBNOPEPUMHCFJSLFWOISWLKFFABTYFQDTEQBDELIEOZQ";

static const float eng_freq[26] = {
    0.08167, 0.01492, 0.02782, 0.04253, 0.12702, 0.02228, 0.02015,
    0.06094, 0.06966, 0.00153, 0.00772, 0.04025, 0.02406, 0.06749,
    0.07507, 0.01929, 0.00095, 0.05987, 0.06327, 0.09056, 0.02758,
    0.00978, 0.02360, 0.00150, 0.01974, 0.00074
};

static float log_eng[26];

static int c_idx[N];
static int alpha_to_std[26];

void init_tables() {
    for (int i = 0; i < 26; i++) {
        alpha_to_std[i] = KRYPTOS[i] - 'A';
        log_eng[i] = logf(eng_freq[i]);
    }
    for (int i = 0; i < N; i++) {
        c_idx[i] = strchr(KRYPTOS, PK10_CT[i]) - KRYPTOS;
    }
}

// Fixed Q7 from PK8/PK9:
static const int Q7_PK[7] = {0, 22, 3, 3, 15, 0, 1};

// Score function combining:
// 1. Unigram log-likelihood (weight 1.0)
// 2. Monogram IoC bonus (weight 5000.0)
// 3. Row-wise bigram transitions along W=42 grid (weight 0.5)
static inline float eval_state(const int *q8, const int *q9) {
    int counts[26] = {0};
    int Z[N];
    float unigram_ll = 0.0f;

    for (int i = 0; i < N; i++) {
        int k = (Q7_PK[i % 7] + q8[i % 8] + q9[i % 9]) % 26;
        int p = (c_idx[i] - k + 26) % 26;
        int std_char = alpha_to_std[p];
        Z[i] = std_char;
        counts[std_char]++;
        unigram_ll += log_eng[std_char];
    }

    // Monogram IoC
    int pairs = 0;
    for (int c = 0; c < 26; c++) pairs += counts[c] * (counts[c] - 1);
    float ioc = (float)pairs / (float)(N * (N - 1));

    // Bigram score along 12 rows of 42 chars
    float bg_score = 0.0f;
    for (int r = 0; r < H; r++) {
        int base = r * W;
        for (int c = 0; c < W - 1; c++) {
            bg_score += bigram[Z[base + c]][Z[base + c + 1]];
        }
    }

    return unigram_ll + (ioc * 5000.0f) + (bg_score * 0.5f);
}

int main(int argc, char **argv) {
    load_bigrams();
    init_tables();

    int restarts = (argc > 1) ? atoi(argv[1]) : 20000;

    printf("======================================================================\n");
    printf("Two-Clock Decoupled Search on PK10 (Q8, Q9) with Q7 Fixed\n");
    printf("Objective: Unigram LL + IoC Bonus + W42 Bigram Density\n");
    printf("Restarts: %d\n", restarts);
    printf("======================================================================\n\n");

    float global_best_sc = -999999.0f;
    int g_q8[8], g_q9[9];

    double t0 = omp_get_wtime();

    #pragma omp parallel
    {
        unsigned int seed = 42 + omp_get_thread_num() * 2027;
        float loc_best_sc = -999999.0f;
        int loc_q8[8], loc_q9[9];

        #pragma omp for schedule(dynamic, 50)
        for (int rep = 0; rep < restarts; rep++) {
            int q8[8], q9[9];
            for (int i = 0; i < 8; i++) q8[i] = rand_r(&seed) % 26;
            for (int i = 0; i < 9; i++) q9[i] = rand_r(&seed) % 26;

            float cur_sc = eval_state(q8, q9);

            // Coordinate descent passes
            int improved = 1;
            int passes = 0;
            while (improved && passes < 10) {
                improved = 0;
                passes++;

                for (int i = 0; i < 8; i++) {
                    int old_v = q8[i];
                    int best_v = old_v;
                    float best_s = cur_sc;
                    for (int diff = 1; diff < 26; diff++) {
                        q8[i] = (old_v + diff) % 26;
                        float s = eval_state(q8, q9);
                        if (s > best_s) { best_s = s; best_v = q8[i]; }
                    }
                    q8[i] = best_v;
                    if (best_v != old_v) { cur_sc = best_s; improved = 1; }
                }

                for (int i = 0; i < 9; i++) {
                    int old_v = q9[i];
                    int best_v = old_v;
                    float best_s = cur_sc;
                    for (int diff = 1; diff < 26; diff++) {
                        q9[i] = (old_v + diff) % 26;
                        float s = eval_state(q8, q9);
                        if (s > best_s) { best_s = s; best_v = q9[i]; }
                    }
                    q9[i] = best_v;
                    if (best_v != old_v) { cur_sc = best_s; improved = 1; }
                }
            }

            if (cur_sc > loc_best_sc) {
                loc_best_sc = cur_sc;
                memcpy(loc_q8, q8, 8 * sizeof(int));
                memcpy(loc_q9, q9, 9 * sizeof(int));
            }
        }

        #pragma omp critical
        {
            if (loc_best_sc > global_best_sc) {
                global_best_sc = loc_best_sc;
                memcpy(g_q8, loc_q8, 8 * sizeof(int));
                memcpy(g_q9, loc_q9, 9 * sizeof(int));
                printf("[Thread %d] BREAKTHROUGH: Total Composite Score = %.2f\n",
                       omp_get_thread_num(), global_best_sc);
            }
        }
    }

    double elapsed = omp_get_wtime() - t0;
    printf("\n%d restarts completed in %.3f s (%.1f restarts/sec)!\n\n",
           restarts, elapsed, (double)restarts / elapsed);

    printf("======================================================================\n");
    printf("FINAL OPTIMAL PK10 CLOCKS\n");
    printf("======================================================================\n");
    printf("Q8: [");
    for (int i = 0; i < 8; i++) printf("%d%s", g_q8[i], i==7?"":", ");
    printf("] (KR: ");
    for (int i = 0; i < 8; i++) printf("%c", KRYPTOS[g_q8[i]]);
    printf(")\n");
    printf("Q9: [");
    for (int i = 0; i < 9; i++) printf("%d%s", g_q9[i], i==8?"":", ");
    printf("] (KR: ");
    for (int i = 0; i < 9; i++) printf("%c", KRYPTOS[g_q9[i]]);
    printf(")\n\n");

    // Decrypt intermediate stream Z
    char Z[N + 1];
    int counts[26] = {0};
    for (int i = 0; i < N; i++) {
        int k = (Q7_PK[i % 7] + g_q8[i % 8] + g_q9[i % 9]) % 26;
        int p = (c_idx[i] - k + 26) % 26;
        int std_char = alpha_to_std[p];
        Z[i] = 'A' + std_char;
        counts[std_char]++;
    }
    Z[N] = '\0';

    int pairs = 0;
    for (int c = 0; c < 26; c++) pairs += counts[c] * (counts[c] - 1);
    float ioc = (float)pairs / (float)(N * (N - 1));

    printf("Decrypted Intermediate Stream Z (IoC = %.5f):\n%s\n\n", ioc, Z);
    printf("Letter counts in Z:\n");
    for (int c = 0; c < 26; c++) {
        printf("%c:%2d (%4.1f%%)  ", 'A' + c, counts[c], (float)counts[c] * 100.0f / N);
        if ((c + 1) % 6 == 0) printf("\n");
    }
    printf("\n\nPlaintext layout in 12 rows of 42 chars:\n");
    for (int r = 0; r < H; r++) {
        char buf[43];
        memcpy(buf, Z + r * W, W);
        buf[W] = '\0';
        printf("  Row %2d: %s\n", r, buf);
    }

    return 0;
}
