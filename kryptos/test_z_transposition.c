#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>
#include <time.h>

#define N 144
static const char Z[N + 1] = "MCHEHAIEMEVVETHHLSQBRSLAKBLMCFINZHIINFUANVEOLDOXGLVZLLOABOSGRICSICMEGWTHTMEKREARLLZMEZELTNEEEZLTNEREEIRKRLZSLSTBEMHHTREZEVRSXMEGWTVKSLNEALVEELARVEEXMEZ";

static float quad[26][26][26][26];

void load_quadgrams(const char *path) {
    for (int a = 0; a < 26; a++)
        for (int b = 0; b < 26; b++)
            for (int c = 0; c < 26; c++)
                for (int d = 0; d < 26; d++)
                    quad[a][b][c][d] = -10.0f;

    FILE *f = fopen(path, "r");
    if (!f) { printf("Failed to open %s\n", path); exit(1); }
    char line[128];
    double total = 0;
    long long counts[26][26][26][26] = {0};

    while (fgets(line, sizeof(line), f)) {
        char q[5]; long long cnt;
        if (sscanf(line, "%4s %lld", q, &cnt) == 2) {
            int a = q[0] - 'A', b = q[1] - 'A', c = q[2] - 'A', d = q[3] - 'A';
            if (a>=0 && a<26 && b>=0 && b<26 && c>=0 && c<26 && d>=0 && d<26) {
                counts[a][b][c][d] = cnt;
                total += cnt;
            }
        }
    }
    fclose(f);

    float log_tot = log10(total);
    for (int a = 0; a < 26; a++)
        for (int b = 0; b < 26; b++)
            for (int c = 0; c < 26; c++)
                for (int d = 0; d < 26; d++) {
                    if (counts[a][b][c][d] > 0)
                        quad[a][b][c][d] = log10((double)counts[a][b][c][d]) - log_tot;
                    else
                        quad[a][b][c][d] = -9.5f;
                }
}

static inline void decrypt_single(const int *ct, int n, int width, const int *order, int *out) {
    int h = n / width;
    int k = 0;
    for (int m = 0; m < width; m++) {
        int col = order[m];
        for (int r = 0; r < h; r++) {
            out[r * width + col] = ct[k++];
        }
    }
}

static inline float score_text(const int *txt, int n) {
    float sc = 0.0f;
    for (int i = 0; i < n - 3; i++) {
        sc += quad[txt[i]][txt[i+1]][txt[i+2]][txt[i+3]];
    }
    return sc / (n - 3);
}

int main() {
    load_quadgrams("/home/user/buttcrack/src/buttcrack/data/english_quadgrams.txt");

    int z_num[N];
    for (int i = 0; i < N; i++) z_num[i] = Z[i] - 'A';

    int pairs[][2] = {
        {12, 12}, {9, 9}, {8, 8}, {12, 9}, {9, 12}, {16, 9}, {9, 16}, {18, 8}, {8, 18}, {6, 6}
    };
    int num_pairs = sizeof(pairs) / sizeof(pairs[0]);

    printf("=== Testing Double Columnar on (5, 7) de-substituted stream Z ===\n");

    for (int p_idx = 0; p_idx < num_pairs; p_idx++) {
        int w1 = pairs[p_idx][0], w2 = pairs[p_idx][1];
        if (N % w1 != 0 || N % w2 != 0) continue;

        float global_best = -999.0f;
        char best_pt[N + 1];

        #pragma omp parallel
        {
            unsigned int seed = 12345 + omp_get_thread_num() * 10007;
            int loc_o1[32], loc_o2[32], loc_inter[N], loc_plain[N];
            float loc_best = -999.0f;

            #pragma omp for schedule(dynamic, 1)
            for (int r = 0; r < 64; r++) {
                for (int i = 0; i < w1; i++) loc_o1[i] = i;
                for (int i = 0; i < w2; i++) loc_o2[i] = i;
                for (int i = w1 - 1; i > 0; i--) {
                    int j = rand_r(&seed) % (i + 1);
                    int tmp = loc_o1[i]; loc_o1[i] = loc_o1[j]; loc_o1[j] = tmp;
                }
                for (int i = w2 - 1; i > 0; i--) {
                    int j = rand_r(&seed) % (i + 1);
                    int tmp = loc_o2[i]; loc_o2[i] = loc_o2[j]; loc_o2[j] = tmp;
                }

                decrypt_single(z_num, N, w2, loc_o2, loc_inter);
                decrypt_single(loc_inter, N, w1, loc_o1, loc_plain);
                float cur_sc = score_text(loc_plain, N);
                float max_sc = cur_sc;
                int max_o1[32], max_o2[32];
                memcpy(max_o1, loc_o1, sizeof(int)*w1);
                memcpy(max_o2, loc_o2, sizeof(int)*w2);

                for (int it = 0; it < 15000; it++) {
                    float temp = 0.5f * (1.0f - (float)it / 15000) + 0.002f;
                    int mut_first = (rand_r(&seed) % (w1 + w2)) < w1;
                    int *mut_o = mut_first ? loc_o1 : loc_o2;
                    int w_cur = mut_first ? w1 : w2;
                    int a = rand_r(&seed) % w_cur;
                    int b = rand_r(&seed) % w_cur;
                    if (a == b) continue;
                    int tmp = mut_o[a]; mut_o[a] = mut_o[b]; mut_o[b] = tmp;

                    decrypt_single(z_num, N, w2, loc_o2, loc_inter);
                    decrypt_single(loc_inter, N, w1, loc_o1, loc_plain);
                    float sc = score_text(loc_plain, N);

                    float diff = sc - cur_sc;
                    if (diff >= 0 || ((float)rand_r(&seed)/RAND_MAX) < expf(diff / temp)) {
                        cur_sc = sc;
                        if (sc > max_sc) {
                            max_sc = sc;
                            memcpy(max_o1, loc_o1, sizeof(int)*w1);
                            memcpy(max_o2, loc_o2, sizeof(int)*w2);
                        }
                    } else {
                        mut_o[b] = mut_o[a]; mut_o[a] = tmp;
                    }
                }

                if (max_sc > loc_best) loc_best = max_sc;
            }

            #pragma omp critical
            {
                if (loc_best > global_best) global_best = loc_best;
            }
        }

        printf("Pair (%2d, %2d): Best Score = %.4f\n", w1, w2, global_best);
    }

    return 0;
}
