#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <omp.h>

#define N 144
const char *ALPH = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
const char *CT = "KSYAWFEYYOISZGEUFBLYATAIBYFAQBQYYVDWJKLJXMYIEPIFVHPQNHZGSUHUUDXLEHRHUMALHEGLHXSJMUXGNUIVBXGUJHZRZGUSVHMLSCTSUQXHSUMQQIFUQGKHJGUQGLHDKEWSKAMHIJXD";
const int s13[7] = {0, 2, 9, 10, 10, 6, 7};

float quad_table[26*26*26*26];
int alph_to_std[26];

int get_idx(char c) {
    for (int i = 0; i < 26; i++) {
        if (ALPH[i] == c) return i;
    }
    return -1;
}

void load_quads() {
    for (int i = 0; i < 26*26*26*26; i++) quad_table[i] = -8.0f;
    for (int i = 0; i < 26; i++) alph_to_std[i] = ALPH[i] - 'A';

    FILE *f = fopen("/home/user/english_quads.tsv", "r");
    if (!f) exit(1);
    char line[128];
    while (fgets(line, sizeof(line), f)) {
        char q[5];
        float sc;
        if (sscanf(line, "%4s\t%f", q, &sc) == 2) {
            int c0 = q[0] - 'A', c1 = q[1] - 'A', c2 = q[2] - 'A', c3 = q[3] - 'A';
            if (c0>=0 && c0<26 && c1>=0 && c1<26 && c2>=0 && c2<26 && c3>=0 && c3<26) {
                int code = ((c0 * 26 + c1) * 26 + c2) * 26 + c3;
                quad_table[code] = sc;
            }
        }
    }
    fclose(f);
}

int main() {
    load_quads();
    int c_arr[N];
    for (int i = 0; i < N; i++) c_arr[i] = get_idx(CT[i]);

    printf("Evaluating all 58,492,928 arbitrary (5, 7) sum-clock combinations...\n");

    float global_best_sc = -999.0f;
    int best_mask = -1;
    int best_k5[5];
    int best_pt[N];

    #pragma omp parallel for schedule(dynamic, 1)
    for (int mask = 0; mask < 128; mask++) {
        int k7[7];
        for (int i = 0; i < 7; i++) {
            k7[i] = s13[i] + ((mask & (1 << i)) ? 13 : 0);
        }

        float local_best_sc = -999.0f;
        int local_k5[5];
        int local_pt[N];

        for (int a1 = 0; a1 < 26; a1++) {
            for (int a2 = 0; a2 < 26; a2++) {
                for (int a3 = 0; a3 < 26; a3++) {
                    for (int a4 = 0; a4 < 26; a4++) {
                        int k5[5] = {0, a1, a2, a3, a4};

                        // Fast prune on first 15 chars
                        float sc_quick = 0.0f;
                        int pt_quick[15];
                        for (int k = 0; k < 15; k++) {
                            int shift = (k5[k % 5] + k7[k % 7]) % 26;
                            int p = (c_arr[k] - shift + 26) % 26;
                            pt_quick[k] = alph_to_std[p];
                        }
                        for (int k = 0; k < 12; k++) {
                            int code = ((pt_quick[k] * 26 + pt_quick[k+1]) * 26 + pt_quick[k+2]) * 26 + pt_quick[k+3];
                            sc_quick += quad_table[code];
                        }
                        sc_quick /= 12;
                        if (sc_quick < -6.1f) continue;

                        // Full score
                        float sc = 0.0f;
                        int pt[N];
                        for (int k = 0; k < N; k++) {
                            int shift = (k5[k % 5] + k7[k % 7]) % 26;
                            int p = (c_arr[k] - shift + 26) % 26;
                            pt[k] = alph_to_std[p];
                        }
                        for (int k = 0; k < N - 3; k++) {
                            int code = ((pt[k] * 26 + pt[k+1]) * 26 + pt[k+2]) * 26 + pt[k+3];
                            sc += quad_table[code];
                        }
                        sc /= (N - 3);

                        if (sc > local_best_sc) {
                            local_best_sc = sc;
                            memcpy(local_k5, k5, sizeof(k5));
                            memcpy(local_pt, pt, sizeof(pt));
                        }
                    }
                }
            }
        }

        #pragma omp critical
        {
            if (local_best_sc > global_best_sc) {
                global_best_sc = local_best_sc;
                best_mask = mask;
                memcpy(best_k5, local_k5, sizeof(best_k5));
                memcpy(best_pt, local_pt, sizeof(best_pt));
                printf("New Best! Mask=%3d, k5=[%d,%d,%d,%d,%d], Score=%.4f\n",
                       mask, best_k5[0], best_k5[1], best_k5[2], best_k5[3], best_k5[4], local_best_sc);
                printf("PT: ");
                for (int k = 0; k < 60; k++) printf("%c", best_pt[k] + 'A');
                printf("...\n");
            }
        }
    }

    printf("\nFinished. Global Best Score: %.4f (Mask %d)\n", global_best_sc, best_mask);
    printf("Best k5: [%d, %d, %d, %d, %d]\n", best_k5[0], best_k5[1], best_k5[2], best_k5[3], best_k5[4]);
    printf("PT: ");
    for (int k = 0; k < N; k++) printf("%c", best_pt[k] + 'A');
    printf("\n");
    return 0;
}
