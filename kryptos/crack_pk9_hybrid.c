#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <time.h>
#include <omp.h>

#define N 144
#define W 12
#define H 12

static const char *ALPH = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
static const char *PK9_REAL = "KSYAWFEYYOISZGEUFBLYATAIBYFAQBQYYVDWJKLJXMYIEPIFVHPQNHZGSUHUUDXLEHRHUMALHEGLHXSJMUXGNUIVBXGUJHZRZGUSVHMLSCTSUQXHSUMQQIFUQGKHJGUQGLHDKEWSKAMHIJXD";

static int ct_kr[N];
static int ct_std[N];
static int kr_to_std[26];
static int std_to_kr[26];

static float quad_table[26][26][26][26];
static double log_monogram[26];

void load_models() {
    for (int a = 0; a < 26; a++)
        for (int b = 0; b < 26; b++)
            for (int c = 0; c < 26; c++)
                for (int d = 0; d < 26; d++)
                    quad_table[a][b][c][d] = -9.5f;

    FILE *f = fopen("english_quadgrams.txt", "r");
    if (!f) exit(1);
    char q[16]; double cnt; double total = 0;
    while (fscanf(f, "%s %lf", q, &cnt) == 2) if (strlen(q) == 4) total += cnt;
    rewind(f);
    double mono_counts[26] = {0}, mono_tot = 0;
    while (fscanf(f, "%s %lf", q, &cnt) == 2) {
        if (strlen(q) == 4) {
            int a = q[0]-'A', b = q[1]-'A', c = q[2]-'A', d = q[3]-'A';
            if (a>=0&&a<26&&b>=0&&b<26&&c>=0&&c<26&&d>=0&&d<26) {
                quad_table[a][b][c][d] = (float)log10((cnt + 0.01) / total);
                mono_counts[a] += cnt; mono_counts[b] += cnt; mono_counts[c] += cnt; mono_counts[d] += cnt;
                mono_tot += 4 * cnt;
            }
        }
    }
    fclose(f);

    for (int a = 0; a < 26; a++) {
        log_monogram[a] = log10((mono_counts[a] + 0.1) / mono_tot);
        kr_to_std[a] = ALPH[a] - 'A';
        std_to_kr[ALPH[a] - 'A'] = a;
    }
    for (int i = 0; i < N; i++) {
        ct_kr[i] = std_to_kr[PK9_REAL[i] - 'A'];
        ct_std[i] = PK9_REAL[i] - 'A';
    }
}

void col_decrypt(const int *in, const int *order, int *out, int w, int h) {
    int grid[H][W];
    int idx = 0;
    for (int c_idx = 0; c_idx < w; c_idx++) {
        int col = order[c_idx];
        for (int r = 0; r < h; r++) grid[r][col] = in[idx++];
    }
    idx = 0;
    for (int r = 0; r < h; r++)
        for (int c = 0; c < w; c++) out[idx++] = grid[r][c];
}

static inline float score_quadgrams(const int *txt) {
    float s = 0.0f;
    for (int i = 0; i < N - 3; i++) {
        s += quad_table[txt[i]][txt[i+1]][txt[i+2]][txt[i+3]];
    }
    return s / (N - 3);
}

// Compute pt_to_z2 mapping for a pair of orders (o1, o2)
static inline void get_mapping(const int *o1, const int *o2, int *pt_to_z2) {
    int identity[N]; for (int j = 0; j < N; j++) identity[j] = j;
    int after2[N];
    col_decrypt(identity, o2, after2, W, H);
    col_decrypt(after2, o1, pt_to_z2, W, H);
}

// Decrypt text given pt_to_z2 mapping and 28 shifts (Mode 1: Kryptos Beaufort)
static inline void decrypt_with_shifts(const int *pt_to_z2, const int *shifts, int *pt) {
    for (int t = 0; t < N; t++) {
        int pos = pt_to_z2[t];
        int sh = shifts[pos % 28];
        int c_val = ct_kr[pos];
        int p_val = (sh - c_val + 26) % 26;
        pt[t] = kr_to_std[p_val];
    }
}

// Fit 28 shifts by monogram maximum likelihood
static inline void fit_monogram_shifts(const int *pt_to_z2, int *best_shifts) {
    for (int s = 0; s < 28; s++) {
        double best_s_sc = -1e9;
        int best_sh = 0;
        for (int sh = 0; sh < 26; sh++) {
            double cur_s_sc = 0.0;
            for (int t = 0; t < N; t++) {
                int pos = pt_to_z2[t];
                if (pos % 28 == s) {
                    int c_val = ct_kr[pos];
                    int p_val = (sh - c_val + 26) % 26;
                    int std_c = kr_to_std[p_val];
                    cur_s_sc += log_monogram[std_c];
                }
            }
            if (cur_s_sc > best_s_sc) { best_s_sc = cur_s_sc; best_sh = sh; }
        }
        best_shifts[s] = best_sh;
    }
}

