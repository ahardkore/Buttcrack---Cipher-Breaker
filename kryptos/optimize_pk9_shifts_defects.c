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

    int base_s[28] = {25, 15, 13, 18, 19, 6, 6, 16, 9, 25, 8, 25, 14, 7, 16, 10, 7, 23, 0, 6, 21, 3, 22, 5, 0, 10, 7, 6};
    int cand_s0[] = {25, 5, 9, 11, 13, 14, 15, 18, 19, 23, 24};
    int cand_s5[] = {6, 1, 3, 5, 7, 9, 10, 15, 19};
    int cand_s17[] = {23, 0, 2, 3, 6, 7, 8, 11, 22, 25};

    int n0 = sizeof(cand_s0)/sizeof(cand_s0[0]);
    int n5 = sizeof(cand_s5)/sizeof(cand_s5[0]);
    int n17 = sizeof(cand_s17)/sizeof(cand_s17[0]);

    int p1[W1] = {15, 1, 3, 7, 6, 0, 17, 9, 13, 12, 5, 4, 2, 10, 11, 8, 16, 14};
    int p2[W2] = {7, 0, 5, 2, 4, 3, 6, 1};

    float best_sc = -999.0f;
    int best_s0 = -1, best_s5 = -1, best_s17 = -1;
    int min_defects = 999;

    printf("Sweeping %d combinations of (s0, s5, s17)...\n", n0 * n5 * n17);

    for (int i0 = 0; i0 < n0; i0++) {
        for (int i5 = 0; i5 < n5; i5++) {
            for (int i17 = 0; i17 < n17; i17++) {
                int s[28];
                memcpy(s, base_s, sizeof(s));
                s[0] = cand_s0[i0];
                s[5] = cand_s5[i5];
                s[17] = cand_s17[i17];

                int Z[N], mid[N], pt[N];
                for (int t = 0; t < N; t++) {
                    int shift = s[t % 28];
                    int p_kr = (ct_kr[t] - shift + 26) % 26;
                    Z[t] = k2std[p_kr];
                }

                invert_col(Z, W2, H2, p2, mid);
                for (int r = 0; r < 8; r++) {
                    for (int c = 0; c < 18; c++) {
                        pt[r * 18 + c] = mid[p1[c] * 8 + r];
                    }
                }

                float sc = 0.0f;
                int defects = 0;
                for (int r = 0; r < 8; r++) {
                    for (int c = 0; c < 15; c++) {
                        int idx = r * 18 + c;
                        int a = pt[idx], b = pt[idx+1], c_char = pt[idx+2], d = pt[idx+3];
                        sc += quad[a][b][c_char][d];
                        if (!valid_quad[a][b][c_char][d]) defects++;
                    }
                }
                sc /= 120.0f;

                if (defects < min_defects || (defects == min_defects && sc > best_sc)) {
                    min_defects = defects;
                    best_sc = sc;
                    best_s0 = s[0];
                    best_s5 = s[5];
                    best_s17 = s[17];
                    printf("New best: s0=%2d, s5=%2d, s17=%2d | defects=%2d/120 | score=%.4f\n",
                           best_s0, best_s5, best_s17, min_defects, best_sc);
                }
            }
        }
    }

    printf("\n=== GLOBAL OPTIMUM ===\n");
    printf("s0=%d, s5=%d, s17=%d | min defects=%d/120 | score=%.4f\n",
           best_s0, best_s5, best_s17, min_defects, best_sc);

    // Print resulting plaintext
    int s[28];
    memcpy(s, base_s, sizeof(s));
    s[0] = best_s0; s[5] = best_s5; s[17] = best_s17;
    int Z[N], mid[N], pt[N];
    for (int t = 0; t < N; t++) {
        int shift = s[t % 28];
        int p_kr = (ct_kr[t] - shift + 26) % 26;
        Z[t] = k2std[p_kr];
    }
    invert_col(Z, W2, H2, p2, mid);
    for (int r = 0; r < 8; r++) {
        for (int c = 0; c < 18; c++) {
            pt[r * 18 + c] = mid[p1[c] * 8 + r];
        }
    }

    printf("Plaintext:\n");
    for (int r = 0; r < 8; r++) {
        printf("  Row %d: ", r);
        for (int c = 0; c < 18; c++) putchar('A' + pt[r * 18 + c]);
        putchar('\n');
    }
    return 0;
}
