#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>

#define N 144

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

static inline float score_quads(const int *pt) {
    float s = 0.0f;
    for (int i = 0; i < N - 3; i++) {
        s += quad_table[pt[i]][pt[i+1]][pt[i+2]][pt[i+3]];
    }
    return s / (N - 3);
}

// AMSCO Decryption:
// Grid has H rows and W cols.
// Pattern starts with start_pat (1 or 2).
// In row r, cell c has length:
// len(r, c) = ( (start_pat == 1 ? (r + c) : (r + c + 1)) % 2 ) + 1
// In encryption: plaintext is written row-by-row into cells.
// Then columns are read top-to-bottom in order: col = order[c_idx].
// In decryption:
// 1. Compute how many letters are in each column: col_len[c] = sum_r len(r, c).
// 2. Distribute z into columns according to order:
//    Column c = order[c_idx] takes the next col_len[c] characters of z.
// 3. Read out the grid row-by-row to reconstruct plaintext.
void decode_amsco(const int *z, int W, int H, int start_pat, const int *order, int *pt) {
    int cell_len[32][32];
    int col_tot[32] = {0};

    for (int r = 0; r < H; r++) {
        for (int c = 0; c < W; c++) {
            int l = (start_pat == 1) ? ((r + c) % 2 + 1) : ((r + c + 1) % 2 + 1);
            cell_len[r][c] = l;
            col_tot[c] += l;
        }
    }

    // Distribute z into columns
    int col_chars[32][64];
    int z_idx = 0;
    for (int c_idx = 0; c_idx < W; c_idx++) {
        int col = order[c_idx];
        for (int i = 0; i < col_tot[col]; i++) {
            col_chars[col][i] = z[z_idx++];
        }
    }

    // Read row-by-row
    int col_read_ptr[32] = {0};
    int pt_idx = 0;
    for (int r = 0; r < H; r++) {
        for (int c = 0; c < W; c++) {
            int l = cell_len[r][c];
            for (int k = 0; k < l; k++) {
                pt[pt_idx++] = col_chars[c][col_read_ptr[c]++];
            }
        }
    }
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

    // Test 1: Width 6 (H = 16) - All 6! = 720 perms, start_pat in {1, 2}
    printf("\n=== Testing AMSCO Transposition for Width 6 (16 rows x 6 cols) ===\n");
    int perms6[720][6];
    int p6_cnt = 0;
    int p6[6] = {0,1,2,3,4,5};
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

    float best_sc6 = -999.0f;
    int best_cand6 = -1, best_perm6[6], best_pat6 = 1;
    char best_pt6[N+1];

    double t0 = omp_get_wtime();

    #pragma omp parallel for schedule(dynamic)
    for (int i = 0; i < count; i++) {
        int z[N];
        decrypt_to_z(cands[i].mode, cands[i].q4, cands[i].q7, z);

        for (int pat = 1; pat <= 2; pat++) {
            for (int p = 0; p < 720; p++) {
                int pt[N];
                decode_amsco(z, 6, 16, pat, perms6[p], pt);
                float sc = score_quads(pt);

                if (sc > best_sc6) {
                    #pragma omp critical
                    {
                        if (sc > best_sc6) {
                            best_sc6 = sc;
                            best_cand6 = i;
                            best_pat6 = pat;
                            memcpy(best_perm6, perms6[p], 6 * sizeof(int));

                            for (int k = 0; k < N; k++) best_pt6[k] = pt[k] + 'A';
                            best_pt6[N] = 0;

                            printf("[AMSCO W=6] New Best: %.4f | Mode %d | Cand #%d | Pat %d | Order: [%d,%d,%d,%d,%d,%d]\n  PT: %.80s...\n",
                                   sc, cands[i].mode, i, pat,
                                   best_perm6[0], best_perm6[1], best_perm6[2], best_perm6[3], best_perm6[4], best_perm6[5],
                                   best_pt6);
                        }
                    }
                }
            }
        }
    }

    double elapsed = omp_get_wtime() - t0;
    printf("Width 6 AMSCO scan completed in %.2f seconds. Best Score: %.4f\n", elapsed, best_sc6);

    // Test 2: Width 8 (H = 12) - All 8! = 40,320 perms, start_pat in {1, 2} on top 100 cands
    printf("\n=== Testing AMSCO Transposition for Width 8 (12 rows x 8 cols) on top 100 cands ===\n");
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

    float best_sc8 = -999.0f;
    int best_cand8 = -1, best_perm8[8], best_pat8 = 1;
    char best_pt8[N+1];

    t0 = omp_get_wtime();

    #pragma omp parallel for schedule(dynamic)
    for (int i = 0; i < 100; i++) {
        int z[N];
        decrypt_to_z(cands[i].mode, cands[i].q4, cands[i].q7, z);

        for (int pat = 1; pat <= 2; pat++) {
            for (int p = 0; p < 40320; p++) {
                int pt[N];
                decode_amsco(z, 8, 12, pat, perms8[p], pt);
                float sc = score_quads(pt);

                if (sc > best_sc8) {
                    #pragma omp critical
                    {
                        if (sc > best_sc8) {
                            best_sc8 = sc;
                            best_cand8 = i;
                            best_pat8 = pat;
                            memcpy(best_perm8, perms8[p], 8 * sizeof(int));

                            for (int k = 0; k < N; k++) best_pt8[k] = pt[k] + 'A';
                            best_pt8[N] = 0;

                            printf("[AMSCO W=8] New Best: %.4f | Mode %d | Cand #%d | Pat %d\n  PT: %.80s...\n",
                                   sc, cands[i].mode, i, pat, best_pt8);
                        }
                    }
                }
            }
        }
    }

    elapsed = omp_get_wtime() - t0;
    printf("Width 8 AMSCO scan completed in %.2f seconds. Best Score: %.4f\n", elapsed, best_sc8);

    return 0;
}
