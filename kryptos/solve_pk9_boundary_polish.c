#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

#define N 144
#define W1 18
#define H1 8
#define W2 8
#define H2 18

static float quad[26][26][26][26];
static unsigned char valid_quad[26][26][26][26];

void load_quads() {
    memset(valid_quad, 0, sizeof(valid_quad));
    for (int a=0; a<26; a++)
        for (int b=0; b<26; b++)
            for (int c=0; c<26; c++)
                for (int d=0; d<26; d++)
                    quad[a][b][c][d] = -9.5f;

    FILE *f = fopen("english_quads.tsv", "r");
    if (!f) { printf("Cannot open english_quads.tsv\n"); exit(1); }
    char q[16]; float sc;
    int cnt = 0;
    while (fscanf(f, "%s\t%f", q, &sc) == 2) {
        if (strlen(q) == 4) {
            int a = q[0]-'A', b = q[1]-'A', c = q[2]-'A', d = q[3]-'A';
            if (a>=0 && a<26 && b>=0 && b<26 && c>=0 && c<26 && d>=0 && d<26) {
                quad[a][b][c][d] = sc;
                valid_quad[a][b][c][d] = 1;
                cnt++;
            }
        }
    }
    fclose(f);
}

static const char *KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
static const char *PK9_RAW = "KSYAWFEYYOISZGEUFBLYATAIBYFAQBQYYVDWJKLJXMYIEPIFVHPQNHZGSUHUUDXLEHRHUMALHEGLHXSJMUXGNUIVBXGUJHZRZGUSVHMLSCTSUQXHSUMQQIFUQGKHJGUQGLHDKEWSKAMHIJXD";

static int ct_kr[N];
static int k2std[26];
static int hpos[256];
static const int p2[W2] = {7, 0, 5, 2, 4, 3, 6, 1};

void init_tables() {
    for (int i = 0; i < 26; i++) {
        hpos[(unsigned char)KRYPTOS[i]] = i;
        k2std[i] = KRYPTOS[i] - 'A';
    }
    for (int i = 0; i < N; i++) ct_kr[i] = hpos[(unsigned char)PK9_RAW[i]];
}

static inline void invert_col(const int *src, int w, int h, const int *perm, int *dst) {
    int idx = 0;
    for (int c_idx = 0; c_idx < w; c_idx++) {
        int col = perm[c_idx];
        for (int r = 0; r < h; r++) {
            dst[r * w + col] = src[idx++];
        }
    }
}

