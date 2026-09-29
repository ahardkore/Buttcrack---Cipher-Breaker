#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

#define N 144
#define W 12
#define H 12

static const char *ALPH = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
static const char *PK9_REAL = "KSYAWFEYYOISZGEUFBLYATAIBYFAQBQYYVDWJKLJXMYIEPIFVHPQNHZGSUHUUDXLEHRHUMALHEGLHXSJMUXGNUIVBXGUJHZRZGUSVHMLSCTSUQXHSUMQQIFUQGKHJGUQGLHDKEWSKAMHIJXD";

static int ct_kr[N];
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
            if (a>=0&&a<26&&b>=0&&b<26&&c>=0&&c<26&&d>=0&&d<26)
                quad_table[a][b][c][d] = (float)log10((cnt + 0.01) / total);
        }
    }
    fclose(f);

    for (int a = 0; a < 26; a++) {
        kr_to_std[a] = ALPH[a] - 'A';
        std_to_kr[ALPH[a] - 'A'] = a;
    }
    for (int i = 0; i < N; i++) {
        ct_kr[i] = std_to_kr[PK9_REAL[i] - 'A'];
    }
}

void col_decrypt(const int *in, const int *order, int *out, int w, int h) {
    int grid[H][W];
    int idx = 0;
    for (int c_idx = 0; c_idx < w; c_idx++) {
        int col = order[c_idx];
        for (int r = 0; r < h; r++) grid[r][col] = in[idx++];
    }
    idx = 0;
    for (int r = 0; r < h; r++)
        for (int c = 0; c < w; c++) out[idx++] = grid[r][c];
}

static inline float score_quadgrams(const int *txt) {
    float s = 0.0f;
    for (int i = 0; i < N - 3; i++) {
        s += quad_table[txt[i]][txt[i+1]][txt[i+2]][txt[i+3]];
    }
    return s / (N - 3);
}

static inline void get_mapping(const int *o1, const int *o2, int *pt_to_z2) {
    int identity[N]; for (int j = 0; j < N; j++) identity[j] = j;
    int after2[N];
    col_decrypt(identity, o2, after2, W, H);
    col_decrypt(after2, o1, pt_to_z2, W, H);
}

static inline void decrypt_with_shifts(const int *pt_to_z2, const int *shifts, int *pt) {
    for (int t = 0; t < N; t++) {
        int pos = pt_to_z2[t];
        int sh = shifts[pos % 28];
        int c_val = ct_kr[pos];
        int p_val = (sh - c_val + 26) % 26;
        pt[t] = kr_to_std[p_val];
    }
}

float polish_shifts(const int *pt_to_z2, int *shifts, int *pt) {
    decrypt_with_shifts(pt_to_z2, shifts, pt);
    float cur_sc = score_quadgrams(pt);

    int improved = 1;
    while (improved) {
        improved = 0;
        for (int s = 0; s < 28; s++) {
            int orig_val = shifts[s];
            int best_val = orig_val;
            float best_sc = cur_sc;

            for (int v = 0; v < 26; v++) {
                if (v == orig_val) continue;
                shifts[s] = v;
                int test_pt[N];
                decrypt_with_shifts(pt_to_z2, shifts, test_pt);
                float sc = score_quadgrams(test_pt);
                if (sc > best_sc) {
                    best_sc = sc;
                    best_val = v;
                }
            }
            if (best_val != orig_val) {
                shifts[s] = best_val;
                cur_sc = best_sc;
                improved = 1;
            } else {
                shifts[s] = orig_val;
            }
        }
    }
    decrypt_with_shifts(pt_to_z2, shifts, pt);
    return cur_sc;
}

