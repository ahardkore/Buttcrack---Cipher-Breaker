#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <stdint.h>
#include <omp.h>

static float quad_table[26][26][26][26];
static const char *ALPH_K = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
static int k_to_std[26];
static int std_to_k[26];

static const char *C_STR = "KSYAWFEYYOISZGEUFBTLAYATAIBYFAQBQYYVDWJKLJXMYIEPIFVHPQNHZGSUHUUDXLEHRHUMALHEGLHXSJMUXGNUIVBXGUJHZRZGUSVHMLSCTSUQXHSUMQQIFUQGKHJGUQGLHDKEWSKAMHIJXD";
static int C[144];
static const int N = 144;

void init() {
    for (int i = 0; i < 26; i++) {
        for (int j = 0; j < 26; j++) {
            for (int k = 0; k < 26; k++) {
                for (int l = 0; l < 26; l++) {
                    quad_table[i][j][k][l] = -9.5f;
                }
            }
        }
    }
    FILE *f = fopen("/home/user/english_quads.tsv", "r");
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
        C[i] = std_to_k[C_STR[i] - 'A'];
    }
}

// Load top trigraphs from file
#define MAX_TRI 2000
static char tri_list[MAX_TRI][4];
static int n_tri = 0;

void load_trigraphs() {
    FILE *f = fopen("/home/user/buttcrack/src/buttcrack/data/english_trigrams.txt", "r");
    if (!f) { fprintf(stderr, "Cannot open trigrams\n"); exit(1); }
    char tri[16];
    int count;
    while (fscanf(f, "%s %d", tri, &count) == 2 && n_tri < MAX_TRI) {
        if (strlen(tri) == 3) {
            strcpy(tri_list[n_tri++], tri);
        }
    }
    fclose(f);
    printf("Loaded %d top English trigraphs.\n", n_tri);
}

int main() {
    init();
    load_trigraphs();

    // At index 119 and 126, C_STR is 'U', 'Q', 'G'
    int c0 = std_to_k['U' - 'A'];
    int c1 = std_to_k['Q' - 'A'];
    int c2 = std_to_k['G' - 'A'];

    printf("Starting search across all %d candidate trigraphs for 'UQG' at pos 119 & 126...\n", n_tri);
    double t0 = omp_get_wtime();

    float global_best_sc = -999.0f;
    char global_best_pt[150];
    char global_best_key[8];

    #pragma omp parallel for schedule(dynamic)
    for (int t = 0; t < n_tri; t++) {
        int p0 = std_to_k[tri_list[t][0] - 'A'];
        int p1 = std_to_k[tri_list[t][1] - 'A'];
        int p2 = std_to_k[tri_list[t][2] - 'A'];

        // Under Quagmire III: C = P + K (mod 26) => K = C - P (mod 26)
        int k0 = (c0 - p0 + 26) % 26;
        int k1 = (c1 - p1 + 26) % 26;
        int k2 = (c2 - p2 + 26) % 26;

        float local_best_sc = -999.0f;
        int local_k[7] = {k0, k1, k2, 0, 0, 0, 0};

        // Loop over all 26^4 = 456,976 combinations of (k3, k4, k5, k6)
        for (int k3 = 0; k3 < 26; k3++) {
            for (int k4 = 0; k4 < 26; k4++) {
                for (int k5 = 0; k5 < 26; k5++) {
                    for (int k6 = 0; k6 < 26; k6++) {
                        int k[7] = {k0, k1, k2, k3, k4, k5, k6};
                        // Evaluate quadgram score of first 30 chars first as quick filter
                        float fast_sc = 0.0f;
                        int pt_fast[30];
                        for (int i = 0; i < 30; i++) {
                            int pi = (C[i] - k[i % 7] + 26) % 26;
                            pt_fast[i] = k_to_std[pi];
                        }
                        for (int i = 0; i < 27; i++) {
                            fast_sc += quad_table[pt_fast[i]][pt_fast[i+1]][pt_fast[i+2]][pt_fast[i+3]];
                        }
                        if (fast_sc < -200.0f) continue; // Fast reject

                        // Full evaluate
                        float full_sc = 0.0f;
                        int pt[144];
                        for (int i = 0; i < N; i++) {
                            int pi = (C[i] - k[i % 7] + 26) % 26;
                            pt[i] = k_to_std[pi];
                        }
                        for (int i = 0; i < N - 3; i++) {
                            full_sc += quad_table[pt[i]][pt[i+1]][pt[i+2]][pt[i+3]];
                        }
                        full_sc /= (N - 3);

                        if (full_sc > local_best_sc) {
                            local_best_sc = full_sc;
                            local_k[3] = k3; local_k[4] = k4; local_k[5] = k5; local_k[6] = k6;
                        }
                    }
                }
            }
        }

        #pragma omp critical
        {
            if (local_best_sc > global_best_sc) {
                global_best_sc = local_best_sc;
                for (int i = 0; i < 7; i++) {
                    global_best_key[i] = ALPH_K[local_k[i]];
                }
                global_best_key[7] = '\0';

                for (int i = 0; i < N; i++) {
                    int pi = (C[i] - local_k[i % 7] + 26) % 26;
                    global_best_pt[i] = k_to_std[pi] + 'A';
                }
                global_best_pt[N] = '\0';

                printf("  [New Best] Tri: %s | Key: %s | sc=%.4f\n    PT: %.70s...\n",
                       tri_list[t], global_best_key, global_best_sc, global_best_pt);
            }
        }
    }

    double t1 = omp_get_wtime();
    printf("\nFinished in %.2f seconds. Best overall score: %.4f\n", t1 - t0, global_best_sc);
    return 0;
}
