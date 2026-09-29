#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <omp.h>

static float quad_table[26][26][26][26];
static const char *ALPH_K = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
static int k_to_std[26];
static int std_to_k[26];

static const char *CT9_REAL = "KSYAWFEYYOISZGEUFBLYATAIBYFAQBQYYVDWJKLJXMYIEPIFVHPQNHZGSUHUUDXLEHRHUMALHEGLHXSJMUXGNUIVBXGUJHZRZGUSVHMLSCTSUQXHSUMQQIFUQGKHJGUQGLHDKEWSKAMHIJXD";
static int C[144];
static const int N = 144;

typedef struct {
    char word[8];
    int shifts[7];
} Word;

static Word *w7_list = NULL;
static int n7 = 0;

static int perms6[720][6];
static int n_perms6 = 0;
static int perms8[40320][8];
static int n_perms8 = 0;

void gen_perms6(int *arr, int l, int r) {
    if (l == r) {
        for (int i = 0; i < 6; i++) perms6[n_perms6][i] = arr[i];
        n_perms6++;
        return;
    }
    for (int i = l; i <= r; i++) {
        int t = arr[l]; arr[l] = arr[i]; arr[i] = t;
        gen_perms6(arr, l + 1, r);
        t = arr[l]; arr[l] = arr[i]; arr[i] = t;
    }
}

void gen_perms8(int *arr, int l, int r) {
    if (l == r) {
        for (int i = 0; i < 8; i++) perms8[n_perms8][i] = arr[i];
        n_perms8++;
        return;
    }
    for (int i = l; i <= r; i++) {
        int t = arr[l]; arr[l] = arr[i]; arr[i] = t;
        gen_perms8(arr, l + 1, r);
        t = arr[l]; arr[l] = arr[i]; arr[i] = t;
    }
}

void init() {
    for (int i = 0; i < 26; i++) {
        for (int j = 0; j < 26; j++) {
            for (int k = 0; k < 26; k++) {
                for (int l = 0; l < 26; l++) {
                    quad_table[i][j][k][l] = -9.0f;
                }
            }
        }
    }
    FILE *f = fopen("english_quads.tsv", "r");
    if (!f) { fprintf(stderr, "Cannot open quads\n"); exit(1); }
    char q[16];
    float sc;
    while (fscanf(f, "%s\t%f", q, &sc) == 2) {
        if (strlen(q) == 4) {
            int c0 = q[0]-'A', c1 = q[1]-'A', c2 = q[2]-'A', c3 = q[3]-'A';
            if (c0>=0&&c0<26&&c1>=0&&c1<26&&c2>=0&&c2<26&&c3>=0&&c3<26) {
                quad_table[c0][c1][c2][c3] = sc;
            }
        }
    }
    fclose(f);

    for (int i = 0; i < 26; i++) {
        int std = ALPH_K[i] - 'A';
        k_to_std[i] = std;
        std_to_k[std] = i;
    }
    for (int i = 0; i < N; i++) {
        C[i] = std_to_k[CT9_REAL[i] - 'A'];
    }

    int a6[6] = {0, 1, 2, 3, 4, 5};
    gen_perms6(a6, 0, 5);
    int a8[8] = {0, 1, 2, 3, 4, 5, 6, 7};
    gen_perms8(a8, 0, 7);
    printf("Permutations: width 6 = %d, width 8 = %d\n", n_perms6, n_perms8);

    w7_list = malloc(50000 * sizeof(Word));
    f = fopen("words_alpha.txt", "r");
    if (!f) { fprintf(stderr, "Cannot open words_alpha.txt\n"); exit(1); }
    char buf[64];
    while (fscanf(f, "%63s", buf) == 1) {
        if (strlen(buf) == 7) {
            int ok = 1;
            for (int i = 0; i < 7; i++) {
                if (buf[i] >= 'a' && buf[i] <= 'z') buf[i] = buf[i] - 'a' + 'A';
                if (buf[i] < 'A' || buf[i] > 'Z') ok = 0;
            }
            if (!ok) continue;
            strcpy(w7_list[n7].word, buf);
            for (int i = 0; i < 7; i++) w7_list[n7].shifts[i] = std_to_k[buf[i] - 'A'];
            n7++;
        }
    }
    fclose(f);
    printf("Loaded: W7=%d\n", n7);
}