int main() {
    load_models();
    printf("Refining PK9 Neighborhood around breakthrough state...\n");

    int base_o1[W] = {3, 4, 11, 10, 6, 1, 8, 7, 9, 0, 5, 2};
    int base_o2[W] = {0, 10, 4, 2, 8, 7, 9, 1, 6, 5, 3, 11};
    int base_shifts[28] = {21, 1, 3, 13, 9, 17, 16, 6, 21, 19, 6, 18, 9, 24, 8, 25, 18, 18, 19, 2, 11, 15, 14, 21, 19, 25, 3, 24};

    int cur_o1[W], cur_o2[W], cur_shifts[28];
    memcpy(cur_o1, base_o1, sizeof(cur_o1));
    memcpy(cur_o2, base_o2, sizeof(cur_o2));
    memcpy(cur_shifts, base_shifts, sizeof(cur_shifts));

    int pt_to_z2[N], pt[N];
    get_mapping(cur_o1, cur_o2, pt_to_z2);
    float best_sc = polish_shifts(pt_to_z2, cur_shifts, pt);
    printf("Initial polished score: %.4f\n", best_sc);

    // Iterative 2-opt and swap hill climber
    int outer_improved = 1;
    int round = 0;
    while (outer_improved && round < 20) {
        outer_improved = 0;
        round++;
        printf("--- Round %d (Current best: %.4f) ---\n", round, best_sc);

        // Try all swaps in o1
        for (int a = 0; a < W - 1; a++) {
            for (int b = a + 1; b < W; b++) {
                int test_o1[W]; memcpy(test_o1, cur_o1, sizeof(test_o1));
                int t = test_o1[a]; test_o1[a] = test_o1[b]; test_o1[b] = t;

                int test_map[N], test_shifts[28], test_pt[N];
                memcpy(test_shifts, cur_shifts, sizeof(test_shifts));
                get_mapping(test_o1, cur_o2, test_map);
                float sc = polish_shifts(test_map, test_shifts, test_pt);

                if (sc > best_sc) {
                    best_sc = sc;
                    memcpy(cur_o1, test_o1, sizeof(cur_o1));
                    memcpy(cur_shifts, test_shifts, sizeof(cur_shifts));
                    outer_improved = 1;
                    char s[N+1]; for (int j=0; j<N; j++) s[j] = test_pt[j]+'A'; s[N]='\0';
                    printf("  [o1 swap %d,%d] NEW BEST: %.4f -> %.60s...\n", a, b, best_sc, s);
                }
            }
        }

        // Try all swaps in o2
        for (int a = 0; a < W - 1; a++) {
            for (int b = a + 1; b < W; b++) {
                int test_o2[W]; memcpy(test_o2, cur_o2, sizeof(test_o2));
                int t = test_o2[a]; test_o2[a] = test_o2[b]; test_o2[b] = t;

                int test_map[N], test_shifts[28], test_pt[N];
                memcpy(test_shifts, cur_shifts, sizeof(test_shifts));
                get_mapping(cur_o1, test_o2, test_map);
                float sc = polish_shifts(test_map, test_shifts, test_pt);

                if (sc > best_sc) {
                    best_sc = sc;
                    memcpy(cur_o2, test_o2, sizeof(cur_o2));
                    memcpy(cur_shifts, test_shifts, sizeof(cur_shifts));
                    outer_improved = 1;
                    char s[N+1]; for (int j=0; j<N; j++) s[j] = test_pt[j]+'A'; s[N]='\0';
                    printf("  [o2 swap %d,%d] NEW BEST: %.4f -> %.60s...\n", a, b, best_sc, s);
                }
            }
        }

        // Try all 2-opts in o1 (reverse segment)
        for (int a = 0; a < W - 2; a++) {
            for (int b = a + 2; b < W; b++) {
                int test_o1[W]; memcpy(test_o1, cur_o1, sizeof(test_o1));
                int l = a, r = b;
                while (l < r) { int t = test_o1[l]; test_o1[l] = test_o1[r]; test_o1[r] = t; l++; r--; }

                int test_map[N], test_shifts[28], test_pt[N];
                memcpy(test_shifts, cur_shifts, sizeof(test_shifts));
                get_mapping(test_o1, cur_o2, test_map);
                float sc = polish_shifts(test_map, test_shifts, test_pt);

                if (sc > best_sc) {
                    best_sc = sc;
                    memcpy(cur_o1, test_o1, sizeof(cur_o1));
                    memcpy(cur_shifts, test_shifts, sizeof(cur_shifts));
                    outer_improved = 1;
                    char s[N+1]; for (int j=0; j<N; j++) s[j] = test_pt[j]+'A'; s[N]='\0';
                    printf("  [o1 2-opt %d..%d] NEW BEST: %.4f -> %.60s...\n", a, b, best_sc, s);
                }
            }
        }

        // Try all 2-opts in o2
        for (int a = 0; a < W - 2; a++) {
            for (int b = a + 2; b < W; b++) {
                int test_o2[W]; memcpy(test_o2, cur_o2, sizeof(test_o2));
                int l = a, r = b;
                while (l < r) { int t = test_o2[l]; test_o2[l] = test_o2[r]; test_o2[r] = t; l++; r--; }

                int test_map[N], test_shifts[28], test_pt[N];
                memcpy(test_shifts, cur_shifts, sizeof(test_shifts));
                get_mapping(cur_o1, test_o2, test_map);
                float sc = polish_shifts(test_map, test_shifts, test_pt);

                if (sc > best_sc) {
                    best_sc = sc;
                    memcpy(cur_o2, test_o2, sizeof(cur_o2));
                    memcpy(cur_shifts, test_shifts, sizeof(cur_shifts));
                    outer_improved = 1;
                    char s[N+1]; for (int j=0; j<N; j++) s[j] = test_pt[j]+'A'; s[N]='\0';
                    printf("  [o2 2-opt %d..%d] NEW BEST: %.4f -> %.60s...\n", a, b, best_sc, s);
                }
            }
        }
    }

    get_mapping(cur_o1, cur_o2, pt_to_z2);
    decrypt_with_shifts(pt_to_z2, cur_shifts, pt);
    char final_pt[N+1];
    for (int j = 0; j < N; j++) final_pt[j] = pt[j] + 'A';
    final_pt[N] = '\0';

    printf("\n==================================================\n");
    printf("FINAL REFINED STATE: Score %.4f\n", best_sc);
    printf("o1: ["); for (int i=0; i<W; i++) printf("%d%s", cur_o1[i], i==W-1?"":", "); printf("]\n");
    printf("o2: ["); for (int i=0; i<W; i++) printf("%d%s", cur_o2[i], i==W-1?"":", "); printf("]\n");
    printf("shifts: ["); for (int i=0; i<28; i++) printf("%d%s", cur_shifts[i], i==27?"":", "); printf("]\n");
    printf("Plaintext:\n%s\n", final_pt);
    printf("==================================================\n");

    return 0;
}
