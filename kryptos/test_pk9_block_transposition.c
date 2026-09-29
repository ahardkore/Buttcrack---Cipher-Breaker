#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>

#define N 144
#define UNIT 3
#define N_BLOCKS (N / UNIT) // 48

static const char *ALPH = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
static const char *PK9_REAL = "KSYAWFEYYOISZGEUFBLYATAIBYFAQBQYYVDWJKLJXMYIEPIFVHPQNHZGSUHUUDXLEHRHUMALHEGLHXSJMUXGNUIVBXGUJHZRZGUSVHMLSCTSUQXHSUMQQIFUQGKHJGUQGLHDKEWSKAMHIJXD";

static int ct_kr[N];
static int ct_std[N];
static int kr_to_std[26];
static int std_to_kr[26];
static float quad_table[26][26][26][26];

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
    while (fscanf(f, "%s %lf", q, &cnt) == 2) {
        if (strlen(q) == 4) {
            int a = q[0]-'A', b = q[1]-'A', c = q[2]-'A', d = q[3]-'A';
            if (a>=0&&a<26&&b>=0&&b<26&&c>=0&&c<26&&d>=0&&d<26) {
                quad_table[a][b][c][d] = (float)log10((cnt + 0.01) / total);
            }
        }
    }
    fclose(f);

    for (int a = 0; a < 26; a++) {
        kr_to_std[a] = ALPH[a] - 'A';
        std_to_kr[ALPH[a] - 'A'] = a;
    }
    for (int i = 0; i < N; i++) {
        ct_kr[i] = std_to_kr[PK9_REAL[i] - 'A'];
        ct_std[i] = PK9_REAL[i] - 'A';
    }
}

void decrypt_to_z(int mode, const int *q4, const int *q7, int *z) {
    for (int i = 0; i < N; i++) {
        int sh = (q4[i % 4] + q7[i % 7]) % 26;
        if (mode == 0) z[i] = (ct_std[i] - sh + 26) % 26;
        else if (mode == 1) z[i] = (sh - ct_std[i] + 26) % 26;
        else if (mode == 2) {
            int kr_p = (ct_kr[i] - sh + 26) % 26;
            z[i] = kr_to_std[kr_p];
        } else {
            int kr_p = (sh - ct_kr[i] + 26) % 26;
            z[i] = kr_to_std[kr_p];
        }
    }
}

// Decode block transposition:
// In grid of H rows x W cols of blocks (each block is UNIT=3 letters):
// Z contains blocks read column-by-column according to order.
// To decrypt: write columns of blocks into grid[r][order[c]], then read row-by-row.
static inline void decode_block_col(const int *z, int W, int H, const int *order, int *pt) {
    int grid[16][16][UNIT]; // grid[r][c][k]
    int b_idx = 0;
    for (int c_idx = 0; c_idx < W; c_idx++) {
        int col = order[c_idx];
        for (int r = 0; r < H; r++) {
            for (int k = 0; k < UNIT; k++) {
                grid[r][col][k] = z[b_idx * UNIT + k];
            }
            b_idx++;
        }
    }
    int out_idx = 0;
    for (int r = 0; r < H; r++) {
        for (int c = 0; c < W; c++) {
            for (int k = 0; k < UNIT; k++) {
                pt[out_idx++] = grid[r][c][k];
            }
        }
    }
}

static inline float score_quads(const int *pt) {
    float s = 0.0f;
    for (int i = 0; i < N - 3; i++) {
        s += quad_table[pt[i]][pt[i+1]][pt[i+2]][pt[i+3]];
    }
    return s / (N - 3);
}

typedef struct {
    int mode;
    double ll;
    int q4[4];
    int q7[7];
} ClockCand;

