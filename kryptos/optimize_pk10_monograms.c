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

// Fixed binary parities for PK10
static const int q2_7[7] = {0, 1, 1, 1, 0, 0, 0};
static const int q2_8[8] = {0, 0, 0, 1, 0, 1, 0, 0};
static const int q2_9[9] = {0, 0, 1, 1, 1, 1, 0, 0, 0};

static inline int crt(int q2, int q13) {
    return (13 * q2 + 14 * q13) % 26;
}

static int c_idx[N];
static int alpha_to_std[26];

void init_tables() {
    for (int i = 0; i < 26; i++) {
        alpha_to_std[i] = KRYPTOS[i] - 'A';
    }
    for (int i = 0; i < N; i++) {
        c_idx[i] = strchr(KRYPTOS, PK10_CT[i]) - KRYPTOS;
    }
}

float compute_dot(const int *q7, const int *q8, const int *q9, int *counts_out) {
    int counts[26] = {0};
    for (int i = 0; i < N; i++) {
        int k = (q7[i % 7] + q8[i % 8] + q9[i % 9]) % 26;
        int p = (c_idx[i] - k + 26) % 26;
        counts[alpha_to_std[p]]++;
    }
    float dot = 0.0f;
    for (int c = 0; c < 26; c++) {
        dot += counts[c] * eng_freq[c];
        if (counts_out) counts_out[c] = counts[c];
    }
    return dot;
}

