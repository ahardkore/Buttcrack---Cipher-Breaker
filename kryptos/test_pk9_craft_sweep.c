#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
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
    while (fscanf(f, "%s %lf", q, &cnt) == 2) {
        if (strlen(q) == 4) total += cnt;
    }
    rewind(f);

    double mono_counts[26] = {0};
    double mono_tot = 0;
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

void keyword_to_order(const char *kw, int *order, int len) {
    int used[32] = {0};
    int count = 0;
    for (int c = 'A'; c <= 'Z'; c++) {
        for (int i = 0; i < len; i++) {
            if (kw[i] == c && !used[i]) {
                order[count++] = i;
                used[i] = 1;
            }
        }
    }
}

void col_decrypt(const int *in, const int *order, int *out, int w, int h) {
    int grid[H][W];
    int idx = 0;
    for (int c_idx = 0; c_idx < w; c_idx++) {
        int col = order[c_idx];
        for (int r = 0; r < h; r++) {
            grid[r][col] = in[idx++];
        }
    }
    idx = 0;
    for (int r = 0; r < h; r++) {
        for (int c = 0; c < w; c++) {
            out[idx++] = grid[r][c];
        }
    }
}

float score_quadgrams(const int *txt) {
    float s = 0.0f;
    for (int i = 0; i < N - 3; i++) {
        s += quad_table[txt[i]][txt[i+1]][txt[i+2]][txt[i+3]];
    }
    return s / (N - 3);
}

static const char *ANCHORS[] = {"METALWORKING", "GOLDSMITHING"};
static const int NUM_ANCHORS = 2;

int main() {
    load_models();

    FILE *fw = fopen("words_12.txt", "r");
    if (!fw) { printf("Cannot open words_12.txt\n"); exit(1); }
    char (*all_words)[16] = malloc(25000 * 16);
    int num_words = 0;
    char line[64];
    while (fgets(line, sizeof(line), fw)) {
        line[strcspn(line, "\r\n")] = '\0';
        if (strlen(line) == 12) {
            for (int i = 0; i < 12; i++) {
                if (line[i] >= 'a' && line[i] <= 'z') line[i] -= 32;
            }
            strcpy(all_words[num_words++], line);
        }
    }
    fclose(fw);
    printf("Loaded %d 12-letter words.\n", num_words);

    // Precompute orders for all dictionary words
    int (*all_orders)[W] = malloc(num_words * sizeof(int[W]));
    for (int i = 0; i < num_words; i++) {
        keyword_to_order(all_words[i], all_orders[i], W);
    }

    printf("Starting Craft Anchor Sweep against all %d dictionary words across both orders (W1, W2) and (W2, W1)...\n", num_words);

    float global_best_sc = -999.0f;
    char best_w1[16] = "", best_w2[16] = "";
    int best_pt[N];
    int best_mode = 0;

    for (int a_idx = 0; a_idx < NUM_ANCHORS; a_idx++) {
        const char *anchor = ANCHORS[a_idx];
        int anchor_order[W];
        keyword_to_order(anchor, anchor_order, W);

        printf("\nEvaluating Anchor: %s (%d/%d)...\n", anchor, a_idx + 1, NUM_ANCHORS);

        #pragma omp parallel
        {
            float local_best_sc = -999.0f;
            char local_w1[16] = "", local_w2[16] = "";
            int local_pt[N];
            int local_mode = 0;

            #pragma omp for schedule(dynamic, 100)
            for (int w_idx = 0; w_idx < num_words; w_idx++) {
                const char *dict_word = all_words[w_idx];
                const int *dict_order = all_orders[w_idx];

                // Test Order 1: (anchor, dict_word)
                // Test Order 2: (dict_word, anchor)
                for (int swap = 0; swap < 2; swap++) {
                    const int *o1 = (swap == 0) ? anchor_order : dict_order;
                    const int *o2 = (swap == 0) ? dict_order : anchor_order;

                    int identity[N];
                    for (int i = 0; i < N; i++) identity[i] = i;
                    int after_dec2[N];
                    col_decrypt(identity, o2, after_dec2, W, H);
                    int pt_to_z2[N];
                    col_decrypt(after_dec2, o1, pt_to_z2, W, H);

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
                                if (cur_s_sc > best_s_sc) {
                                    best_s_sc = cur_s_sc;
                                    best_sh = sh;
                                }
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
                        if (sc > local_best_sc) {
                            local_best_sc = sc;
                            if (swap == 0) {
                                strcpy(local_w1, anchor);
                                strcpy(local_w2, dict_word);
                            } else {
                                strcpy(local_w1, dict_word);
                                strcpy(local_w2, anchor);
                            }
                            memcpy(local_pt, pt, sizeof(pt));
                            local_mode = mode;
                        }
                    }
                }
            }

            #pragma omp critical
            {
                if (local_best_sc > global_best_sc) {
                    global_best_sc = local_best_sc;
                    strcpy(best_w1, local_w1);
                    strcpy(best_w2, local_w2);
                    memcpy(best_pt, local_pt, sizeof(best_pt));
                    best_mode = local_mode;

                    char pt_str[N+1];
                    for (int i = 0; i < N; i++) pt_str[i] = best_pt[i] + 'A';
                    pt_str[N] = '\0';

                    printf("  >>> NEW BEST: %.4f | W1: %s, W2: %s | Mode: %d <<<\n",
                           global_best_sc, best_w1, best_w2, best_mode);
                    printf("  PT: %.100s\n", pt_str);
                }
            }
        }
    }

    printf("\n==================================================\n");
    printf("FINAL BEST RESULT:\n");
    printf("Score: %.4f | W1: %s, W2: %s | Mode: %d\n", global_best_sc, best_w1, best_w2, best_mode);
    char final_pt[N+1];
    for (int i = 0; i < N; i++) final_pt[i] = best_pt[i] + 'A';
    final_pt[N] = '\0';
    printf("Plaintext:\n%s\n", final_pt);
    printf("==================================================\n");

    return 0;
}