int main(int argc, char **argv) {
    (void)argc; (void)argv;
    init();

    // Test 1: Width 6 columnar transposition (24 rows, 6 cols)
    // For each W7 in dictionary, compute M' = (C - W7) mod 26
    // Then for each perm in perms6, untranspose M' into P, score with quadgrams
    printf("\n--- Test 1: Width 6 Columnar (24 rows x 6 cols) across %d W7 x 720 perms = %lld combos ---\n",
           n7, (long long)n7 * n_perms6);

    float best_sc6 = -999.0f;
    char best_w6[16] = "";
    int best_perm6[6];
    char best_pt6[150] = "";

    #pragma omp parallel
    {
        float local_best = -999.0f;
        char local_w[16] = "";
        int local_perm[6];
        char local_pt[150] = "";

        #pragma omp for schedule(dynamic, 100)
        for (int i7 = 0; i7 < n7; i7++) {
            const int *s7 = w7_list[i7].shifts;

            // Compute M' = (C - s7) mod 26 in KRYPTOS
            int M_prime[144];
            for (int i = 0; i < N; i++) {
                M_prime[i] = (C[i] - s7[i % 7] + 26) % 26;
            }

            // Test both write-row/read-col and write-col/read-row
            // Standard columnar un-transpose:
            // Text M' was read column by column from grid of width 6, height 24.
            // Column c of M' is placed into column perm[c] of grid.
            // Then plaintext is read row by row.
            // P[r * 6 + c] = M'[perm[c] * 24 + r]
            for (int pi = 0; pi < n_perms6; pi++) {
                const int *p = perms6[pi];

                // Fast check: first 16 chars (rows 0 and 1)
                int pt[16];
                int idx = 0;
                for (int r = 0; r < 2; r++) {
                    for (int c = 0; c < 6; c++) {
                        pt[idx++] = k_to_std[M_prime[p[c] * 24 + r]];
                    }
                }
                for (int c = 0; c < 4; c++) {
                    pt[idx++] = k_to_std[M_prime[p[c] * 24 + 2]];
                }
                float sc = 0.0f;
                for (int i = 0; i < 13; i++) sc += quad_table[pt[i]][pt[i+1]][pt[i+2]][pt[i+3]];
                sc /= 13.0f;
                if (sc < -5.6f) continue;

                // Full 144
                int full_pt[144];
                idx = 0;
                for (int r = 0; r < 24; r++) {
                    for (int c = 0; c < 6; c++) {
                        full_pt[idx++] = k_to_std[M_prime[p[c] * 24 + r]];
                    }
                }
                float full_sc = 0.0f;
                for (int i = 0; i < 141; i++) full_sc += quad_table[full_pt[i]][full_pt[i+1]][full_pt[i+2]][full_pt[i+3]];
                full_sc /= 141.0f;

                if (full_sc > local_best) {
                    local_best = full_sc;
                    strcpy(local_w, w7_list[i7].word);
                    for (int i = 0; i < 6; i++) local_perm[i] = p[i];
                    for (int i = 0; i < N; i++) local_pt[i] = full_pt[i] + 'A';
                    local_pt[N] = '\0';
                }
            }
        }

        #pragma omp critical
        {
            if (local_best > best_sc6) {
                best_sc6 = local_best;
                strcpy(best_w6, local_w);
                for (int i = 0; i < 6; i++) best_perm6[i] = local_perm[i];
                strcpy(best_pt6, local_pt);
                printf("New best W6: sc=%.3f | kw=%s perm=[%d,%d,%d,%d,%d,%d]\nPT: %.55s...\n",
                       best_sc6, best_w6, best_perm6[0], best_perm6[1], best_perm6[2],
                       best_perm6[3], best_perm6[4], best_perm6[5], best_pt6);
                fflush(stdout);
            }
        }
    }

    printf("\nWidth 6 complete. Best: sc=%.3f with kw=%s\nPT: %s\n", best_sc6, best_w6, best_pt6);

    // Test 2: Width 8 columnar transposition (18 rows x 8 cols)
    // Test top 100 thematic words across all 40,320 perms
    const char *thematic_keys[] = {
        "KRYPTOS", "WEBSTER", "WOMACKA", "WILLIAM", "SANBORN", "SCHEIDT", "LANGLEY",
        "BERLINS", "GERMANY", "AMERICA", "HEARTHS", "NEEDLES", "WHITESM", "WORKSHO",
        "ANVILSS", "BELLOWS", "HAMMERS", "METALLS", "IRONBAR", "COPPERT", "DRAWPLT",
        "PELLEGR", "VIENNAS", "AUSTRIA", "LEIPZIG", "EASTNNE", "PALIMPS", "ABSCISS",
        "PORTALS", "SEVENTH", "FIFTEEN", "FOURTEE", "SIXTEEN", "TWENTYF", "NIMBLES",
        "WIMBLES", "WINDLES", "TROWELS", "TONGSSS", "CHISELS", "PLIERSN", "SPINDLE",
        "THIMBLE", "SHUTTLE", "BOBBINS", "LOOMSSS", "WEAVERS", "SPINNER", "TAILORS",
        "QUENCHS", "TEMPERS", "ANNEALS", "FORGING", "CRUCIBL", "FURNACE", "CASTING"
    };
    int n_them = sizeof(thematic_keys)/sizeof(thematic_keys[0]);

    printf("\n--- Test 2: Width 8 Columnar (18 rows x 8 cols) across %d thematic keys x 40,320 perms ---\n",
           n_them);

    float best_sc8 = -999.0f;
    char best_w8[16] = "";
    int best_perm8[8];
    char best_pt8[150] = "";

    #pragma omp parallel
    {
        float local_best = -999.0f;
        char local_w[16] = "";
        int local_perm[8];
        char local_pt[150] = "";

        #pragma omp for schedule(dynamic, 1)
        for (int k = 0; k < n_them; k++) {
            const char *kw = thematic_keys[k];
            int s7[7];
            for (int i = 0; i < 7; i++) s7[i] = std_to_k[kw[i] - 'A'];

            int M_prime[144];
            for (int i = 0; i < N; i++) {
                M_prime[i] = (C[i] - s7[i % 7] + 26) % 26;
            }

            for (int pi = 0; pi < n_perms8; pi++) {
                const int *p = perms8[pi];

                // Fast check: first 16 chars (rows 0 and 1)
                int pt[16];
                int idx = 0;
                for (int r = 0; r < 2; r++) {
                    for (int c = 0; c < 8; c++) {
                        pt[idx++] = k_to_std[M_prime[p[c] * 18 + r]];
                    }
                }
                float sc = 0.0f;
                for (int i = 0; i < 13; i++) sc += quad_table[pt[i]][pt[i+1]][pt[i+2]][pt[i+3]];
                sc /= 13.0f;
                if (sc < -5.6f) continue;

                // Full 144
                int full_pt[144];
                idx = 0;
                for (int r = 0; r < 18; r++) {
                    for (int c = 0; c < 8; c++) {
                        full_pt[idx++] = k_to_std[M_prime[p[c] * 18 + r]];
                    }
                }
                float full_sc = 0.0f;
                for (int i = 0; i < 141; i++) full_sc += quad_table[full_pt[i]][full_pt[i+1]][full_pt[i+2]][full_pt[i+3]];
                full_sc /= 141.0f;

                if (full_sc > local_best) {
                    local_best = full_sc;
                    strcpy(local_w, kw);
                    for (int i = 0; i < 8; i++) local_perm[i] = p[i];
                    for (int i = 0; i < N; i++) local_pt[i] = full_pt[i] + 'A';
                    local_pt[N] = '\0';
                }
            }
        }

        #pragma omp critical
        {
            if (local_best > best_sc8) {
                best_sc8 = local_best;
                strcpy(best_w8, local_w);
                for (int i = 0; i < 8; i++) best_perm8[i] = local_perm[i];
                strcpy(best_pt8, local_pt);
                printf("New best W8: sc=%.3f | kw=%s perm=[%d,%d,%d,%d,%d,%d,%d,%d]\nPT: %.55s...\n",
                       best_sc8, best_w8, best_perm8[0], best_perm8[1], best_perm8[2],
                       best_perm8[3], best_perm8[4], best_perm8[5], best_perm8[6], best_perm8[7], best_pt8);
                fflush(stdout);
            }
        }
    }

    printf("\nWidth 8 complete. Best: sc=%.3f with kw=%s\nPT: %s\n", best_sc8, best_w8, best_pt8);
    return 0;
}
