#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>

#define N 504
#define W1 12
#define H1 42
#define W2 42
#define H2 12

static const char *KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
static const char *PK10_CT = "UBINFYJSFQXQVRLJJAJDGBXIWKDMAREZTGSHQWRXCHEPCLYSDNGYRRBTCVOZJYVLYWREJTCDOYVEYCJJVZKRMKTRPGVHRWMJSRCSHXZMJEVQKJYJJAYZKDFQBGRSWXATJMEXKFXAXKSIZXOERFESNVCGCNRHEOBCNCBUPXTJJRCIMDMRUVZWRDRRFXAPGPIGSPLILFIZSTDZYOVQGGDFUFZPUOJPJVWREUVRQIYPCEHGYUZUKWTFXELUNOKBANZFTFRMXZSXXQSBGPCWGXPFSCANSVUYLMTZIRCCCJJPBQAEPWVCDIMLOPOXQEGJKVQIVHEFAPQMVCYSQAFKCTYTPAOOJZCWIPGDPAFTINBFFHVXYEQXCEIDJJOUABBAHSWKHGMLJBXDSQEFBBDLTLJPLZPIPPTRGDRZIZPUPYJODOCSOYCZZWTKYWMBQTFMFEQZWVPQYLJTMEYKYBNOPEPUMHCFJSLFWOISWLKFFABTYFQDTEQBDELIEOZQ";

static const int base_q7[7] = {0, 9, 5, 17, 10, 2, 24};
static const int base_q8[8] = {0, 8, 16, 15, 16, 3, 6, 20};
static const int base_q9[9] = {16, 0, 19, 9, 7, 23, 6, 16, 18};

static float qtable[26][26][26][26];
static char valid_q[26][26][26][26];

static void load_quads(void) {
    for (int a = 0; a < 26; a++)
        for (int b = 0; b < 26; b++)
            for (int c = 0; c < 26; c++)
                for (int d = 0; d < 26; d++) {
                    qtable[a][b][c][d] = -9.5f;
                    valid_q[a][b][c][d] = 0;
                }
    FILE *f = fopen("english_quads.tsv", "r");
    if (!f) { fprintf(stderr, "Missing english_quads.tsv\n"); exit(1); }
    char buf[64];
    while (fgets(buf, sizeof(buf), f)) {
        char q[5]; float sc;
        if (sscanf(buf, "%4s %f", q, &sc) == 2) {
            int a = q[0] - 'A', b = q[1] - 'A', c = q[2] - 'A', d = q[3] - 'A';
            if (a>=0 && a<26 && b>=0 && b<26 && c>=0 && c<26 && d>=0 && d<26) {
                qtable[a][b][c][d] = sc;
                valid_q[a][b][c][d] = 1;
            }
        }
    }
    fclose(f);
}

// Invert/permute columnar transposition:
// Given src of length w*h:
// read columns according to perm[0..w-1], each column of length h,
// write row by row into dst: dst[r * w + col] = src[idx++]
static inline void apply_col_trans(const char *src, int w, int h, const int *perm, char *dst) {
    int idx = 0;
    for (int c_idx = 0; c_idx < w; c_idx++) {
        int col = perm[c_idx];
        for (int r = 0; r < h; r++) {
            dst[r * w + col] = src[idx++];
        }
    }
}

static inline void eval_grid_42(const char *pt, float *out_sc, int *out_def) {
    float sc = 0.0f;
    int def = 0;
    for (int r = 0; r < 12; r++) {
        const char *row = pt + r * 42;
        for (int c = 0; c <= 42 - 4; c++) {
            int a = row[c] - 'A', b = row[c+1] - 'A', c_ch = row[c+2] - 'A', d = row[c+3] - 'A';
            sc += qtable[a][b][c_ch][d];
            if (!valid_q[a][b][c_ch][d]) def++;
        }
    }
    *out_sc = sc / 468.0f;
    *out_def = def;
}

