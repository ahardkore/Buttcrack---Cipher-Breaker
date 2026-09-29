#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>
#include <time.h>

#define N 504

const char *KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
const char *PK10_CT = "UBINFYJSFQXQVRLJJAJDGBXIWKDMAREZTGSHQWRXCHEPCLYSDNGYRRBTCVOZJYVLYWREJTCDOYVEYCJJVZKRMKTRPGVHRWMJSRCSHXZMJEVQKJYJJAYZKDFQBGRSWXATJMEXKFXAXKSIZXOERFESNVCGCNRHEOBCNCBUPXTJJRCIMDMRUVZWRDRRFXAPGPIGSPLILFIZSTDZYOVQGGDFUFZPUOJPJVWREUVRQIYPCEHGYUZUKWTFXELUNOKBANZFTFRMXZSXXQSBGPCWGXPFSCANSVUYLMTZIRCCCJJPBQAEPWVCDIMLOPOXQEGJKVQIVHEFAPQMVCYSQAFKCTYTPAOOJZCWIPGDPAFTINBFFHVXYEQXCEIDJJOUABBAHSWKHGMLJBXDSQEFBBDLTLJPLZPIPPTRGDRZIZPUPYJODOCSOYCZZWTKYWMBQTFMFEQZWVPQYLJTMEYKYBNOPEPUMHCFJSLFWOISWLKFFABTYFQDTEQBDELIEOZQ";

// Precomputed binary parities
static const int q2_7[7] = {0, 1, 1, 1, 0, 0, 0};
static const int q2_8[8] = {0, 0, 0, 1, 0, 1, 0, 0};
static const int q2_9[9] = {0, 0, 1, 1, 1, 1, 0, 0, 0};

static inline int crt(int q2, int q13) {
    return (13 * q2 + 14 * q13) % 26;
}

static int c_idx[N];
static int alpha_to_std[26];
static float quad_table[26][26][26][26];
static float floor_score = -10.0f;

void init_tables() {
    for (int i = 0; i < 26; i++) {
        alpha_to_std[i] = KRYPTOS[i] - 'A';
    }
    for (int i = 0; i < N; i++) {
        c_idx[i] = strchr(KRYPTOS, PK10_CT[i]) - KRYPTOS;
    }

    // Initialize quadgram table
    for (int a = 0; a < 26; a++)
        for (int b = 0; b < 26; b++)
            for (int c = 0; c < 26; c++)
                for (int d = 0; d < 26; d++)
                    quad_table[a][b][c][d] = floor_score;

    FILE *f = fopen("english_quads.tsv", "r");
    if (!f) {
        printf("Error: english_quads.tsv not found!\n");
        exit(1);
    }
    char q[8];
    float val;
    int count = 0;
    while (fscanf(f, "%s %f", q, &val) == 2) {
        if (strlen(q) == 4) {
            int a = q[0] - 'A';
            int b = q[1] - 'A';
            int c = q[2] - 'A';
            int d = q[3] - 'A';
            if (a >= 0 && a < 26 && b >= 0 && b < 26 && c >= 0 && c < 26 && d >= 0 && d < 26) {
                quad_table[a][b][c][d] = val;
                count++;
            }
        }
    }
    fclose(f);
    printf("Loaded %d quadgrams into lookup array.\n", count);
}

static inline float score_plain(const int *p) {
    float s = 0.0f;
    for (int i = 0; i < N - 3; i++) {
        s += quad_table[p[i]][p[i+1]][p[i+2]][p[i+3]];
    }
    return s / (N - 3);
}

