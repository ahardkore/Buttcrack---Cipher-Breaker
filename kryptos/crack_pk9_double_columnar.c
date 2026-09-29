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

const char *KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
const char *PK9_CT = "KSYAWFEYYOISZGEUFBLYATAIBYFAQBQYYVDWJKLJXMYIEPIFVHPQNHZGSUHUUDXLEHRHUMALHEGLHXSJMUXGNUIVBXGUJHZRZGUSVHMLSCTSUQXHSUMQQIFUQGKHJGUQGLHDKEWSKAMHIJXD";

static int c_idx[N];
static int hpos[256];
static int k_to_std[26];

void init_tables() {
    for (int i = 0; i < 26; i++) {
        hpos[(unsigned char)KRYPTOS[i]] = i;
        k_to_std[i] = KRYPTOS[i] - 'A';
    }
    for (int i = 0; i < N; i++) {
        c_idx[i] = hpos[(unsigned char)PK9_CT[i]];
    }
}

static inline float score_plain(const int *pt) {
    float s = 0.0f;
    for (int i = 0; i < N - 3; i++) {
        s += quad[pt[i]][pt[i+1]][pt[i+2]][pt[i+3]];
    }
    return s / (N - 3);
}

// Single columnar decode on integer indices
void single_col_decode(const int *in, int len, int width, const int *order, int *out) {
    int h = len / width;
    int grid[150][30];
    int k = 0;
    for (int m = 0; m < width; m++) {
        int col = order[m];
        for (int r = 0; r < h; r++) {
            grid[r][col] = in[k++];
        }
    }
    int idx = 0;
    for (int r = 0; r < h; r++) {
        for (int c = 0; c < width; c++) {
            out[idx++] = grid[r][c];
        }
    }
}

// Double columnar mapping: plain[p] = X[plain_indices[p]]
void make_double_col_mapping(int w1, const int *o1, int w2, const int *o2, int *plain_indices) {
    int x_indices[N];
    for (int i = 0; i < N; i++) x_indices[i] = i;
    int inter[N];
    // Undo O2 first, then O1
    single_col_decode(x_indices, N, w2, o2, inter);
    single_col_decode(inter, N, w1, o1, plain_indices);
}

// Optimize period P shifts on the double-columnar mapping
float optimize_shifts(int P, const int *plain_indices, int *best_shifts, char *best_pt_out) {
    int shifts[32];
    for (int j = 0; j < P; j++) shifts[j] = 0;

    int X[N], pt[N];
    for (int o = 0; o < N; o++) {
        int dec_k = (c_idx[o] - shifts[o % P] + 26) % 26;
        X[o] = dec_k;
    }
    for (int p = 0; p < N; p++) {
        pt[p] = k_to_std[X[plain_indices[p]]];
    }
    float cur_sc = score_plain(pt);

    int improved = 1;
    int passes = 0;
    while (improved && passes < 6) {
        improved = 0;
        passes++;
        for (int j = 0; j < P; j++) {
            int old_sh = shifts[j];
            int best_sh = old_sh;
            float best_s = cur_sc;

            for (int sh = 0; sh < 26; sh++) {
                if (sh == old_sh) continue;
                for (int o = j; o < N; o += P) {
                    X[o] = (c_idx[o] - sh + 26) % 26;
                }
                for (int p = 0; p < N; p++) {
                    pt[p] = k_to_std[X[plain_indices[p]]];
                }
                float s = score_plain(pt);
                if (s > best_s) {
                    best_s = s;
                    best_sh = sh;
                }
            }
            shifts[j] = best_sh;
            for (int o = j; o < N; o += P) {
                X[o] = (c_idx[o] - shifts[j] + 26) % 26;
            }
            if (best_sh != old_sh) {
                cur_sc = best_s;
                improved = 1;
            }
        }
    }

    if (best_shifts) {
        for (int j = 0; j < P; j++) best_shifts[j] = shifts[j];
    }
    if (best_pt_out) {
        for (int p = 0; p < N; p++) {
            pt[p] = k_to_std[X[plain_indices[p]]];
            best_pt_out[p] = 'A' + pt[p];
        }
        best_pt_out[N] = '\0';
    }
    return cur_sc;
}

typedef struct {
    char word[16];
    int order[16];
} WordOrder;

int load_wordlist(const char *path, int expected_len, WordOrder *list, int max_items) {
    FILE *f = fopen(path, "r");
    if (!f) return 0;
    char line[64];
    int count = 0;
    while (fgets(line, sizeof(line), f) && count < max_items) {
        char w[32];
        if (sscanf(line, "%s", w) == 1 && strlen(w) == expected_len) {
            strcpy(list[count].word, w);
            typedef struct { char ch; int orig_idx; } Pair;
            Pair p[16];
            for (int i = 0; i < expected_len; i++) { p[i].ch = w[i]; p[i].orig_idx = i; }
            for (int i = 0; i < expected_len - 1; i++) {
                for (int j = i + 1; j < expected_len; j++) {
                    if (p[j].ch < p[i].ch || (p[j].ch == p[i].ch && p[j].orig_idx < p[i].orig_idx)) {
                        Pair tmp = p[i]; p[i] = p[j]; p[j] = tmp;
                    }
                }
            }
            for (int i = 0; i < expected_len; i++) list[count].order[i] = p[i].orig_idx;
            count++;
        }
    }
    fclose(f);
    return count;
}