int main(void) {
    load_quads();

    // 1. Decrypt PK10 CT with base clocks
    char Z[N];
    for (int i = 0; i < N; i++) {
        int ct_idx = strchr(KRYPTOS, PK10_CT[i]) - KRYPTOS;
        int shift = (base_q7[i%7] + base_q8[i%8] + base_q9[i%9]) % 26;
        int pt_idx = (ct_idx - shift + 26) % 26;
        Z[i] = KRYPTOS[pt_idx];
    }

    // Base identity for p1 (width 12)
    int p1[W1];
    for (int i = 0; i < W1; i++) p1[i] = i;

    // Base order for p2 (width 42) from record
    int p2[W2] = {
        29, 1, 34, 28, 15, 3, 0, 2, 21, 13, 38, 12, 30, 17, 23, 25, 26, 16,
        20, 37, 39, 7, 31, 33, 32, 36, 22, 35, 27, 10, 9,
        41, 8, 19, 11, 18, 14, 6, 24, 5, 4, 40
    };

    // Evaluate baseline: identity p1 (12x42) -> p2 (42x12)
    char mid[N], pt[N];
    apply_col_trans(Z, W1, H1, p1, mid);
    apply_col_trans(mid, W2, H2, p2, pt);

    float base_sc; int base_def;
    eval_grid_42(pt, &base_sc, &base_def);
    printf("Baseline (Identity P1 x Record P2): Score = %.4f | Defects = %d / 468\n", base_sc, base_def);

    // Optimize P1 (12 columns) using Simulated Annealing
    printf("Optimizing Stage 1 Permutation P1 (12 columns)...\n");
    int best_p1[W1];
    memcpy(best_p1, p1, sizeof(p1));
    float best_sc = base_sc;
    int best_def = base_def;

    #pragma omp parallel
    {
        unsigned int seed = 1234 + omp_get_thread_num() * 777;
        int cur_p1[W1];
        memcpy(cur_p1, p1, sizeof(p1));
        float cur_sc = base_sc;
        int cur_def = base_def;

        int local_best_p1[W1];
        memcpy(local_best_p1, p1, sizeof(p1));
        float local_best_sc = base_sc;
        int local_best_def = base_def;

        int steps = 500000;
        float T_start = 1.0f, T_end = 0.001f;

        for (int step = 0; step < steps; step++) {
            float frac = (float)step / steps;
            float T = T_start * powf(T_end / T_start, frac);

            int next_p1[W1];
            memcpy(next_p1, cur_p1, sizeof(cur_p1));

            // Swap two random elements in P1
            int i = rand_r(&seed) % W1;
            int j = rand_r(&seed) % W1;
            int tmp = next_p1[i];
            next_p1[i] = next_p1[j];
            next_p1[j] = tmp;

            char local_mid[N], local_pt[N];
            apply_col_trans(Z, W1, H1, next_p1, local_mid);
            apply_col_trans(local_mid, W2, H2, p2, local_pt);

            float next_sc; int next_def;
            eval_grid_42(local_pt, &next_sc, &next_def);

            float d_fit = (cur_def - next_def) * 2.0f + (next_sc - cur_sc);
            if (d_fit > 0 || (expf(d_fit / T) > ((float)rand_r(&seed) / RAND_MAX))) {
                memcpy(cur_p1, next_p1, sizeof(cur_p1));
                cur_sc = next_sc;
                cur_def = next_def;

                if (cur_def < local_best_def || (cur_def == local_best_def && cur_sc > local_best_sc)) {
                    local_best_def = cur_def;
                    local_best_sc = cur_sc;
                    memcpy(local_best_p1, cur_p1, sizeof(cur_p1));
                }
            }
        }

        #pragma omp critical
        {
            if (local_best_def < best_def || (local_best_def == best_def && local_best_sc > best_sc)) {
                best_def = local_best_def;
                best_sc = local_best_sc;
                memcpy(best_p1, local_best_p1, sizeof(best_p1));
                printf("[Thread %d] IMPROVEMENT: Score = %.4f | Defects = %d / 468\n",
                       omp_get_thread_num(), best_sc, best_def);
            }
        }
    }

    printf("\n--- RESULT OF STAGE 1 OPTIMIZATION ---\n");
    printf("Best Score: %.4f | Best Defects: %d / 468 (%.1f%% valid)\n",
           best_sc, best_def, (468 - best_def) / 468.0f * 100.0f);
    printf("P1: [");
    for (int i = 0; i < W1; i++) printf("%d%s", best_p1[i], i == W1-1 ? "" : ", ");
    printf("]\n");

    return 0;
}
