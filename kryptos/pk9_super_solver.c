#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <time.h>

const char *ALPH = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
const char *CT = "KSYAWFEYYOISZGEUFBLYATAIBYFAQBQYYVDWJKLJXMYIEPIFVHPQNHZGSUHUUDXLEHRHUMALHEGLHXSJMUXGNUIVBXGUJHZRZGUSVHMLSCTSUQXHSUMQQIFUQGKHJGUQGLHDKEWSKAMHIJXD";

#define N 144

float quad_table[26*26*26*26];

int get_idx(char c) {
    for (int i = 0; i < 26; i++) {
        if (ALPH[i] == c) return i;
    }
    return -1;
}

// Convert letter in ALPH to standard A=0..Z=25 for quadgram lookup
int alph_to_std[26];

void load_quads() {
    for (int i = 0; i < 26*26*26*26; i++) quad_table[i] = -8.0f;
    for (int i = 0; i < 26; i++) {
        alph_to_std[i] = ALPH[i] - 'A';
    }

    FILE *f = fopen("/home/user/english_quads.tsv", "r");
    if (!f) {
        printf("Failed to open quadgram file\n");
        exit(1);
    }
    char line[128];
    while (fgets(line, sizeof(line), f)) {
        char q[5];
        float sc;
        if (sscanf(line, "%4s\t%f", q, &sc) == 2) {
            int c0 = q[0] - 'A';
            int c1 = q[1] - 'A';
            int c2 = q[2] - 'A';
            int c3 = q[3] - 'A';
            if (c0>=0 && c0<26 && c1>=0 && c1<26 && c2>=0 && c2<26 && c3>=0 && c3<26) {
                int code = ((c0 * 26 + c1) * 26 + c2) * 26 + c3;
                quad_table[code] = sc;
            }
        }
    }
    fclose(f);
    printf("Loaded quadgrams.\n");
}

float score_text_std(const int *pt_std) {
    float sc = 0.0f;
    for (int i = 0; i < N - 3; i++) {
        int code = ((pt_std[i] * 26 + pt_std[i+1]) * 26 + pt_std[i+2]) * 26 + pt_std[i+3];
        sc += quad_table[code];
    }
    return sc / (N - 3);
}

// Invert columnar transposition of width W with read order 'order'
// Given M (transposed intermediate text), reconstruct PT
void invert_columnar(const int *M, int W, const int *order, int *PT) {
    int rows = N / W;
    int cols[W][rows];
    int idx = 0;
    for (int c_idx = 0; c_idx < W; c_idx++) {
        int orig_c = order[c_idx];
        for (int r = 0; r < rows; r++) {
            cols[orig_c][r] = M[idx++];
        }
    }
    int p_idx = 0;
    for (int r = 0; r < rows; r++) {
        for (int c = 0; c < W; c++) {
            PT[p_idx++] = cols[c][r];
        }
    }
}