int main(int argc, char **argv) {
    init_tables();

    int total_restarts = 100000;
    if (argc > 1) total_restarts = atoi(argv[1]);

    printf("Starting Ultra-Fast Simulated Annealing on PK10 (3-Clock Q7+Q8+Q9)...\n");
    printf("Evaluating %d restarts across %d OpenMP threads...\n", total_restarts, omp_get_max_threads());

    float global_best_score = -10.0f;
    int best_q7[7], best_q8[8], best_q9[9];

    double t0 = omp_get_wtime();

    #pragma omp parallel
    {
        unsigned int seed = 12345 + omp_get_thread_num() * 777;
        float local_best_score = -10.0f;
        int local_best_q7[7], local_best_q8[8], local_best_q9[9];

        int p[N];

        #pragma omp for schedule(dynamic, 50)
        for (int r = 0; r < total_restarts; r++) {
            int q13_7[7], q13_8[8], q13_9[9];
            for (int i = 0; i < 7; i++) q13_7[i] = rand_r(&seed) % 13;
            for (int i = 0; i < 7; i++) q13_8[i] = rand_r(&seed) % 13; q13_8[7] = 0;
            for (int i = 0; i < 8; i++) q13_9[i] = rand_r(&seed) % 13; q13_9[8] = 0;

            int q7[7], q8[8], q9[9];
            for (int i = 0; i < 7; i++) q7[i] = crt(q2_7[i], q13_7[i]);
            for (int i = 0; i < 8; i++) q8[i] = crt(q2_8[i], q13_8[i]);
            for (int i = 0; i < 9; i++) q9[i] = crt(q2_9[i], q13_9[i]);

            for (int i = 0; i < N; i++) {
                int k = (q7[i % 7] + q8[i % 8] + q9[i % 9]) % 26;
                p[i] = alpha_to_std[(c_idx[i] - k + 26) % 26];
            }

            float cur_score = score_plain(p);

            float temp = 0.5f;
            float cool = 0.95f;
            int steps = 150;

            for (int step = 0; step < steps; step++) {
                // Pick random clock and random position
                int clk = rand_r(&seed) % 3;
                int pos, old_v, new_v;

                if (clk == 0) {
                    pos = rand_r(&seed) % 7;
                    old_v = q13_7[pos];
                    new_v = rand_r(&seed) % 13;
                    if (new_v == old_v) continue;
                    q13_7[pos] = new_v;
                    q7[pos] = crt(q2_7[pos], new_v);
                } else if (clk == 1) {
                    pos = rand_r(&seed) % 7;
                    old_v = q13_8[pos];
                    new_v = rand_r(&seed) % 13;
                    if (new_v == old_v) continue;
                    q13_8[pos] = new_v;
                    q8[pos] = crt(q2_8[pos], new_v);
                } else {
                    pos = rand_r(&seed) % 8;
                    old_v = q13_9[pos];
                    new_v = rand_r(&seed) % 13;
                    if (new_v == old_v) continue;
                    q13_9[pos] = new_v;
                    q9[pos] = crt(q2_9[pos], new_v);
                }

                // Recompute plain
                for (int i = 0; i < N; i++) {
                    int k = (q7[i % 7] + q8[i % 8] + q9[i % 9]) % 26;
                    p[i] = alpha_to_std[(c_idx[i] - k + 26) % 26];
                }

                float new_score = score_plain(p);
                float delta = new_score - cur_score;

                if (delta > 0 || (temp > 0.001f && expf(delta / temp) > ((float)rand_r(&seed) / RAND_MAX))) {
                    cur_score = new_score;
                } else {
                    // Revert
                    if (clk == 0) {
                        q13_7[pos] = old_v;
                        q7[pos] = crt(q2_7[pos], old_v);
                    } else if (clk == 1) {
                        q13_8[pos] = old_v;
                        q8[pos] = crt(q2_8[pos], old_v);
                    } else {
                        q13_9[pos] = old_v;
                        q9[pos] = crt(q2_9[pos], old_v);
                    }
                }
                temp *= cool;
            }

            // Final greedy ascent
            int improved = 1;
            int g_passes = 0;
            while (improved && g_passes < 5) {
                improved = 0;
                g_passes++;

                for (int i = 0; i < 7; i++) {
                    int old_v = q13_7[i];
                    int best_v = old_v;
                    float best_s = cur_score;
                    for (int v = 0; v < 13; v++) {
                        if (v == old_v) continue;
                        q7[i] = crt(q2_7[i], v);
                        for (int idx = 0; idx < N; idx++) {
                            int k = (q7[idx % 7] + q8[idx % 8] + q9[idx % 9]) % 26;
                            p[idx] = alpha_to_std[(c_idx[idx] - k + 26) % 26];
                        }
                        float s = score_plain(p);
                        if (s > best_s) { best_s = s; best_v = v; }
                    }
                    q13_7[i] = best_v;
                    q7[i] = crt(q2_7[i], best_v);
                    if (best_v != old_v) { cur_score = best_s; improved = 1; }
                }

                for (int i = 0; i < 7; i++) {
                    int old_v = q13_8[i];
                    int best_v = old_v;
                    float best_s = cur_score;
                    for (int v = 0; v < 13; v++) {
                        if (v == old_v) continue;
                        q8[i] = crt(q2_8[i], v);
                        for (int idx = 0; idx < N; idx++) {
                            int k = (q7[idx % 7] + q8[idx % 8] + q9[idx % 9]) % 26;
                            p[idx] = alpha_to_std[(c_idx[idx] - k + 26) % 26];
                        }
                        float s = score_plain(p);
                        if (s > best_s) { best_s = s; best_v = v; }
                    }
                    q13_8[i] = best_v;
                    q8[i] = crt(q2_8[i], best_v);
                    if (best_v != old_v) { cur_score = best_s; improved = 1; }
                }

                for (int i = 0; i < 8; i++) {
                    int old_v = q13_9[i];
                    int best_v = old_v;
                    float best_s = cur_score;
                    for (int v = 0; v < 13; v++) {
                        if (v == old_v) continue;
                        q9[i] = crt(q2_9[i], v);
                        for (int idx = 0; idx < N; idx++) {
                            int k = (q7[idx % 7] + q8[idx % 8] + q9[idx % 9]) % 26;
                            p[idx] = alpha_to_std[(c_idx[idx] - k + 26) % 26];
                        }
                        float s = score_plain(p);
                        if (s > best_s) { best_s = s; best_v = v; }
                    }
                    q13_9[i] = best_v;
                    q9[i] = crt(q2_9[i], best_v);
                    if (best_v != old_v) { cur_score = best_s; improved = 1; }
                }
            }

            if (cur_score > local_best_score) {
                local_best_score = cur_score;
                for (int i = 0; i < 7; i++) local_best_q7[i] = q7[i];
                for (int i = 0; i < 8; i++) local_best_q8[i] = q8[i];
                for (int i = 0; i < 9; i++) local_best_q9[i] = q9[i];
            }
        }

        #pragma omp critical
        {
            if (local_best_score > global_best_score) {
                global_best_score = local_best_score;
                for (int i = 0; i < 7; i++) best_q7[i] = local_best_q7[i];
                for (int i = 0; i < 8; i++) best_q8[i] = local_best_q8[i];
                for (int i = 0; i < 9; i++) best_q9[i] = local_best_q9[i];

                char plain_str[N+1];
                for (int idx = 0; idx < N; idx++) {
                    int k = (best_q7[idx % 7] + best_q8[idx % 8] + best_q9[idx % 9]) % 26;
                    plain_str[idx] = 'A' + alpha_to_std[(c_idx[idx] - k + 26) % 26];
                }
                plain_str[N] = '\0';

                printf("\n>>> NEW BEST (Score = %.4f):\n", global_best_score);
                printf("  q7: [");
                for (int i = 0; i < 7; i++) printf("%d%s", best_q7[i], i==6 ? "]\n" : ", ");
                printf("  q8: [");
                for (int i = 0; i < 8; i++) printf("%d%s", best_q8[i], i==7 ? "]\n" : ", ");
                printf("  q9: [");
                for (int i = 0; i < 9; i++) printf("%d%s", best_q9[i], i==8 ? "]\n" : ", ");
                printf("  Plaintext: %.80s...\n", plain_str);
                fflush(stdout);
            }
        }
    }

    double elapsed = omp_get_wtime() - t0;
    printf("\nCompleted %d restarts in %.2f s (%.1f restarts/sec)\n",
           total_restarts, elapsed, total_restarts / elapsed);
    printf("Global Best Quadgram Score = %.4f (Native English: ~ -4.3, Random: ~ -6.5)\n",
           global_best_score);

    return 0;
}
