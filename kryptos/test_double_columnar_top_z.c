#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>
#include <time.h>

#define N 144

static float quad[26][26][26][26];

void load_quadgrams() {
    for (int a = 0; a < 26; a++)
        for (int b = 0; b < 26; b++)
            for (int c = 0; c < 26; c++)
                for (int d = 0; d < 26; d++)
                    quad[a][b][c][d] = -9.5f;

    FILE *f = fopen("english_quads.tsv", "r");
    if (!f) { printf("Failed to open english_quads.tsv\n"); exit(1); }
    char q[16]; float sc;
    while (fscanf(f, "%s\t%f", q, &sc) == 2) {
        if (strlen(q) == 4) {
            int a = q[0]-'A', b = q[1]-'A', c = q[2]-'A', d = q[3]-'A';
            if (a>=0 && a<26 && b>=0 && b<26 && c>=0 && c<26 && d>=0 && d<26) {
                quad[a][b][c][d] = sc;
            }
        }
    }
    fclose(f);
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

static char Z_cands[16][150];
static int num_cands = 0;

void load_top_z() {
    FILE *f = fopen("top_Z_candidates.txt", "r");
    if (!f) return;
    char line[512];
    while (fgets(line, sizeof(line), f) && num_cands < 6) {
        float dot; int q4[4], q7[7]; char z[150];
        if (sscanf(line, "%f %d %d %d %d %d %d %d %d %d %d %d %s",
                   &dot, &q4[0], &q4[1], &q4[2], &q4[3],
                   &q7[0], &q7[1], &q7[2], &q7[3], &q7[4], &q7[5], &q7[6], z) == 13) {
            strcpy(Z_cands[num_cands++], z);
        }
    }
    fclose(f);
}

int main() {
    load_quadgrams();
    load_top_z();

    int pairs[][2] = {
        {12, 12},
        {9, 9},
        {8, 8},
        {12, 9},
        {9, 12},
        {12, 8},
        {8, 12},
        {16, 9},
        {9, 16},
        {6, 6}
    };
    int num_pairs = sizeof(pairs) / sizeof(pairs[0]);

    printf("Testing Double Columnar Transposition on %d top Z candidates...\n", num_cands);

    for (int c_idx = 0; c_idx < num_cands; c_idx++) {
        const char *Z = Z_cands[c_idx];
        int z_num[N];
        for (int i = 0; i < N; i++) z_num[i] = Z[i] - 'A';

        for (int pi = 0; pi < num_pairs; pi++) {
            int w1 = pairs[pi][0];
            int w2 = pairs[pi][1];
            if (N % w1 != 0 || N % w2 != 0) continue;

            float best_sc = -999.0f;
            char best_pt[N + 1];

            #pragma omp parallel
            {
                unsigned int seed = 42 + omp_get_thread_num() * 10007 + pi * 53 + c_idx * 17;
                int loc_o1[32], loc_o2[32], loc_inter[N], loc_plain[N];
                float loc_best = -999.0f;
                int loc_best_o1[32], loc_best_o2[32];

                #pragma omp for schedule(dynamic, 1)
                for (int r = 0; r < 30; r++) {
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

                    for (int it = 0; it < 8000; it++) {
                        float temp = 0.5f * (1.0f - (float)it / 8000) + 0.002f;
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

                    if (max_sc > loc_best) {
                        loc_best = max_sc;
                        memcpy(loc_best_o1, max_o1, sizeof(int)*w1);
                        memcpy(loc_best_o2, max_o2, sizeof(int)*w2);
                    }
                }

                #pragma omp critical
                {
                    if (loc_best > best_sc) {
                        best_sc = loc_best;
                        int inter[N], plain[N];
                        decrypt_single(z_num, N, w2, loc_best_o2, inter);
                        decrypt_single(inter, N, w1, loc_best_o1, plain);
                        for (int i = 0; i < N; i++) best_pt[i] = 'A' + plain[i];
                        best_pt[N] = '\0';
                    }
                }
            }

            if (best_sc > -5.5f) {
                printf("  HIT! Cand %d (%d, %d): sc=%6.4f | %s\n", c_idx, w1, w2, best_sc, best_pt);
            }
        }
    }
    printf("Double columnar test complete.\n");
    return 0;
}
