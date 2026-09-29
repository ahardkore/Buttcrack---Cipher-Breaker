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

static const char *M_STR = "QGKVHPZGUKSYHEGBYFHJGQNHSVHAWFLHXAQBUQGZGSMLSEYYSJMQYYLHDUHUCTSOISUXGVDWKEWUDXUQXZGENUIJKLSKALEHHSUUFBVBXJXMMHIRHUMQQLYAGUJYIEJXDMALIFUTAIHZRPIF";
static const char *C_STR = "KSYAWFEYYOISZGEUFBTLAYATAIBYFAQBQYYVDWJKLJXMYIEPIFVHPQNHZGSUHUUDXLEHRHUMALHEGLHXSJMUXGNUIVBXGUJHZRZGUSVHMLSCTSUQXHSUMQQIFUQGKHJGUQGLHDKEWSKAMHIJXD";
static int M[144];
static int C[144];
static const int N = 144;

void init() {
    for (int i = 0; i < 26; i++) {
        for (int j = 0; j < 26; j++) {
            for (int k = 0; k < 26; k++) {
                for (int l = 0; l < 26; l++) {
                    quad_table[i][j][k][l] = -9.0f;
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
        M[i] = std_to_k[M_STR[i] - 'A'];
        C[i] = std_to_k[C_STR[i] - 'A'];
    }
}

static inline float score_decryption(const int *ct, const int *ks, int is_kryptos) {
    int pt[144];
    for (int i = 0; i < N; i++) {
        int p_idx = (ct[i] - ks[i] + 26) % 26;
        if (is_kryptos) pt[i] = k_to_std[p_idx];
        else pt[i] = p_idx;
    }
    float sc = 0.0f;
    for (int i = 0; i < N - 3; i++) {
        sc += quad_table[pt[i]][pt[i+1]][pt[i+2]][pt[i+3]];
    }
    return sc / (N - 3);
}

static inline uint32_t xorshift32(uint32_t *state) {
    uint32_t x = *state;
    x ^= x << 13;
    x ^= x >> 17;
    x ^= x << 5;
    *state = x;
    return x;
}

static inline float rand_uniform(uint32_t *state) {
    return (float)(xorshift32(state) & 0xFFFFFF) / (float)0x1000000;
}

void anneal_clocks(const int *ct, int p1, int p2, int is_kryptos, const char *target_name, int n_restarts, int steps_per_restart) {
    float global_best_sc = -999.0f;
    int global_k1[32], global_k2[32];
    char global_pt[150];

    #pragma omp parallel
    {
        uint32_t rng = 1337 + omp_get_thread_num() * 10007;
        float local_best_sc = -999.0f;
        int local_k1[32], local_k2[32];
        char local_pt[150];

        #pragma omp for schedule(dynamic)
        for (int r = 0; r < n_restarts; r++) {
            int k1[32], k2[32];
            k1[0] = 0;
            for (int i = 1; i < p1; i++) k1[i] = xorshift32(&rng) % 26;
            for (int i = 0; i < p2; i++) k2[i] = xorshift32(&rng) % 26;

            int ks[144];
            for (int i = 0; i < N; i++) ks[i] = (k1[i % p1] + k2[i % p2]) % 26;
            float cur_sc = score_decryption(ct, ks, is_kryptos);

            float best_r_sc = cur_sc;
            int best_r_k1[32], best_r_k2[32];
            memcpy(best_r_k1, k1, sizeof(k1));
            memcpy(best_r_k2, k2, sizeof(k2));

            float T_start = 0.5f;
            float T_end = 0.005f;

            for (int step = 0; step < steps_per_restart; step++) {
                float frac = (float)step / steps_per_restart;
                float T = T_start * powf(T_end / T_start, frac);

                int pick = xorshift32(&rng) % (p1 + p2 - 1);
                int old_val;
                int is_p1 = (pick < p1 - 1);
                int pos = is_p1 ? (pick + 1) : (pick - (p1 - 1));

                if (is_p1) {
                    old_val = k1[pos];
                    k1[pos] = xorshift32(&rng) % 26;
                } else {
                    old_val = k2[pos];
                    k2[pos] = xorshift32(&rng) % 26;
                }

                for (int i = 0; i < N; i++) ks[i] = (k1[i % p1] + k2[i % p2]) % 26;
                float new_sc = score_decryption(ct, ks, is_kryptos);
                float delta = new_sc - cur_sc;

                if (delta > 0.0f || rand_uniform(&rng) < expf(delta / T)) {
                    cur_sc = new_sc;
                    if (cur_sc > best_r_sc) {
                        best_r_sc = cur_sc;
                        memcpy(best_r_k1, k1, sizeof(k1));
                        memcpy(best_r_k2, k2, sizeof(k2));
                    }
                } else {
                    if (is_p1) k1[pos] = old_val;
                    else k2[pos] = old_val;
                }
            }

            if (best_r_sc > local_best_sc) {
                local_best_sc = best_r_sc;
                memcpy(local_k1, best_r_k1, sizeof(k1));
                memcpy(local_k2, best_r_k2, sizeof(k2));
                for (int i = 0; i < N; i++) ks[i] = (local_k1[i % p1] + local_k2[i % p2]) % 26;
                for (int i = 0; i < N; i++) {
                    int p_idx = (ct[i] - ks[i] + 26) % 26;
                    local_pt[i] = (is_kryptos ? k_to_std[p_idx] : p_idx) + 'A';
                }
                local_pt[N] = '\0';
            }
        }

        #pragma omp critical
        {
            if (local_best_sc > global_best_sc) {
                global_best_sc = local_best_sc;
                memcpy(global_k1, local_k1, sizeof(global_k1));
                memcpy(global_k2, local_k2, sizeof(global_k2));
                strcpy(global_pt, local_pt);
            }
        }
    }

    printf("[%s (%d,%d) %s] Best sc: %.3f | PT: %.65s...\n",
           target_name, p1, p2, is_kryptos?"KRYPTOS":"STD", global_best_sc, global_pt);
}

int main() {
    init();
    int pairs[][2] = {{4,7}, {3,7}, {5,7}, {6,7}, {7,8}, {4,5}, {5,8}};
    int num_pairs = 7;

    for (int i = 0; i < num_pairs; i++) {
        anneal_clocks(M, pairs[i][0], pairs[i][1], 1, "M", 400, 2500);
        anneal_clocks(M, pairs[i][0], pairs[i][1], 0, "M", 400, 2500);
        anneal_clocks(C, pairs[i][0], pairs[i][1], 1, "C", 400, 2500);
        anneal_clocks(C, pairs[i][0], pairs[i][1], 0, "C", 400, 2500);
    }
    return 0;
}