// Quadgram polish on shifts: coordinate descent on all 28 shifts
float polish_shifts_quadgram(const int *pt_to_z2, int *shifts, int *pt) {
    decrypt_with_shifts(pt_to_z2, shifts, pt);
    float cur_sc = score_quadgrams(pt);

    int improved = 1;
    int passes = 0;
    while (improved && passes < 5) {
        improved = 0;
        passes++;
        for (int s = 0; s < 28; s++) {
            int orig_val = shifts[s];
            int best_val = orig_val;
            float best_sc = cur_sc;

            for (int v = 0; v < 26; v++) {
                if (v == orig_val) continue;
                shifts[s] = v;
                int test_pt[N];
                decrypt_with_shifts(pt_to_z2, shifts, test_pt);
                float sc = score_quadgrams(test_pt);
                if (sc > best_sc) {
                    best_sc = sc;
                    best_val = v;
                }
            }
            if (best_val != orig_val) {
                shifts[s] = best_val;
                cur_sc = best_sc;
                improved = 1;
            } else {
                shifts[s] = orig_val;
            }
        }
    }
    decrypt_with_shifts(pt_to_z2, shifts, pt);
    return cur_sc;
}

// Mutate a permutation (swap, 2-opt, insert)
static inline void mutate_perm(int *p, unsigned int *seed) {
    int r = rand_r(seed) % 100;
    if (r < 40) {
        // Swap 2
        int a = rand_r(seed) % W;
        int b = rand_r(seed) % W;
        int t = p[a]; p[a] = p[b]; p[b] = t;
    } else if (r < 75) {
        // 2-opt (reverse segment)
        int a = rand_r(seed) % W;
        int b = rand_r(seed) % W;
        if (a > b) { int t = a; a = b; b = t; }
        while (a < b) {
            int t = p[a]; p[a] = p[b]; p[b] = t;
            a++; b--;
        }
    } else {
        // Insert (move element a to position b)
        int a = rand_r(seed) % W;
        int b = rand_r(seed) % W;
        int val = p[a];
        if (a < b) {
            for (int k = a; k < b; k++) p[k] = p[k+1];
        } else {
            for (int k = a; k > b; k--) p[k] = p[k-1];
        }
        p[b] = val;
    }
}