int main() {
    load_quads();
    init_tables();

    // Base shifts
    int base_s[28] = {25, 15, 13, 18, 19, 6, 6, 16, 9, 25, 8, 25, 14, 7, 16, 10, 7, 8, 0, 6, 21, 3, 22, 5, 0, 10, 7, 6};

    // Candidate shifts for s0, s5, s17 that avoid rare letters:
    int cand_s0[] = {25, 5, 9, 11, 13, 14, 15, 18, 19, 23, 24};
    int cand_s5[] = {6, 1, 3, 5, 7, 9, 10, 15, 19};
    int cand_s17[] = {8, 23, 0, 2, 3, 6, 7, 11, 22, 25};

    int n0 = sizeof(cand_s0)/sizeof(cand_s0[0]);
    int n5 = sizeof(cand_s5)/sizeof(cand_s5[0]);
    int n17 = sizeof(cand_s17)/sizeof(cand_s17[0]);

    // Solid core columns (10 columns, indices 4 to 13):
    int core_cols[10] = {6, 0, 17, 9, 13, 12, 5, 4, 2, 10};

    // Left 4 columns:
    int left_cands[4] = {15, 1, 3, 7};
    // Right 4 columns:
    int right_cands[4] = {11, 14, 16, 8};

    int perm4[24][4];
    int p_cnt = 0;
    int a[4] = {0, 1, 2, 3};
    // Generate all 24 perms of 4 elements:
    for (int i=0; i<4; i++)
        for (int j=0; j<4; j++) if (j!=i)
            for (int k=0; k<4; k++) if (k!=i && k!=j)
                for (int l=0; l<4; l++) if (l!=i && l!=j && l!=k) {
                    perm4[p_cnt][0] = i; perm4[p_cnt][1] = j; perm4[p_cnt][2] = k; perm4[p_cnt][3] = l;
                    p_cnt++;
                }

    printf("======================================================================\n");
    printf("PK9 Boundary Polish: 24 Left x 24 Right x %d Shift Combos\n", n0 * n5 * n17);
    printf("Evaluating full continuous text across all 141 quadgrams...\n");
    printf("======================================================================\n\n");

    float global_best_sc = -999.0f;
    int global_min_def = 999;
    int best_s0 = -1, best_s5 = -1, best_s17 = -1;
    int best_left[4], best_right[4];

    // Evaluate for s0, s5, s17:
    for (int i0 = 0; i0 < n0; i0++) {
        for (int i5 = 0; i5 < n5; i5++) {
            for (int i17 = 0; i17 < n17; i17++) {
                int s[28];
                memcpy(s, base_s, sizeof(s));
                s[0] = cand_s0[i0];
                s[5] = cand_s5[i5];
                s[17] = cand_s17[i17];

                int Z[N], mid[N];
                for (int t = 0; t < N; t++) {
                    int shift = s[t % 28];
                    int p_kr = (ct_kr[t] - shift + 26) % 26;
                    Z[t] = k2std[p_kr];
                }
                invert_col(Z, W2, H2, p2, mid);

                for (int lp = 0; lp < 24; lp++) {
                    int left[4];
                    for (int k=0; k<4; k++) left[k] = left_cands[perm4[lp][k]];

                    for (int rp = 0; rp < 24; rp++) {
                        int right[4];
                        for (int k=0; k<4; k++) right[k] = right_cands[perm4[rp][k]];

                        // Build full p1:
                        int p1[18];
                        for (int k=0; k<4; k++) p1[k] = left[k];
                        for (int k=0; k<10; k++) p1[4+k] = core_cols[k];
                        for (int k=0; k<4; k++) p1[14+k] = right[k];

                        // Build continuous text:
                        int full[N];
                        int idx = 0;
                        for (int r = 0; r < 8; r++) {
                            for (int c = 0; c < 18; c++) {
                                full[idx++] = mid[p1[c] * 8 + r];
                            }
                        }

                        float sc = 0.0f;
                        int def = 0;
                        for (int i = 0; i < N - 3; i++) {
                            int ca = full[i], cb = full[i+1], cc = full[i+2], cd = full[i+3];
                            sc += quad[ca][cb][cc][cd];
                            if (!valid_quad[ca][cb][cc][cd]) def++;
                        }
                        sc /= (N - 3);

                        if (def < global_min_def || (def == global_min_def && sc > global_best_sc)) {
                            global_min_def = def;
                            global_best_sc = sc;
                            best_s0 = s[0]; best_s5 = s[5]; best_s17 = s[17];
                            memcpy(best_left, left, sizeof(left));
                            memcpy(best_right, right, sizeof(right));

                            printf("New best: Defects=%2d/141 (%.1f%% valid) | Score=%.4f | s0=%2d, s5=%2d, s17=%2d | L=[%d,%d,%d,%d], R=[%d,%d,%d,%d]\n",
                                   global_min_def, (1.0f - (float)global_min_def/141.0f)*100.0f, global_best_sc,
                                   best_s0, best_s5, best_s17,
                                   best_left[0], best_left[1], best_left[2], best_left[3],
                                   best_right[0], best_right[1], best_right[2], best_right[3]);
                        }
                    }
                }
            }
        }
    }

    printf("\n======================================================================\n");
    printf("GLOBAL OPTIMUM: Defects=%d/141 (%.1f%% valid) | Score=%.4f\n",
           global_min_def, (1.0f - (float)global_min_def/141.0f)*100.0f, global_best_sc);
    printf("s0=%d, s5=%d, s17=%d\n", best_s0, best_s5, best_s17);
    printf("======================================================================\n\n");

    // Print resulting plaintext:
    int s[28];
    memcpy(s, base_s, sizeof(s));
    s[0] = best_s0; s[5] = best_s5; s[17] = best_s17;

    int Z[N], mid[N], p1[18];
    for (int t = 0; t < N; t++) {
        int shift = s[t % 28];
        int p_kr = (ct_kr[t] - shift + 26) % 26;
        Z[t] = k2std[p_kr];
    }
    invert_col(Z, W2, H2, p2, mid);

    for (int k=0; k<4; k++) p1[k] = best_left[k];
    for (int k=0; k<10; k++) p1[4+k] = core_cols[k];
    for (int k=0; k<4; k++) p1[14+k] = best_right[k];

    printf("Full Plaintext Grid (8 rows x 18 cols):\n");
    for (int r = 0; r < 8; r++) {
        printf("  Row %d: ", r);
        for (int c = 0; c < 18; c++) putchar('A' + mid[p1[c] * 8 + r]);
        putchar('\n');
    }

    printf("\nContinuous Text (144 chars):\n  ");
    for (int r = 0; r < 8; r++) {
        for (int c = 0; c < 18; c++) putchar('A' + mid[p1[c] * 8 + r]);
    }
    putchar('\n');

    return 0;
}
