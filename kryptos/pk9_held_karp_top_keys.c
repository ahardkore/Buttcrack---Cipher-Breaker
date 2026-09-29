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

static float bigram_table[26][26];
static float quad_table[26][26][26][26];
static double log_monogram[26];

void load_models() {
    for (int a = 0; a < 26; a++) {
        for (int b = 0; b < 26; b++) {
            bigram_table[a][b] = -7.0f;
            for (int c = 0; c < 26; c++)
                for (int d = 0; d < 26; d++)
                    quad_table[a][b][c][d] = -9.5f;
        }
    }

    FILE *f = fopen("english_quadgrams.txt", "r");
    if (!f) { printf("Missing english_quadgrams.txt\n"); exit(1); }
    char q[16]; double cnt; double total = 0;
    while (fscanf(f, "%s %lf", q, &cnt) == 2) {
        if (strlen(q) == 4) total += cnt;
    }
    rewind(f);

    double bi_counts[26][26] = {0};
    double bi_tot = 0;
    double mono_counts[26] = {0};
    double mono_tot = 0;

    while (fscanf(f, "%s %lf", q, &cnt) == 2) {
        if (strlen(q) == 4) {
            int a = q[0]-'A', b = q[1]-'A', c = q[2]-'A', d = q[3]-'A';
            if (a>=0&&a<26&&b>=0&&b<26&&c>=0&&c<26&&d>=0&&d<26) {
                quad_table[a][b][c][d] = (float)log10((cnt + 0.01) / total);
                bi_counts[a][b] += cnt; bi_counts[b][c] += cnt; bi_counts[c][d] += cnt;
                bi_tot += 3 * cnt;
                mono_counts[a] += cnt; mono_counts[b] += cnt; mono_counts[c] += cnt; mono_counts[d] += cnt;
                mono_tot += 4 * cnt;
            }
        }
    }
    fclose(f);

    for (int a = 0; a < 26; a++) {
        log_monogram[a] = log10((mono_counts[a] + 0.1) / mono_tot);
        for (int b = 0; b < 26; b++) {
            bigram_table[a][b] = (float)log10((bi_counts[a][b] + 0.01) / bi_tot);
        }
    }

    for (int i = 0; i < 26; i++) {
        kr_to_std[i] = ALPH[i] - 'A';
        std_to_kr[ALPH[i] - 'A'] = i;
    }
    for (int i = 0; i < N; i++) {
        ct_kr[i] = std_to_kr[PK9_REAL[i] - 'A'];
        ct_std[i] = PK9_REAL[i] - 'A';
    }
}

// Held-Karp dynamic programming for optimal column permutation
float solve_held_karp(const int cols[W][H], int *best_order, float dp[4096][W], int parent[4096][W]) {
    float cost[W][W];
    for (int i = 0; i < W; i++) {
        for (int j = 0; j < W; j++) {
            if (i == j) { cost[i][j] = -1e9f; continue; }
            float s = 0.0f;
            for (int r = 0; r < H; r++) {
                s += bigram_table[cols[i][r]][cols[j][r]];
            }
            cost[i][j] = s;
        }
    }

    // DP table: 4096 x 12

    for (int m = 0; m < 4096; m++)
        for (int c = 0; c < W; c++)
            dp[m][c] = -1e9f;

    for (int c = 0; c < W; c++) {
        dp[1 << c][c] = 0.0f;
    }

    for (int m = 1; m < 4096; m++) {
        for (int u = 0; u < W; u++) {
            if (!(m & (1 << u))) continue;
            float cur_val = dp[m][u];
            if (cur_val <= -1e8f) continue;

            for (int v = 0; v < W; v++) {
                if (m & (1 << v)) continue;
                int next_m = m | (1 << v);
                float next_val = cur_val + cost[u][v];
                if (next_val > dp[next_m][v]) {
                    dp[next_m][v] = next_val;
                    parent[next_m][v] = u;
                }
            }
        }
    }

    int full_mask = (1 << W) - 1;
    float best_total = -1e9f;
    int best_end = -1;
    for (int c = 0; c < W; c++) {
        if (dp[full_mask][c] > best_total) {
            best_total = dp[full_mask][c];
            best_end = c;
        }
    }

    int curr_m = full_mask;
    int curr_c = best_end;
    for (int step = W - 1; step >= 0; step--) {
        best_order[step] = curr_c;
        int p = parent[curr_m][curr_c];
        curr_m &= ~(1 << curr_c);
        curr_c = p;
    }

    return best_total / (11.0f * H);
}

