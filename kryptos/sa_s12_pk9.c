#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <time.h>
#include <omp.h>

#define N 144
#define W 12

static const char *ALPH = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
static const char *CT = "KSYAWFEYYOISZGEUFBLYATAIBYFAQBQYYVDWJKLJXMYIEPIFVHPQNHZGSUHUUDXLEHRHUMALHEGLHXSJMUXGNUIVBXGUJHZRZGUSVHMLSCTSUQXHSUMQQIFUQGKHJGUQGLHDKEWSKAMHIJXD";
static const int q7[7] = {0, 2, 9, 23, 23, 6, 20};

static float quadgrams[26][26][26][26];

void load_quads() {
    float floor_val = -8.728227f;
    for (int i=0; i<26; i++)
        for (int j=0; j<26; j++)
            for (int k=0; k<26; k++)
                for (int l=0; l<26; l++)
                    quadgrams[i][j][k][l] = floor_val;

    FILE *f = fopen("buttcrack/src/buttcrack/data/english_quadgrams.txt", "r");
    if (!f) f = fopen("english_quadgrams.txt", "r");
    char line[64];
    double total = 5348433.0;
    while (fgets(line, sizeof(line), f)) {
        char g[5]; double cnt;
        if (sscanf(line, "%4s %lf", g, &cnt) == 2) {
            int a = g[0]-'A', b = g[1]-'A', c = g[2]-'A', d = g[3]-'A';
            if (a>=0&&a<26&&b>=0&&b<26&&c>=0&&c<26&&d>=0&&d<26) {
                quadgrams[a][b][c][d] = (float)log10(cnt / total);
            }
        }
    }
    fclose(f);
}

// Score a permutation o1 on the 12 blocks of 12
static inline float eval_o1(const int grid[W][W], const int *inv_o1) {
    float sc = 0;
    for (int m = 0; m < W; m++) {
        int r[W];
        for (int c = 0; c < W; c++) {
            r[c] = grid[m][inv_o1[c]];
        }
        for (int c = 0; c < W - 3; c++) {
            sc += quadgrams[r[c]][r[c+1]][r[c+2]][r[c+3]];
        }
    }
    return sc / (W * (W - 3));
}

// Also test transposed grid (if blocks are columns)
static inline float eval_o1_trans(const int grid[W][W], const int *inv_o1) {
    float sc = 0;
    for (int m = 0; m < W; m++) {
        int r[W];
        for (int c = 0; c < W; c++) {
            r[c] = grid[inv_o1[c]][m];
        }
        for (int c = 0; c < W - 3; c++) {
            sc += quadgrams[r[c]][r[c+1]][r[c+2]][r[c+3]];
        }
    }
    return sc / (W * (W - 3));
}

static inline unsigned int xorshift32(unsigned int *state) {
    unsigned int x = *state;
    x ^= x << 13;
    x ^= x >> 17;
    x ^= x << 5;
    *state = x;
    return x;
}

int main() {
    load_quads();

    int k2i[256];
    for (int i=0; i<256; i++) k2i[i] = -1;
    for (int i=0; i<26; i++) k2i[(int)ALPH[i]] = i;

    int ct_k[N];
    for (int i=0; i<N; i++) ct_k[i] = k2i[(int)CT[i]];

    printf("Starting S12 search across 16 parities and grid orientations...\n");

    for (int parity = 0; parity < 16; parity++) {
        int q4_bits[4];
        for (int b=0; b<4; b++) q4_bits[b] = ((parity >> b) & 1) * 13;

        int grid[W][W];
        for (int i=0; i<N; i++) {
            int shift = (q7[i % 7] + q4_bits[i % 4]) % 26;
            int z_kr = (ct_k[i] - shift + 26) % 26;
            char ch = ALPH[z_kr];
            grid[i / W][i % W] = ch - 'A';
        }

        // Run SA for both Normal and Transposed
        for (int trans = 0; trans < 2; trans++) {
            float best_sc = -1e9f;
            int best_perm[W];

            #pragma omp parallel
            {
                unsigned int seed = (unsigned int)(time(NULL) ^ (omp_get_thread_num() * 777777 + parity * 101));
                float local_best = -1e9f;
                int local_perm[W];

                #pragma omp for
                for (int run = 0; run < 200; run++) {
                    int p[W];
                    for (int i=0; i<W; i++) p[i] = i;
                    // shuffle
                    for (int i=W-1; i>0; i--) {
                        int j = xorshift32(&seed) % (i + 1);
                        int tmp = p[i]; p[i] = p[j]; p[j] = tmp;
                    }

                    float cur_sc = trans ? eval_o1_trans(grid, p) : eval_o1(grid, p);
                    float run_best = cur_sc;
                    int run_perm[W];
                    memcpy(run_perm, p, sizeof(p));

                    float temp = 1.0f;
                    float cooling = 0.9999f;
                    for (int step = 0; step < 50000; step++) {
                        int i = xorshift32(&seed) % W;
                        int j = xorshift32(&seed) % W;
                        while (i == j) j = xorshift32(&seed) % W;

                        // swap
                        int tmp = p[i]; p[i] = p[j]; p[j] = tmp;
                        float new_sc = trans ? eval_o1_trans(grid, p) : eval_o1(grid, p);
                        float delta = new_sc - cur_sc;

                        if (delta > 0 || ((float)xorshift32(&seed) / 4294967296.0f) < expf(delta / temp)) {
                            cur_sc = new_sc;
                            if (cur_sc > run_best) {
                                run_best = cur_sc;
                                memcpy(run_perm, p, sizeof(p));
                            }
                        } else {
                            // revert
                            tmp = p[i]; p[i] = p[j]; p[j] = tmp;
                        }
                        temp *= cooling;
                    }

                    if (run_best > local_best) {
                        local_best = run_best;
                        memcpy(local_perm, run_perm, sizeof(p));
                    }
                }

                #pragma omp critical
                {
                    if (local_best > best_sc) {
                        best_sc = local_best;
                        memcpy(best_perm, local_perm, sizeof(local_perm));
                    }
                }
            }

            if (best_sc > -6.0f) {
                printf(">>> HIT! Parity %2d, Trans %d: Score = %.4f <<<\n  Perm: ", parity, trans, best_sc);
                for (int i=0; i<W; i++) printf("%d ", best_perm[i]);
                printf("\n");
                for (int m=0; m<W; m++) {
                    char row[W+1];
                    for (int c=0; c<W; c++) {
                        int val = trans ? grid[best_perm[c]][m] : grid[m][best_perm[c]];
                        row[c] = val + 'A';
                    }
                    row[W] = 0;
                    printf("    Row %2d: %s\n", m, row);
                }
            } else {
                printf("Parity %2d, Trans %d: Best = %.4f\n", parity, trans, best_sc);
            }
        }
    }
    return 0;
}