int main() {
    load_models();
    printf("Models loaded.\nReading top_clocks.csv...\n");

    FILE *f = fopen("top_clocks.csv", "r");
    if (!f) return 1;
    char line[256];
    fgets(line, sizeof(line), f);

    ClockCand cands[2000];
    int count = 0;
    while (fgets(line, sizeof(line), f) && count < 2000) {
        ClockCand *c = &cands[count];
        char dummy1[32], dummy2[32], dummy3[32], dummy4[32];
        if (sscanf(line, "%d,%lf,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%s,%s,%s,%s",
                   &c->mode, &c->ll,
                   &c->q4[0], &c->q4[1], &c->q4[2], &c->q4[3],
                   &c->q7[0], &c->q7[1], &c->q7[2], &c->q7[3], &c->q7[4], &c->q7[5], &c->q7[6],
                   dummy1, dummy2, dummy3, dummy4) >= 13) {
            count++;
        }
    }
    fclose(f);
    printf("Loaded %d clock candidates.\n", count);

    // Test 1: Width 6 (8 rows x 6 cols of blocks) - All 6! = 720 perms
    printf("\n=== Testing Block Transposition (unit=3), Width 6 (8 rows x 6 cols) ===\n");
    int perms6[720][6];
    int p6_cnt = 0;
    int p6[6] = {0,1,2,3,4,5};
    // Generate all 6!
    void gen_perms6(int idx, int *arr) {
        if (idx == 6) {
            memcpy(perms6[p6_cnt++], arr, 6 * sizeof(int));
            return;
        }
        for (int i = idx; i < 6; i++) {
            int t = arr[idx]; arr[idx] = arr[i]; arr[i] = t;
            gen_perms6(idx + 1, arr);
            t = arr[idx]; arr[idx] = arr[i]; arr[i] = t;
        }
    }
    gen_perms6(0, p6);
    printf("Generated %d permutations of length 6.\n", p6_cnt);

    float best_sc6 = -999.0f;
    int best_cand6 = -1, best_perm6[6], best_pt6[N];

    #pragma omp parallel for schedule(dynamic)
    for (int i = 0; i < count; i++) {
        int z[N];
        decrypt_to_z(cands[i].mode, cands[i].q4, cands[i].q7, z);

        for (int p = 0; p < 720; p++) {
            int pt[N];
            decode_block_col(z, 6, 8, perms6[p], pt);
            float sc = score_quads(pt);

            if (sc > best_sc6) {
                #pragma omp critical
                {
                    if (sc > best_sc6) {
                        best_sc6 = sc;
                        best_cand6 = i;
                        memcpy(best_perm6, perms6[p], 6 * sizeof(int));
                        memcpy(best_pt6, pt, N * sizeof(int));

                        char pt_str[N+1];
                        for (int k = 0; k < N; k++) pt_str[k] = pt[k] + 'A';
                        pt_str[N] = 0;
                        printf("[W=6 unit=3] New Best: %.4f | Mode %d | Cand #%d | Order: [%d,%d,%d,%d,%d,%d]\n  PT: %.80s...\n",
                               sc, cands[i].mode, i,
                               best_perm6[0], best_perm6[1], best_perm6[2], best_perm6[3], best_perm6[4], best_perm6[5],
                               pt_str);
                    }
                }
            }
        }
    }

    printf("\nBest Score for Width 6 (unit=3): %.4f\n", best_sc6);

    // Test 2: Width 8 (6 rows x 8 cols of blocks) - All 8! = 40,320 perms on top 100 cands
    printf("\n=== Testing Block Transposition (unit=3), Width 8 (6 rows x 8 cols) on top 100 cands ===\n");
    // Pre-generate 8!
    int (*perms8)[8] = malloc(40320 * sizeof(*perms8));
    int p8_cnt = 0;
    int p8[8] = {0,1,2,3,4,5,6,7};
    void gen_perms8(int idx, int *arr) {
        if (idx == 8) {
            memcpy(perms8[p8_cnt++], arr, 8 * sizeof(int));
            return;
        }
        for (int i = idx; i < 8; i++) {
            int t = arr[idx]; arr[idx] = arr[i]; arr[i] = t;
            gen_perms8(idx + 1, arr);
            t = arr[idx]; arr[idx] = arr[i]; arr[i] = t;
        }
    }
    gen_perms8(0, p8);
    printf("Generated %d permutations of length 8.\n", p8_cnt);

    float best_sc8 = -999.0f;
    int best_cand8 = -1, best_perm8[8], best_pt8[N];

    #pragma omp parallel for schedule(dynamic)
    for (int i = 0; i < 100; i++) {
        int z[N];
        decrypt_to_z(cands[i].mode, cands[i].q4, cands[i].q7, z);

        for (int p = 0; p < 40320; p++) {
            int pt[N];
            decode_block_col(z, 8, 6, perms8[p], pt);
            float sc = score_quads(pt);

            if (sc > best_sc8) {
                #pragma omp critical
                {
                    if (sc > best_sc8) {
                        best_sc8 = sc;
                        best_cand8 = i;
                        memcpy(best_perm8, perms8[p], 8 * sizeof(int));
                        memcpy(best_pt8, pt, N * sizeof(int));

                        char pt_str[N+1];
                        for (int k = 0; k < N; k++) pt_str[k] = pt[k] + 'A';
                        pt_str[N] = 0;
                        printf("[W=8 unit=3] New Best: %.4f | Mode %d | Cand #%d\n  PT: %.80s...\n",
                               sc, cands[i].mode, i, pt_str);
                    }
                }
            }
        }
    }

    printf("\nBest Score for Width 8 (unit=3): %.4f\n", best_sc8);

    return 0;
}