float score_quadgrams(const char *txt) {
    float s = 0.0f;
    for (int i = 0; i < N - 3; i++) {
        s += quad_table[txt[i]-'A'][txt[i+1]-'A'][txt[i+2]-'A'][txt[i+3]-'A'];
    }
    return s / (N - 3);
}

typedef struct {
    float mono_score;
    int q4[4];
    int q7[7];
    int mode; // 0: Kr-Vig, 1: Kr-Beau, 2: Std-Vig, 3: Std-Beau
} KeyCandidate;

int compare_candidates(const void *a, const void *b) {
    float diff = ((KeyCandidate*)b)->mono_score - ((KeyCandidate*)a)->mono_score;
    return (diff > 0) - (diff < 0);
}

int main() {
    load_models();
    printf("Models loaded. Pre-generating top candidate keys (Q4, Q7) across 4 modes...\n");

    // Allocate memory for candidate keys
    int max_per_mode = 20000;
    KeyCandidate *pool = malloc(4 * max_per_mode * sizeof(KeyCandidate));
    int total_keys = 0;

    for (int mode = 0; mode < 4; mode++) {
        int use_kr = (mode == 0 || mode == 1);
        int is_beau = (mode == 1 || mode == 3);
        const int *src_ct = use_kr ? ct_kr : ct_std;
        const int *to_std = use_kr ? kr_to_std : NULL;

        // Precompute score table for 28 slices
        double score_table[28][26];
        for (int s = 0; s < 28; s++) {
            for (int sh = 0; sh < 26; sh++) {
                double tot = 0.0;
                for (int idx = s; idx < N; idx += 28) {
                    int c_val = src_ct[idx];
                    int p_val = is_beau ? (sh - c_val + 26) % 26 : (c_val - sh + 26) % 26;
                    int std_c = use_kr ? to_std[p_val] : p_val;
                    tot += log_monogram[std_c];
                }
                score_table[s][sh] = tot;
            }
        }

        KeyCandidate *mode_candidates = malloc(17576 * sizeof(KeyCandidate));
        int mc_count = 0;

        int q4[4] = {0, 0, 0, 0};
        for (int q4_1 = 0; q4_1 < 26; q4_1++) {
            q4[1] = q4_1;
            for (int q4_2 = 0; q4_2 < 26; q4_2++) {
                q4[2] = q4_2;
                for (int q4_3 = 0; q4_3 < 26; q4_3++) {
                    q4[3] = q4_3;

                    double tot_sc = 0.0;
                    int cur_q7[7];
                    for (int j = 0; j < 7; j++) {
                        int s0 = j, s1 = j+7, s2 = j+14, s3 = j+21;
                        double best_j_sc = -1e9;
                        int best_v = 0;
                        for (int v = 0; v < 26; v++) {
                            double sc = score_table[s0][(q4[s0 % 4] + v) % 26] +
                                        score_table[s1][(q4[s1 % 4] + v) % 26] +
                                        score_table[s2][(q4[s2 % 4] + v) % 26] +
                                        score_table[s3][(q4[s3 % 4] + v) % 26];
                            if (sc > best_j_sc) {
                                best_j_sc = sc;
                                best_v = v;
                            }
                        }
                        cur_q7[j] = best_v;
                        tot_sc += best_j_sc;
                    }

                    mode_candidates[mc_count].mono_score = (float)tot_sc;
                    memcpy(mode_candidates[mc_count].q4, q4, sizeof(q4));
                    memcpy(mode_candidates[mc_count].q7, cur_q7, sizeof(cur_q7));
                    mode_candidates[mc_count].mode = mode;
                    mc_count++;
                }
            }
        }

        // Sort mode candidates
        qsort(mode_candidates, mc_count, sizeof(KeyCandidate), compare_candidates);

        int take = (mc_count < max_per_mode) ? mc_count : max_per_mode;
        printf("Mode %d: Best mono score = %.2f, taking top %d candidates\n", mode, mode_candidates[0].mono_score, take);
        for (int i = 0; i < take; i++) {
            pool[total_keys++] = mode_candidates[i];
        }
        free(mode_candidates);
    }

    printf("Total candidates pooled across 4 modes: %d. Running Held-Karp ATSP in parallel...\n", total_keys);

    float global_best_quad = -999.0f;
    char global_best_pt[N+1];
    int global_best_perm[W];
    KeyCandidate global_best_key;

    #pragma omp parallel
    {
        float local_best_quad = -999.0f;
        char local_best_pt[N+1];
        int local_best_perm[W];
        KeyCandidate local_best_key;
        float (*thread_dp)[W] = malloc(4096 * sizeof(float[W]));
        int (*thread_parent)[W] = malloc(4096 * sizeof(int[W]));

        #pragma omp for schedule(dynamic, 10)
        for (int k_idx = 0; k_idx < total_keys; k_idx++) {
            KeyCandidate cand = pool[k_idx];
            int mode = cand.mode;
            int use_kr = (mode == 0 || mode == 1);
            int is_beau = (mode == 1 || mode == 3);
            const int *src_ct = use_kr ? ct_kr : ct_std;
            const int *to_std = use_kr ? kr_to_std : NULL;

            // Decrypt Z
            int Z[N];
            for (int i = 0; i < N; i++) {
                int shift = (cand.q4[i % 4] + cand.q7[i % 7]) % 26;
                int c_val = src_ct[i];
                int p_val = is_beau ? (shift - c_val + 26) % 26 : (c_val - shift + 26) % 26;
                Z[i] = use_kr ? to_std[p_val] : p_val;
            }

            // Test Orientation 1: Columns are Z[c*12 + r]
            int cols1[W][H];
            for (int c = 0; c < W; c++) {
                for (int r = 0; r < H; r++) {
                    cols1[c][r] = Z[c * H + r];
                }
            }
            int order1[W];
            solve_held_karp(cols1, order1, thread_dp, thread_parent);

            char pt1[N+1];
            int idx = 0;
            for (int r = 0; r < H; r++) {
                for (int c = 0; c < W; c++) {
                    pt1[idx++] = cols1[order1[c]][r] + 'A';
                }
            }
            pt1[N] = '\0';
            float sc1 = score_quadgrams(pt1);

            if (sc1 > local_best_quad) {
                local_best_quad = sc1;
                strcpy(local_best_pt, pt1);
                memcpy(local_best_perm, order1, sizeof(order1));
                local_best_key = cand;
            }

            // Test Orientation 2: Columns are Z[r*12 + c]
            int cols2[W][H];
            for (int c = 0; c < W; c++) {
                for (int r = 0; r < H; r++) {
                    cols2[c][r] = Z[r * W + c];
                }
            }
            int order2[W];
            solve_held_karp(cols2, order2, thread_dp, thread_parent);

            char pt2[N+1];
            idx = 0;
            for (int r = 0; r < H; r++) {
                for (int c = 0; c < W; c++) {
                    pt2[idx++] = cols2[order2[c]][r] + 'A';
                }
            }
            pt2[N] = '\0';
            float sc2 = score_quadgrams(pt2);

            if (sc2 > local_best_quad) {
                local_best_quad = sc2;
                strcpy(local_best_pt, pt2);
                memcpy(local_best_perm, order2, sizeof(order2));
                local_best_key = cand;
            }
        }

        #pragma omp critical
        {
            if (local_best_quad > global_best_quad) {
                global_best_quad = local_best_quad;
                strcpy(global_best_pt, local_best_pt);
                memcpy(global_best_perm, local_best_perm, sizeof(global_best_perm));
                global_best_key = local_best_key;

                printf("\n>>> NEW BEST QUAD SCORE: %.4f (Mode %d) <<<\n", global_best_quad, global_best_key.mode);
                printf("q4: [%d, %d, %d, %d]\n", global_best_key.q4[0], global_best_key.q4[1], global_best_key.q4[2], global_best_key.q4[3]);
                printf("q7: [%d, %d, %d, %d, %d, %d, %d]\n", global_best_key.q7[0], global_best_key.q7[1], global_best_key.q7[2], global_best_key.q7[3], global_best_key.q7[4], global_best_key.q7[5], global_best_key.q7[6]);
                printf("Permutation: [");
                for (int i = 0; i < W; i++) printf("%d%s", global_best_perm[i], i == W-1 ? "" : ", ");
                printf("]\n");
                printf("Plaintext:\n%s\n\n", global_best_pt);
            }
        }
        free(thread_dp);
        free(thread_parent);
    }

    printf("==================================================\n");
    printf("FINAL BEST RESULT:\n");
    printf("Quadgram score: %.4f | Mode: %d\n", global_best_quad, global_best_key.mode);
    printf("Plaintext:\n%s\n", global_best_pt);
    printf("==================================================\n");

    return 0;
}