void test_double_columnar(int w1, WordOrder *list1, int n1,
                          int w2, WordOrder *list2, int n2,
                          int P) {
    long total_pairs = (long)n1 * n2;
    printf("\n=== Double Columnar (%d, %d) on %d x %d = %ld pairs with Period %d ===\n",
           w1, w2, n1, n2, total_pairs, P);

    float global_best_sc = -999.0f;
    char global_w1[16] = "", global_w2[16] = "";
    int global_shifts[32];
    char global_pt[N+1] = "";

    double t0 = omp_get_wtime();

    #pragma omp parallel
    {
        float local_best_sc = -999.0f;
        char local_w1[16] = "", local_w2[16] = "";
        int local_shifts[32];
        char local_pt[N+1] = "";

        #pragma omp for schedule(dynamic, 100)
        for (long idx = 0; idx < total_pairs; idx++) {
            int i1 = idx / n2;
            int i2 = idx % n2;

            int plain_indices[N];
            make_double_col_mapping(w1, list1[i1].order, w2, list2[i2].order, plain_indices);

            int shifts[32];
            char pt[N+1];
            float sc = optimize_shifts(P, plain_indices, shifts, pt);

            if (sc > -5.6f) {
                #pragma omp critical
                {
                    printf("HIT! Score=%.4f | Pair: (%s, %s) | Shifts: ", sc, list1[i1].word, list2[i2].word);
                    for (int j = 0; j < P; j++) printf("%c", KRYPTOS[shifts[j]]);
                    printf("\nPT: %s\n", pt);
                    fflush(stdout);
                }
            }

            if (sc > local_best_sc) {
                local_best_sc = sc;
                strcpy(local_w1, list1[i1].word);
                strcpy(local_w2, list2[i2].word);
                for (int j = 0; j < P; j++) local_shifts[j] = shifts[j];
                strcpy(local_pt, pt);
            }
        }

        #pragma omp critical
        {
            if (local_best_sc > global_best_sc) {
                global_best_sc = local_best_sc;
                strcpy(global_w1, local_w1);
                strcpy(global_w2, local_w2);
                for (int j = 0; j < P; j++) global_shifts[j] = local_shifts[j];
                strcpy(global_pt, local_pt);
            }
        }
    }

    double elapsed = omp_get_wtime() - t0;
    printf("Completed in %.2f s (%.1f pairs/sec)\n", elapsed, total_pairs / elapsed);
    printf("Best Score: %.4f | Words: (%s, %s)\n", global_best_sc, global_w1, global_w2);
    printf("Shifts (KRYPTOS): ");
    for (int j = 0; j < P; j++) printf("%c", KRYPTOS[global_shifts[j]]);
    printf("\nPlaintext: %s\n", global_pt);
}

static WordOrder list6[1500], list8[1000], list9[1000], list12[2000];

int main() {
    printf("Loading quadgrams...\n"); fflush(stdout);
    load_quadgrams();
    printf("Quadgrams loaded.\n"); fflush(stdout);
    init_tables();

    int n6 = load_wordlist("curated_w6.txt", 6, list6, 1500);
    int n8 = load_wordlist("theophilus_w8.txt", 8, list8, 1000);
    int n9 = load_wordlist("theophilus_w9.txt", 9, list9, 1000);
    int n12 = load_wordlist("words_12.txt", 12, list12, 1000);

    printf("Loaded: %d w6, %d w8, %d w9, %d w12\n", n6, n8, n9, n12);

    // 1. (8, 6) Period 7
    test_double_columnar(8, list8, n8, 6, list6, n6, 7);

    // 2. (6, 8) Period 7
    test_double_columnar(6, list6, n6, 8, list8, n8, 7);

    // 3. (9, 8) Period 7
    test_double_columnar(9, list9, n9, 8, list8, n8, 7);

    // 4. (8, 9) Period 7
    test_double_columnar(8, list8, n8, 9, list9, n9, 7);

    // 5. (6, 6) Period 7
    test_double_columnar(6, list6, n6, 6, list6, n6, 7);

    // 6. (8, 6) Period 12
    test_double_columnar(8, list8, n8, 6, list6, n6, 12);

    // 7. (12, 12) Period 7 (1,000 top words x 1,000 = 1,000,000 pairs)
    // test_double_columnar(12, list12, n12, 12, list12, n12, 7);

    return 0;
}
