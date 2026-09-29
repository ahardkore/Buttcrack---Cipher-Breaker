#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>
#include <time.h>

#define N 504

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

// Fixed Q7 from PK9 breakthrough:
static const int Q7_PK9[7] = {0, 22, 3, 3, 15, 0, 1};

float eval_clocks_ll(const int *q7, const int *q8, const int *q9) {
    float ll = 0.0f;
    for (int i = 0; i < N; i++) {
        int k = (q7[i % 7] + q8[i % 8] + q9[i % 9]) % 26;
        int p = (c_idx[i] - k + 26) % 26;
        ll += log_eng[alpha_to_std[p]];
    }
    return ll;
}

int main(int argc, char **argv) {
    init_tables();

    int restarts = (argc > 1) ? atoi(argv[1]) : 50000;

    printf("======================================================================\n");
    printf("Optimizing PK10 (Q8, Q9) with Q7 Fixed from PK9 Breakthrough\n");
    printf("Q7: [0, 22, 3, 3, 15, 0, 1] | Restarts: %d\n", restarts);
    printf("======================================================================\n\n");

    float global_best_ll = -999999.0f;
    int best_q8[8], best_q9[9];

    double t0 = omp_get_wtime();

    #pragma omp parallel
    {
        unsigned int seed = 777 + omp_get_thread_num() * 3137;
        float loc_best_ll = -999999.0f;
        int loc_q8[8], loc_q9[9];

        #pragma omp for schedule(dynamic, 100)
        for (int rep = 0; rep < restarts; rep++) {
            int q8[8], q9[9];
            for (int i = 0; i < 8; i++) q8[i] = rand_r(&seed) % 26;
            for (int i = 0; i < 9; i++) q9[i] = rand_r(&seed) % 26;

            float cur_ll = eval_clocks_ll(Q7_PK9, q8, q9);

            // Coordinate descent
            int improved = 1;
            int passes = 0;
            while (improved && passes < 12) {
                improved = 0;
                passes++;

                for (int i = 0; i < 8; i++) {
                    int old_v = q8[i];
                    int best_v = old_v;
                    float best_l = cur_ll;
                    for (int diff = 1; diff < 26; diff++) {
                        q8[i] = (old_v + diff) % 26;
                        float l = eval_clocks_ll(Q7_PK9, q8, q9);
                        if (l > best_l) { best_l = l; best_v = q8[i]; }
                    }
                    q8[i] = best_v;
                    if (best_v != old_v) { cur_ll = best_l; improved = 1; }
                }

                for (int i = 0; i < 9; i++) {
                    int old_v = q9[i];
                    int best_v = old_v;
                    float best_l = cur_ll;
                    for (int diff = 1; diff < 26; diff++) {
                        q9[i] = (old_v + diff) % 26;
                        float l = eval_clocks_ll(Q7_PK9, q8, q9);
                        if (l > best_l) { best_l = l; best_v = q9[i]; }
                    }
                    q9[i] = best_v;
                    if (best_v != old_v) { cur_ll = best_l; improved = 1; }
                }
            }

            if (cur_ll > loc_best_ll) {
                loc_best_ll = cur_ll;
                memcpy(loc_q8, q8, 8 * sizeof(int));
                memcpy(loc_q9, q9, 9 * sizeof(int));
            }
        }

        #pragma omp critical
        {
            if (loc_best_ll > global_best_ll) {
                global_best_ll = loc_best_ll;
                memcpy(best_q8, loc_q8, 8 * sizeof(int));
                memcpy(best_q9, loc_q9, 9 * sizeof(int));
                printf("[Thread %d] New Best LL = %.2f\n", omp_get_thread_num(), global_best_ll);
            }
        }
    }

    double elapsed = omp_get_wtime() - t0;
    printf("\n%d restarts completed in %.3f s (%.1f restarts/sec)!\n",
           restarts, elapsed, (double)restarts / elapsed);

    printf("======================================================================\n");
    printf("FINAL OPTIMAL PK10 CLOCKS\n");
    printf("======================================================================\n");
    printf("Best Log-Likelihood: %.2f (Avg per char: %.4f)\n",
           global_best_ll, global_best_ll / N);
    printf("Q8: [");
    for (int i = 0; i < 8; i++) printf("%d%s", best_q8[i], i==7?"":", ");
    printf("] (KR: ");
    for (int i = 0; i < 8; i++) printf("%c", KRYPTOS[best_q8[i]]);
    printf(")\n");
    printf("Q9: [");
    for (int i = 0; i < 9; i++) printf("%d%s", best_q9[i], i==8?"":", ");
    printf("] (KR: ");
    for (int i = 0; i < 9; i++) printf("%c", KRYPTOS[best_q9[i]]);
    printf(")\n\n");

    // Decrypt intermediate stream Z
    char Z[N + 1];
    int counts[26] = {0};
    for (int i = 0; i < N; i++) {
        int k = (Q7_PK9[i % 7] + best_q8[i % 8] + best_q9[i % 9]) % 26;
        int p = (c_idx[i] - k + 26) % 26;
        int ch_std = alpha_to_std[p];
        Z[i] = 'A' + ch_std;
        counts[ch_std]++;
    }
    Z[N] = '\0';

    float ioc = 0.0f;
    for (int c = 0; c < 26; c++) ioc += counts[c] * (counts[c] - 1);
    ioc /= (float)(N * (N - 1));

    printf("Decrypted Intermediate Stream Z (IoC = %.5f):\n%s\n\n", ioc, Z);
    printf("Letter counts in Z:\n");
    for (int c = 0; c < 26; c++) {
        printf("%c:%2d (%4.1f%%)  ", 'A' + c, counts[c], (float)counts[c] * 100.0f / N);
        if ((c + 1) % 6 == 0) printf("\n");
    }
    printf("\n");

    return 0;
}
