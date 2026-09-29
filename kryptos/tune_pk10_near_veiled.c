#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>

#define N 504

const char *KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
const char *PK10_CT = "UBINFYJSFQXQVRLJJAJDGBXIWKDMAREZTGSHQWRXCHEPCLYSDNGYRRBTCVOZJYVLYWREJTCDOYVEYCJJVZKRMKTRPGVHRWMJSRCSHXZMJEVQKJYJJAYZKDFQBGRSWXATJMEXKFXAXKSIZXOERFESNVCGCNRHEOBCNCBUPXTJJRCIMDMRUVZWRDRRFXAPGPIGSPLILFIZSTDZYOVQGGDFUFZPUOJPJVWREUVRQIYPCEHGYUZUKWTFXELUNOKBANZFTFRMXZSXXQSBGPCWGXPFSCANSVUYLMTZIRCCCJJPBQAEPWVCDIMLOPOXQEGJKVQIVHEFAPQMVCYSQAFKCTYTPAOOJZCWIPGDPAFTINBFFHVXYEQXCEIDJJOUABBAHSWKHGMLJBXDSQEFBBDLTLJPLZPIPPTRGDRZIZPUPYJODOCSOYCZZWTKYWMBQTFMFEQZWVPQYLJTMEYKYBNOPEPUMHCFJSLFWOISWLKFFABTYFQDTEQBDELIEOZQ";

static const int q2_7[7] = {0, 1, 1, 1, 0, 0, 0};
static const int q2_8[8] = {0, 0, 0, 1, 0, 1, 0, 0};
static const int q2_9[9] = {0, 0, 1, 1, 1, 1, 0, 0, 0};

// Seed keys from optimize_pk10_monograms
static const int base_q7[7] = {20, 3, 1, 13, 14, 22, 8};
static const int base_q8[8] = {24, 0, 4, 21, 2, 5, 10, 0};
static const int base_q9[9] = {0, 0, 11, 19, 7, 25, 6, 6, 0};

static inline int crt(int q2, int q13) {
    return (13 * q2 + 14 * q13) % 26;
}

static inline int get_q13(int q) {
    return q % 13;
}

static int c_idx[N];
static int alpha_to_std[26];
static float quad[26][26][26][26];

void load_quadgrams() {
    for (int a = 0; a < 26; a++)
        for (int b = 0; b < 26; b++)
            for (int c = 0; c < 26; c++)
                for (int d = 0; d < 26; d++)
                    quad[a][b][c][d] = -9.5f;

    FILE *f = fopen("english_quads.tsv", "r");
    if (!f) exit(1);
    char q[16]; float sc;
    while (fscanf(f, "%s %f", q, &sc) == 2) {
        if (strlen(q) == 4) {
            int a = q[0]-'A', b = q[1]-'A', c = q[2]-'A', d = q[3]-'A';
            if (a>=0 && a<26 && b>=0 && b<26 && c>=0 && c<26 && d>=0 && d<26) {
                quad[a][b][c][d] = sc;
            }
        }
    }
    fclose(f);
}

void init_tables() {
    for (int i = 0; i < 26; i++) {
        alpha_to_std[i] = KRYPTOS[i] - 'A';
    }
    for (int i = 0; i < N; i++) {
        c_idx[i] = strchr(KRYPTOS, PK10_CT[i]) - KRYPTOS;
    }
}

static inline float score_plain(const int *pt) {
    float s = 0.0f;
    for (int i = 0; i < N - 3; i++) {
        s += quad[pt[i]][pt[i+1]][pt[i+2]][pt[i+3]];
    }
    return s / (N - 3);
}

