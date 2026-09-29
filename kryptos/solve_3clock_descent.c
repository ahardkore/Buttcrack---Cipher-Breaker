#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <stdint.h>
#include <omp.h>

static float quad_table[26][26][26][26];
static const char *ALPH_K = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
static int k_to_std[26];
static int std_to_k[26];

static const char *C_STR = "KSYAWFEYYOISZGEUFBLYATAIBYFAQBQYYVDWJKLJXMYIEPIFVHPQNHZGSUHUUDXLEHRHUMALHEGLHXSJMUXGNUIVBXGUJHZRZGUSVHMLSCTSUQXHSUMQQIFUQGKHJGUQGLHDKEWSKAMHIJXD";
static int C[144];
static const int N = 144;

void init() {
    for (int i = 0; i < 26; i++) {
        for (int j = 0; j < 26; j++) {
            for (int k = 0; k < 26; k++) {
                for (int l = 0; l < 26; l++) {
                    quad_table[i][j][k][l] = -9.5f;
                }
            }
        }
    }
    FILE *f = fopen("/home/user/english_quads.tsv", "r");
    if (!f) { fprintf(stderr, "Cannot open quads\n"); exit(1); }
    char q[16];
    float sc;
    while (fscanf(f, "%s\t%f", q, &sc) == 2) {
        if (strlen(q) == 4) {
            int c0 = q[0]-'A', c1 = q[1]-'A', c2 = q[2]-'A', c3 = q[3]-'A';
            if (c0>=0&&c0<26&&c1>=0&&c1<26&&c2>=0&&c2<26&&c3>=0&&c3<26) {
                quad_table[c0][c1][c2][c3] = sc;
            }
        }
    }
    fclose(f);

    for (int i = 0; i < 26; i++) {
        int std = ALPH_K[i] - 'A';
        k_to_std[i] = std;
        std_to_k[std] = i;
    }
    for (int i = 0; i < N; i++) {
        C[i] = std_to_k[C_STR[i] - 'A'];
    }
}

static inline uint32_t xorshift32(uint32_t *state) {
    uint32_t x = *state;
    x ^= x << 13;
    x ^= x >> 17;
    x ^= x << 5;
    *state = x;
    return x;
}

static inline float eval_ks(const int *ks, int is_kryptos) {
    int pt[144];
    for (int i = 0; i < N; i++) {
        int pi = (C[i] - ks[i] + 26) % 26;
        if (is_kryptos) pt[i] = k_to_std[pi];
        else pt[i] = pi;
    }
    float sc = 0.0f;
    for (int i = 0; i < N - 3; i++) {
        sc += quad_table[pt[i]][pt[i+1]][pt[i+2]][pt[i+3]];
    }
    return sc / (N - 3);
}

