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
    if (!f) { printf("Missing english_quadgrams.txt\n"); exit(1); }
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

// Evaluate a given pair (o1, o2) across all 4 modes, optimizing 28 slice shifts
float evaluate_pair(const int *o1, const int *o2, int *best_mode_out, int *best_pt_out) {
    int identity[N]; for (int j = 0; j < N; j++) identity[j] = j;
    int after2[N], pt_to_z2[N];
    col_decrypt(identity, o2, after2, W, H);
    col_decrypt(after2, o1, pt_to_z2, W, H);

    float best_pair_sc = -999.0f;
    int best_pair_mode = 0;
    int best_pair_pt[N];

    // Evaluate Mode 1 (Kr-Beau) and Mode 0 (Kr-Vig) first as they gave highest scores
    for (int mode = 0; mode < 4; mode++) {
        int use_kr = (mode == 0 || mode == 1);
        int is_beau = (mode == 1 || mode == 3);
        const int *src_ct = use_kr ? ct_kr : ct_std;
        const int *to_std = use_kr ? kr_to_std : NULL;

        int best_shifts[28];
        for (int s = 0; s < 28; s++) {
            double best_s_sc = -1e9;
            int best_sh = 0;
            for (int sh = 0; sh < 26; sh++) {
                double cur_s_sc = 0.0;
                for (int t = 0; t < N; t++) {
                    int pos = pt_to_z2[t];
                    if (pos % 28 == s) {
                        int c_val = src_ct[pos];
                        int p_val = is_beau ? (sh - c_val + 26) % 26 : (c_val - sh + 26) % 26;
                        int std_c = use_kr ? to_std[p_val] : p_val;
                        cur_s_sc += log_monogram[std_c];
                    }
                }
                if (cur_s_sc > best_s_sc) { best_s_sc = cur_s_sc; best_sh = sh; }
            }
            best_shifts[s] = best_sh;
        }

        int pt[N];
        for (int t = 0; t < N; t++) {
            int pos = pt_to_z2[t];
            int sh = best_shifts[pos % 28];
            int c_val = src_ct[pos];
            int p_val = is_beau ? (sh - c_val + 26) % 26 : (c_val - sh + 26) % 26;
            pt[t] = use_kr ? to_std[p_val] : p_val;
        }

        float sc = score_quadgrams(pt);
        if (sc > best_pair_sc) {
            best_pair_sc = sc;
            best_pair_mode = mode;
            memcpy(best_pair_pt, pt, sizeof(pt));
        }
    }

    *best_mode_out = best_pair_mode;
    memcpy(best_pt_out, best_pair_pt, sizeof(best_pair_pt));
    return best_pair_sc;
}

void keyword_to_order(const char *kw, int *order, int len) {
    int used[32] = {0}, count = 0;
    for (int c = 'A'; c <= 'Z'; c++) {
        for (int i = 0; i < len; i++) {
            if (kw[i] == c && !used[i]) { order[count++] = i; used[i] = 1; }
        }
    }
}