int main() {
    init_tables();
    load_quadgrams();

    int q13_7[7], q13_8[8], q13_9[9];
    for (int i = 0; i < 7; i++) q13_7[i] = get_q13(base_q7[i]);
    for (int i = 0; i < 8; i++) q13_8[i] = get_q13(base_q8[i]);
    for (int i = 0; i < 9; i++) q13_9[i] = get_q13(base_q9[i]);

    int pt[N];
    for (int i = 0; i < N; i++) {
        int k = (base_q7[i % 7] + base_q8[i % 8] + base_q9[i % 9]) % 26;
        int p = (c_idx[i] - k + 26) % 26;
        pt[i] = alpha_to_std[p];
    }
    float initial_sc = score_plain(pt);
    printf("Initial Base Score = %.4f\n", initial_sc);

    // Multi-restart simulated annealing centered around base key
    int num_restarts = 1000;
    printf("Searching neighborhood of base key with %d restarts...\n", num_restarts);

    float global_best_sc = initial_sc;
    int best_q7[7], best_q8[8], best_q9[9];
    char best_pt[N + 1] = "";

    double t0 = omp_get_wtime();

    #pragma omp parallel
    {
        unsigned int seed = 42 + omp_get_thread_num() * 1337;
        float local_best_sc = -999.0f;
        int local_best_q7[7], local_best_q8[8], local_best_q9[9];
        char local_best_pt[N + 1] = "";

        int local_pt[N];

        #pragma omp for schedule(dynamic, 100)
        for (int r = 0; r < num_restarts; r++) {
            // Start near base with 1-4 random perturbations
            int cur_q13_7[7], cur_q13_8[8], cur_q13_9[9];
            for (int i = 0; i < 7; i++) cur_q13_7[i] = q13_7[i];
            for (int i = 0; i < 8; i++) cur_q13_8[i] = q13_8[i];
            for (int i = 0; i < 9; i++) cur_q13_9[i] = q13_9[i];

            int perturbs = 1 + rand_r(&seed) % 4;
            for (int p = 0; p < perturbs; p++) {
                int clk = rand_r(&seed) % 3;
                if (clk == 0) {
                    int pos = rand_r(&seed) % 7;
                    cur_q13_7[pos] = (cur_q13_7[pos] + 1 + rand_r(&seed) % 12) % 13;
                } else if (clk == 1) {
                    int pos = rand_r(&seed) % 7;
                    cur_q13_8[pos] = (cur_q13_8[pos] + 1 + rand_r(&seed) % 12) % 13;
                } else {
                    int pos = rand_r(&seed) % 8;
                    cur_q13_9[pos] = (cur_q13_9[pos] + 1 + rand_r(&seed) % 12) % 13;
                }
            }

            int q7[7], q8[8], q9[9];
            for (int i = 0; i < 7; i++) q7[i] = crt(q2_7[i], cur_q13_7[i]);
            for (int i = 0; i < 8; i++) q8[i] = crt(q2_8[i], cur_q13_8[i]);
            for (int i = 0; i < 9; i++) q9[i] = crt(q2_9[i], cur_q13_9[i]);

            for (int i = 0; i < N; i++) {
                int k = (q7[i % 7] + q8[i % 8] + q9[i % 9]) % 26;
                local_pt[i] = alpha_to_std[(c_idx[i] - k + 26) % 26];
            }
            float cur_sc = score_plain(local_pt);

            // Greedy ascent
            int improved = 1;
            int passes = 0;
            while (improved && passes < 6) {
                improved = 0;
                passes++;

                for (int i = 0; i < 7; i++) {
                    int old_v = cur_q13_7[i];
                    int best_v = old_v;
                    float best_s = cur_sc;
                    for (int v = 0; v < 13; v++) {
                        if (v == old_v) continue;
                        q7[i] = crt(q2_7[i], v);
                        for (int idx = 0; idx < N; idx++) {
                            int k = (q7[idx % 7] + q8[idx % 8] + q9[idx % 9]) % 26;
                            local_pt[idx] = alpha_to_std[(c_idx[idx] - k + 26) % 26];
                        }
                        float s = score_plain(local_pt);
                        if (s > best_s) { best_s = s; best_v = v; }
                    }
                    cur_q13_7[i] = best_v;
                    q7[i] = crt(q2_7[i], best_v);
                    if (best_v != old_v) { cur_sc = best_s; improved = 1; }
                }

                for (int i = 0; i < 7; i++) {
                    int old_v = cur_q13_8[i];
                    int best_v = old_v;
                    float best_s = cur_sc;
                    for (int v = 0; v < 13; v++) {
                        if (v == old_v) continue;
                        q8[i] = crt(q2_8[i], v);
                        for (int idx = 0; idx < N; idx++) {
                            int k = (q7[idx % 7] + q8[idx % 8] + q9[idx % 9]) % 26;
                            local_pt[idx] = alpha_to_std[(c_idx[idx] - k + 26) % 26];
                        }
                        float s = score_plain(local_pt);
                        if (s > best_s) { best_s = s; best_v = v; }
                    }
                    cur_q13_8[i] = best_v;
                    q8[i] = crt(q2_8[i], best_v);
                    if (best_v != old_v) { cur_sc = best_s; improved = 1; }
                }

                for (int i = 0; i < 8; i++) {
                    int old_v = cur_q13_9[i];
                    int best_v = old_v;
                    float best_s = cur_sc;
                    for (int v = 0; v < 13; v++) {
                        if (v == old_v) continue;
                        q9[i] = crt(q2_9[i], v);
                        for (int idx = 0; idx < N; idx++) {
                            int k = (q7[idx % 7] + q8[idx % 8] + q9[idx % 9]) % 26;
                            local_pt[idx] = alpha_to_std[(c_idx[idx] - k + 26) % 26];
                        }
                        float s = score_plain(local_pt);
                        if (s > best_s) { best_s = s; best_v = v; }
                    }
                    cur_q13_9[i] = best_v;
                    q9[i] = crt(q2_9[i], best_v);
                    if (best_v != old_v) { cur_sc = best_s; improved = 1; }
                }
            }

            if (cur_sc > local_best_sc) {
                local_best_sc = cur_sc;
                for (int i = 0; i < 7; i++) local_best_q7[i] = q7[i];
                for (int i = 0; i < 8; i++) local_best_q8[i] = q8[i];
                for (int i = 0; i < 9; i++) local_best_q9[i] = q9[i];
                for (int i = 0; i < N; i++) local_best_pt[i] = 'A' + local_pt[i];
                local_best_pt[N] = '\0';
            }
        }

        #pragma omp critical
        {
            if (local_best_sc > global_best_sc) {
                global_best_sc = local_best_sc;
                for (int i = 0; i < 7; i++) best_q7[i] = local_best_q7[i];
                for (int i = 0; i < 8; i++) best_q8[i] = local_best_q8[i];
                for (int i = 0; i < 9; i++) best_q9[i] = local_best_q9[i];
                strcpy(best_pt, local_best_pt);

                printf("\n>>> IMPROVEMENT! Score = %.4f (Base: %.4f)\n", global_best_sc, initial_sc);
                printf("  q7: [");
                for (int i = 0; i < 7; i++) printf("%d%s", best_q7[i], i==6 ? "]\n" : ", ");
                printf("  q8: [");
                for (int i = 0; i < 8; i++) printf("%d%s", best_q8[i], i==7 ? "]\n" : ", ");
                printf("  q9: [");
                for (int i = 0; i < 9; i++) printf("%d%s", best_q9[i], i==8 ? "]\n" : ", ");
                printf("  PT: %.80s...\n", best_pt);
                fflush(stdout);
            }
        }
    }

    double elapsed = omp_get_wtime() - t0;
    printf("\nCompleted in %.2f s (%.1f restarts/sec)\n", elapsed, num_restarts / elapsed);
    printf("Final Best Score = %.4f\n", global_best_sc);
    printf("Plaintext:\n%s\n", best_pt);

    return 0;
}