int main(int argc, char **argv) {
    init_tables();

    int num_restarts = 50000;
    if (argc > 1) num_restarts = atoi(argv[1]);

    printf("Starting OpenMP Monogram Optimization on PK10 (%d restarts)...\n", num_restarts);

    float global_best_dot = 0.0f;
    int best_q7[7], best_q8[8], best_q9[9];
    int best_counts[26];

    double t0 = omp_get_wtime();

    #pragma omp parallel
    {
        unsigned int seed = 42 + omp_get_thread_num() * 1337;
        float local_best_dot = 0.0f;
        int local_best_q7[7], local_best_q8[8], local_best_q9[9];
        int local_counts[26];

        #pragma omp for schedule(dynamic, 100)
        for (int r = 0; r < num_restarts; r++) {
            int q13_7[7], q13_8[8], q13_9[9];
            for (int i = 0; i < 7; i++) q13_7[i] = rand_r(&seed) % 13;
            for (int i = 0; i < 7; i++) q13_8[i] = rand_r(&seed) % 13; q13_8[7] = 0;
            for (int i = 0; i < 8; i++) q13_9[i] = rand_r(&seed) % 13; q13_9[8] = 0;

            int q7[7], q8[8], q9[9];
            for (int i = 0; i < 7; i++) q7[i] = crt(q2_7[i], q13_7[i]);
            for (int i = 0; i < 8; i++) q8[i] = crt(q2_8[i], q13_8[i]);
            for (int i = 0; i < 9; i++) q9[i] = crt(q2_9[i], q13_9[i]);

            float cur_dot = compute_dot(q7, q8, q9, NULL);

            int improved = 1;
            int passes = 0;
            while (improved && passes < 10) {
                improved = 0;
                passes++;

                // Clock 7
                for (int i = 0; i < 7; i++) {
                    int old_v = q13_7[i];
                    int best_v = old_v;
                    float best_d = cur_dot;
                    for (int v = 0; v < 13; v++) {
                        if (v == old_v) continue;
                        q7[i] = crt(q2_7[i], v);
                        float d = compute_dot(q7, q8, q9, NULL);
                        if (d > best_d) {
                            best_d = d;
                            best_v = v;
                        }
                    }
                    q13_7[i] = best_v;
                    q7[i] = crt(q2_7[i], best_v);
                    if (best_v != old_v) {
                        cur_dot = best_d;
                        improved = 1;
                    }
                }

                // Clock 8 (0..6)
                for (int i = 0; i < 7; i++) {
                    int old_v = q13_8[i];
                    int best_v = old_v;
                    float best_d = cur_dot;
                    for (int v = 0; v < 13; v++) {
                        if (v == old_v) continue;
                        q8[i] = crt(q2_8[i], v);
                        float d = compute_dot(q7, q8, q9, NULL);
                        if (d > best_d) {
                            best_d = d;
                            best_v = v;
                        }
                    }
                    q13_8[i] = best_v;
                    q8[i] = crt(q2_8[i], best_v);
                    if (best_v != old_v) {
                        cur_dot = best_d;
                        improved = 1;
                    }
                }

                // Clock 9 (0..7)
                for (int i = 0; i < 8; i++) {
                    int old_v = q13_9[i];
                    int best_v = old_v;
                    float best_d = cur_dot;
                    for (int v = 0; v < 13; v++) {
                        if (v == old_v) continue;
                        q9[i] = crt(q2_9[i], v);
                        float d = compute_dot(q7, q8, q9, NULL);
                        if (d > best_d) {
                            best_d = d;
                            best_v = v;
                        }
                    }
                    q13_9[i] = best_v;
                    q9[i] = crt(q2_9[i], best_v);
                    if (best_v != old_v) {
                        cur_dot = best_d;
                        improved = 1;
                    }
                }
            }

            if (cur_dot > local_best_dot) {
                local_best_dot = cur_dot;
                for (int i = 0; i < 7; i++) local_best_q7[i] = q7[i];
                for (int i = 0; i < 8; i++) local_best_q8[i] = q8[i];
                for (int i = 0; i < 9; i++) local_best_q9[i] = q9[i];
                compute_dot(q7, q8, q9, local_counts);
            }
        }

        #pragma omp critical
        {
            if (local_best_dot > global_best_dot) {
                global_best_dot = local_best_dot;
                for (int i = 0; i < 7; i++) best_q7[i] = local_best_q7[i];
                for (int i = 0; i < 8; i++) best_q8[i] = local_best_q8[i];
                for (int i = 0; i < 9; i++) best_q9[i] = local_best_q9[i];
                for (int c = 0; c < 26; c++) best_counts[c] = local_counts[c];

                printf("New Global Best Dot = %.4f\n", global_best_dot);
                printf("  q7: [");
                for (int i = 0; i < 7; i++) printf("%d%s", best_q7[i], i==6 ? "]\n" : ", ");
                printf("  q8: [");
                for (int i = 0; i < 8; i++) printf("%d%s", best_q8[i], i==7 ? "]\n" : ", ");
                printf("  q9: [");
                for (int i = 0; i < 9; i++) printf("%d%s", best_q9[i], i==8 ? "]\n" : ", ");
                fflush(stdout);
            }
        }
    }

    double elapsed = omp_get_wtime() - t0;
    printf("\nCompleted %d restarts in %.2f s (%.1f restarts/sec)\n",
           num_restarts, elapsed, num_restarts / elapsed);
    printf("Global Best Monogram Dot = %.4f (Expected English: ~33.0 for 504 chars, Random: ~23.5)\n",
           global_best_dot);

    printf("\nLetter Counts for Best Stream X:\n");
    for (int c = 0; c < 26; c++) {
        printf("%c: %2d (%.1f%%)  ", 'A' + c, best_counts[c], best_counts[c] * 100.0 / N);
        if ((c + 1) % 6 == 0) printf("\n");
    }
    printf("\n");

    // Output X string to file
    char X[N+1];
    for (int i = 0; i < N; i++) {
        int k = (best_q7[i % 7] + best_q8[i % 8] + best_q9[i % 9]) % 26;
        int p = (c_idx[i] - k + 26) % 26;
        X[i] = 'A' + alpha_to_std[p];
    }
    X[N] = '\0';
    FILE *fout = fopen("pk10_best_monogram_X.txt", "w");
    fprintf(fout, "%.4f\n%s\n", global_best_dot, X);
    fclose(fout);
    printf("Saved pk10_best_monogram_X.txt\n");

    return 0;
}