void search_3clock(int p1, int p2, int p3, int is_kryptos, int n_restarts) {
    printf("\n=== Coordinate Descent for Clocks (%d, %d, %d) | %s | %d restarts ===\n",
           p1, p2, p3, is_kryptos ? "KRYPTOS" : "STD", n_restarts);

    double t0 = omp_get_wtime();
    float global_best_sc = -999.0f;
    int best_k1[16], best_k2[16], best_k3[16];
    char best_pt[150] = "";

    #pragma omp parallel
    {
        uint32_t rng = 1337 + omp_get_thread_num() * 10007;
        float local_best_sc = -999.0f;
        int local_k1[16], local_k2[16], local_k3[16];
        char local_pt[150] = "";

        #pragma omp for schedule(dynamic, 64)
        for (int r = 0; r < n_restarts; r++) {
            int k1[16] = {0}, k2[16] = {0}, k3[16] = {0};
            // Gauge fix: k1[0] = 0, k2[0] = 0
            for (int i = 1; i < p1; i++) k1[i] = xorshift32(&rng) % 26;
            for (int i = 1; i < p2; i++) k2[i] = xorshift32(&rng) % 26;
            for (int i = 0; i < p3; i++) k3[i] = xorshift32(&rng) % 26;

            int ks[144];
            for (int i = 0; i < N; i++) {
                ks[i] = (k1[i % p1] + k2[i % p2] + k3[i % p3]) % 26;
            }
            float cur_sc = eval_ks(ks, is_kryptos);

            // Coordinate descent
            int changed = 1;
            int max_rounds = 15;
            int round = 0;

            while (changed && round < max_rounds) {
                changed = 0;
                round++;

                // Optimize k1[1..p1-1]
                for (int pos = 1; pos < p1; pos++) {
                    int best_v = k1[pos];
                    float best_s = cur_sc;
                    for (int v = 0; v < 26; v++) {
                        if (v == k1[pos]) continue;
                        k1[pos] = v;
                        for (int i = 0; i < N; i++) {
                            ks[i] = (k1[i % p1] + k2[i % p2] + k3[i % p3]) % 26;
                        }
                        float sc = eval_ks(ks, is_kryptos);
                        if (sc > best_s) {
                            best_s = sc;
                            best_v = v;
                        }
                    }
                    if (best_v != k1[pos]) {
                        k1[pos] = best_v;
                        cur_sc = best_s;
                        changed = 1;
                    } else {
                        // Revert
                        k1[pos] = best_v;
                    }
                }

                // Optimize k2[1..p2-1]
                for (int pos = 1; pos < p2; pos++) {
                    int best_v = k2[pos];
                    float best_s = cur_sc;
                    for (int v = 0; v < 26; v++) {
                        if (v == k2[pos]) continue;
                        k2[pos] = v;
                        for (int i = 0; i < N; i++) {
                            ks[i] = (k1[i % p1] + k2[i % p2] + k3[i % p3]) % 26;
                        }
                        float sc = eval_ks(ks, is_kryptos);
                        if (sc > best_s) {
                            best_s = sc;
                            best_v = v;
                        }
                    }
                    if (best_v != k2[pos]) {
                        k2[pos] = best_v;
                        cur_sc = best_s;
                        changed = 1;
                    } else {
                        k2[pos] = best_v;
                    }
                }

                // Optimize k3[0..p3-1]
                for (int pos = 0; pos < p3; pos++) {
                    int best_v = k3[pos];
                    float best_s = cur_sc;
                    for (int v = 0; v < 26; v++) {
                        if (v == k3[pos]) continue;
                        k3[pos] = v;
                        for (int i = 0; i < N; i++) {
                            ks[i] = (k1[i % p1] + k2[i % p2] + k3[i % p3]) % 26;
                        }
                        float sc = eval_ks(ks, is_kryptos);
                        if (sc > best_s) {
                            best_s = sc;
                            best_v = v;
                        }
                    }
                    if (best_v != k3[pos]) {
                        k3[pos] = best_v;
                        cur_sc = best_s;
                        changed = 1;
                    } else {
                        k3[pos] = best_v;
                    }
                }
            }

            if (cur_sc > local_best_sc) {
                local_best_sc = cur_sc;
                memcpy(local_k1, k1, sizeof(k1));
                memcpy(local_k2, k2, sizeof(k2));
                memcpy(local_k3, k3, sizeof(k3));
                for (int i = 0; i < N; i++) {
                    int pi = (C[i] - ks[i] + 26) % 26;
                    local_pt[i] = (is_kryptos ? k_to_std[pi] : pi) + 'A';
                }
                local_pt[N] = '\0';

                if (cur_sc > -5.8f) {
                    #pragma omp critical
                    {
                        printf("  >>> HIGH SCORE: sc=%.3f\n    PT: %s\n", cur_sc, local_pt);
                    }
                }
            }
        }

        #pragma omp critical
        {
            if (local_best_sc > global_best_sc) {
                global_best_sc = local_best_sc;
                memcpy(best_k1, local_k1, sizeof(best_k1));
                memcpy(best_k2, local_k2, sizeof(best_k2));
                memcpy(best_k3, local_k3, sizeof(best_k3));
                strcpy(best_pt, local_pt);
            }
        }
    }

    double t1 = omp_get_wtime();
    printf("Finished in %.2f seconds. Best score: %.3f\n  PT: %.70s...\n",
           t1 - t0, global_best_sc, best_pt);
}

int main() {
    init();

    // 1. Clocks (4, 5, 7) on KRYPTOS
    search_3clock(4, 5, 7, 1, 5000);

    // 2. Clocks (4, 5, 7) on STANDARD
    search_3clock(4, 5, 7, 0, 5000);

    // 3. Clocks (4, 6, 7) on KRYPTOS
    search_3clock(4, 6, 7, 1, 5000);

    // 4. Clocks (5, 6, 7) on KRYPTOS
    search_3clock(5, 6, 7, 1, 5000);

    return 0;
}