int main() {
    load_models();
    printf("Models loaded. Starting Hybrid Crack Engine (SA + 2-Opt + Quadgram Shift Polish)...\n");

    // Seeds from our previous best discovery
    int seed_o1[W] = {3, 4, 11, 10, 6, 1, 8, 7, 9, 0, 5, 2};
    int seed_o2[W] = {0, 7, 8, 2, 4, 10, 9, 1, 6, 5, 3, 11};

    float global_best_sc = -999.0f;
    int global_best_o1[W], global_best_o2[W];
    int global_best_shifts[28];
    int global_best_pt[N];

    double t0 = omp_get_wtime();

    #pragma omp parallel
    {
        unsigned int seed = 77777 + omp_get_thread_num() * 22222;
        float local_best_sc = -999.0f;
        int local_best_o1[W], local_best_o2[W];
        int local_best_shifts[28];
        int local_best_pt[N];

        int cur_o1[W], cur_o2[W];
        int cur_pt_to_z2[N];
        int cur_shifts[28];
        int cur_pt[N];

        for (int restart = 0; restart < 150; restart++) {
            // Half restarts seeded around our best discovery, half random
            if (restart % 2 == 0) {
                memcpy(cur_o1, seed_o1, sizeof(cur_o1));
                memcpy(cur_o2, seed_o2, sizeof(cur_o2));
                // Add a small jitter
                for (int j = 0; j < (restart % 4); j++) {
                    mutate_perm(cur_o1, &seed);
                    mutate_perm(cur_o2, &seed);
                }
            } else {
                for (int i = 0; i < W; i++) { cur_o1[i] = i; cur_o2[i] = i; }
                for (int i = W - 1; i > 0; i--) {
                    int j1 = rand_r(&seed) % (i + 1);
                    int t1 = cur_o1[i]; cur_o1[i] = cur_o1[j1]; cur_o1[j1] = t1;
                    int j2 = rand_r(&seed) % (i + 1);
                    int t2 = cur_o2[i]; cur_o2[i] = cur_o2[j2]; cur_o2[j2] = t2;
                }
            }

            get_mapping(cur_o1, cur_o2, cur_pt_to_z2);
            fit_monogram_shifts(cur_pt_to_z2, cur_shifts);
            decrypt_with_shifts(cur_pt_to_z2, cur_shifts, cur_pt);
            float cur_sc = score_quadgrams(cur_pt);

            float T = 0.5f;
            float T_min = 0.005f;
            float alpha = 0.999f;

            for (int step = 0; step < 2000; step++) {
                int next_o1[W], next_o2[W];
                memcpy(next_o1, cur_o1, sizeof(next_o1));
                memcpy(next_o2, cur_o2, sizeof(next_o2));

                if (rand_r(&seed) % 2 == 0) {
                    mutate_perm(next_o1, &seed);
                } else {
                    mutate_perm(next_o2, &seed);
                }

                int next_pt_to_z2[N];
                get_mapping(next_o1, next_o2, next_pt_to_z2);
                int next_shifts[28];
                fit_monogram_shifts(next_pt_to_z2, next_shifts);
                int next_pt[N];
                decrypt_with_shifts(next_pt_to_z2, next_shifts, next_pt);
                float next_sc = score_quadgrams(next_pt);

                float diff = next_sc - cur_sc;
                if (diff > 0.0f || expf(diff / T) > ((float)rand_r(&seed) / RAND_MAX)) {
                    cur_sc = next_sc;
                    memcpy(cur_o1, next_o1, sizeof(cur_o1));
                    memcpy(cur_o2, next_o2, sizeof(cur_o2));
                    memcpy(cur_pt_to_z2, next_pt_to_z2, sizeof(cur_pt_to_z2));
                    memcpy(cur_shifts, next_shifts, sizeof(cur_shifts));
                    memcpy(cur_pt, next_pt, sizeof(cur_pt));

                    // If score is high (> -6.15), polish shifts with quadgrams!
                    if (cur_sc > -6.15f) {
                        float polished_sc = polish_shifts_quadgram(cur_pt_to_z2, cur_shifts, cur_pt);
                        if (polished_sc > cur_sc) {
                            cur_sc = polished_sc;
                        }
                    }

                    if (cur_sc > local_best_sc) {
                        local_best_sc = cur_sc;
                        memcpy(local_best_o1, cur_o1, sizeof(cur_o1));
                        memcpy(local_best_o2, cur_o2, sizeof(cur_o2));
                        memcpy(local_best_shifts, cur_shifts, sizeof(cur_shifts));
                        memcpy(local_best_pt, cur_pt, sizeof(cur_pt));
                    }
                }

                T *= alpha;
                if (T < T_min) T = T_min;
            }
        }

        #pragma omp critical
        {
            if (local_best_sc > global_best_sc) {
                global_best_sc = local_best_sc;
                memcpy(global_best_o1, local_best_o1, sizeof(global_best_o1));
                memcpy(global_best_o2, local_best_o2, sizeof(global_best_o2));
                memcpy(global_best_shifts, local_best_shifts, sizeof(global_best_shifts));
                memcpy(global_best_pt, local_best_pt, sizeof(global_best_pt));

                char pt_str[N+1];
                for (int i = 0; i < N; i++) pt_str[i] = global_best_pt[i] + 'A';
                pt_str[N] = '\0';

                printf("\n>>> [Thread %d] BREAKTHROUGH SCORE: %.4f <<<\n",
                       omp_get_thread_num(), global_best_sc);
                printf("  o1: [");
                for (int i = 0; i < W; i++) printf("%d%s", global_best_o1[i], i==W-1?"":", ");
                printf("]\n");
                printf("  o2: [");
                for (int i = 0; i < W; i++) printf("%d%s", global_best_o2[i], i==W-1?"":", ");
                printf("]\n");
                printf("  shifts: [");
                for (int i = 0; i < 28; i++) printf("%d%s", global_best_shifts[i], i==27?"":", ");
                printf("]\n");
                printf("  PT: %.120s\n", pt_str);
            }
        }
    }

    double elapsed = omp_get_wtime() - t0;
    printf("\nExecution finished in %.2f seconds.\n", elapsed);
    printf("FINAL CRACK SCORE: %.4f\n", global_best_sc);
    char final_pt[N+1];
    for (int i = 0; i < N; i++) final_pt[i] = global_best_pt[i] + 'A';
    final_pt[N] = '\0';
    printf("Plaintext:\n%s\n", final_pt);

    return 0;
}