int main() {
    load_quads();
    int c_arr[N];
    for (int i = 0; i < N; i++) c_arr[i] = get_idx(CT[i]);

    int periods[] = {7, 14, 28};
    int widths[] = {6, 8, 9, 12, 16};

    float global_best_score = -999.0f;
    char global_best_pt[N+1];

    srand(1337);

    for (int p_idx = 0; p_idx < 3; p_idx++) {
        int P = periods[p_idx];
        printf("\n======================================================\n");
        printf("SEARCHING PERIOD P = %d\n", P);
        printf("======================================================\n");

        for (int w_idx = 0; w_idx < 5; w_idx++) {
            int W = widths[w_idx];
            int rows = N / W;
            printf("Testing Width W = %d (rows = %d)...\n", W, rows);

            float best_w_score = -999.0f;
            int best_order[W];
            int best_shifts[P];

            // Run 50 random restarts of order hill-climbing
            for (int restart = 0; restart < 50; restart++) {
                int order[W];
                for (int i = 0; i < W; i++) order[i] = i;
                // Shuffle initial order
                for (int i = W - 1; i > 0; i--) {
                    int j = rand() % (i + 1);
                    int tmp = order[i]; order[i] = order[j]; order[j] = tmp;
                }

                int shifts[P];
                for (int j = 0; j < P; j++) shifts[j] = rand() % 26;

                // Alternate between optimizing shifts and optimizing order
                float cur_score = -999.0f;
                int improved = 1;
                int iter = 0;

                while (improved && iter < 10) {
                    improved = 0;
                    iter++;

                    // 1. Optimize shifts via coordinate ascent
                    for (int j = 0; j < P; j++) {
                        int best_s = shifts[j];
                        float best_sc = -999.0f;

                        for (int s = 0; s < 26; s++) {
                            shifts[j] = s;
                            // Decrypt M = (C - shifts) mod 26
                            int M[N];
                            for (int k = 0; k < N; k++) {
                                M[k] = (c_arr[k] - shifts[k % P] + 26) % 26;
                            }
                            // Invert columnar to get PT
                            int PT[N];
                            invert_columnar(M, W, order, PT);
                            // Convert to std alphabet indices
                            int PT_std[N];
                            for (int k = 0; k < N; k++) PT_std[k] = alph_to_std[PT[k]];
                            float sc = score_text_std(PT_std);
                            if (sc > best_sc) {
                                best_sc = sc;
                                best_s = s;
                            }
                        }
                        shifts[j] = best_s;
                        if (best_sc > cur_score) {
                            cur_score = best_sc;
                            improved = 1;
                        }
                    }

                    // 2. Optimize order via pairwise swaps
                    for (int a = 0; a < W; a++) {
                        for (int b = a + 1; b < W; b++) {
                            int tmp = order[a]; order[a] = order[b]; order[b] = tmp;

                            int M[N];
                            for (int k = 0; k < N; k++) {
                                M[k] = (c_arr[k] - shifts[k % P] + 26) % 26;
                            }
                            int PT[N];
                            invert_columnar(M, W, order, PT);
                            int PT_std[N];
                            for (int k = 0; k < N; k++) PT_std[k] = alph_to_std[PT[k]];
                            float sc = score_text_std(PT_std);

                            if (sc > cur_score) {
                                cur_score = sc;
                                improved = 1;
                            } else {
                                // Revert swap
                                tmp = order[a]; order[a] = order[b]; order[b] = tmp;
                            }
                        }
                    }
                }

                if (cur_score > best_w_score) {
                    best_w_score = cur_score;
                    memcpy(best_order, order, sizeof(order));
                    memcpy(best_shifts, shifts, sizeof(shifts));
                }
            }

            printf("  Best score for W=%d: %.3f (restart winner)\n", W, best_w_score);

            if (best_w_score > global_best_score) {
                global_best_score = best_w_score;
                // Reconstruct PT
                int M[N];
                for (int k = 0; k < N; k++) {
                    M[k] = (c_arr[k] - best_shifts[k % P] + 26) % 26;
                }
                int PT[N];
                invert_columnar(M, W, best_order, PT);
                for (int k = 0; k < N; k++) global_best_pt[k] = ALPH[PT[k]];
                global_best_pt[N] = '\0';

                printf(">>> NEW GLOBAL BEST: Period %d, Width %d, Score %.3f\n", P, W, global_best_score);
                printf("    Order: [");
                for (int i = 0; i < W; i++) printf("%d%s", best_order[i], i == W - 1 ? "" : ", ");
                printf("]\n    Shifts: [");
                for (int i = 0; i < P; i++) printf("%d%s", best_shifts[i], i == P - 1 ? "" : ", ");
                printf("]\n    PT: %s\n\n", global_best_pt);
            }
        }
    }

    printf("\n======================================================\n");
    printf("FINAL WINNER: Score %.3f\nPlaintext:\n%s\n", global_best_score, global_best_pt);
    printf("======================================================\n");

    return 0;
}