int main() {
    load_models();
    printf("Models loaded. Executing Large-Scale Double Columnar Simulated Annealing on PK9...\n");

    // Anchor: NEEDLEMAKING
    int needle_order[W];
    keyword_to_order("NEEDLEMAKING", needle_order, W);

    // Anchor: GOLDSMITHING
    int gold_order[W];
    keyword_to_order("GOLDSMITHING", gold_order, W);

    float global_best_sc = -999.0f;
    int global_best_o1[W], global_best_o2[W];
    int global_best_pt[N];
    int global_best_mode = 0;

    double t0 = omp_get_wtime();

    #pragma omp parallel
    {
        unsigned int seed = 12345 + omp_get_thread_num() * 33333;
        float local_best_sc = -999.0f;
        int local_best_o1[W], local_best_o2[W];
        int local_best_pt[N];
        int local_best_mode = 0;

        int cur_o1[W], cur_o2[W];
        int cur_pt[N];
        int cur_mode = 0;

        for (int restart = 0; restart < 30; restart++) {
            // Seed from craft anchors
            if (restart % 3 == 0) {
                memcpy(cur_o1, needle_order, sizeof(cur_o1));
                memcpy(cur_o2, gold_order, sizeof(cur_o2));
            } else if (restart % 3 == 1) {
                memcpy(cur_o1, gold_order, sizeof(cur_o1));
                memcpy(cur_o2, needle_order, sizeof(cur_o2));
            } else {
                for (int i = 0; i < W; i++) { cur_o1[i] = i; cur_o2[i] = i; }
                for (int i = W - 1; i > 0; i--) {
                    int j1 = rand_r(&seed) % (i + 1);
                    int t1 = cur_o1[i]; cur_o1[i] = cur_o1[j1]; cur_o1[j1] = t1;
                    int j2 = rand_r(&seed) % (i + 1);
                    int t2 = cur_o2[i]; cur_o2[i] = cur_o2[j2]; cur_o2[j2] = t2;
                }
            }

            float cur_sc = evaluate_pair(cur_o1, cur_o2, &cur_mode, cur_pt);

            float T = 0.8f;
            float T_min = 0.01f;
            float alpha = 0.999f;

            for (int step = 0; step < 400; step++) {
                int next_o1[W], next_o2[W];
                memcpy(next_o1, cur_o1, sizeof(cur_o1));
                memcpy(next_o2, cur_o2, sizeof(cur_o2));

                int target = rand_r(&seed) % 2;
                int *target_o = (target == 0) ? next_o1 : next_o2;

                int a = rand_r(&seed) % W;
                int b = rand_r(&seed) % W;
                int t = target_o[a]; target_o[a] = target_o[b]; target_o[b] = t;

                int next_mode, next_pt[N];
                float next_sc = evaluate_pair(next_o1, next_o2, &next_mode, next_pt);

                float diff = next_sc - cur_sc;
                if (diff > 0.0f || expf(diff / T) > ((float)rand_r(&seed) / RAND_MAX)) {
                    cur_sc = next_sc;
                    memcpy(cur_o1, next_o1, sizeof(cur_o1));
                    memcpy(cur_o2, next_o2, sizeof(cur_o2));
                    cur_mode = next_mode;
                    memcpy(cur_pt, next_pt, sizeof(next_pt));

                    if (cur_sc > local_best_sc) {
                        local_best_sc = cur_sc;
                        memcpy(local_best_o1, cur_o1, sizeof(cur_o1));
                        memcpy(local_best_o2, cur_o2, sizeof(cur_o2));
                        memcpy(local_best_pt, cur_pt, sizeof(cur_pt));
                        local_best_mode = cur_mode;
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
                memcpy(global_best_pt, local_best_pt, sizeof(global_best_pt));
                global_best_mode = local_best_mode;

                char pt_str[N+1];
                for (int i = 0; i < N; i++) pt_str[i] = global_best_pt[i] + 'A';
                pt_str[N] = '\0';

                printf(">>> [Thread %d] NEW BEST SCORE: %.4f | Mode: %d <<<\n",
                       omp_get_thread_num(), global_best_sc, global_best_mode);
                printf("  o1: [");
                for (int i = 0; i < W; i++) printf("%d%s", global_best_o1[i], i==W-1?"":", ");
                printf("]\n");
                printf("  o2: [");
                for (int i = 0; i < W; i++) printf("%d%s", global_best_o2[i], i==W-1?"":", ");
                printf("]\n");
                printf("  PT: %.100s\n\n", pt_str);
            }
        }
    }

    double elapsed = omp_get_wtime() - t0;
    printf("Finished in %.2f seconds.\n", elapsed);
    printf("Global Best: %.4f | Mode %d\n", global_best_sc, global_best_mode);
    char final_pt[N+1];
    for (int i = 0; i < N; i++) final_pt[i] = global_best_pt[i] + 'A';
    final_pt[N] = '\0';
    printf("Plaintext:\n%s\n", final_pt);

    return 0;
}
