#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>
#include <time.h>

#define N 504
#define L 22
#define N_POS (N - L + 1) // 483

static float quad[26][26][26][26];

void load_quads() {
    for (int a=0; a<26; a++)
        for (int b=0; b<26; b++)
            for (int c=0; c<26; c++)
                for (int d=0; d<26; d++)
                    quad[a][b][c][d] = -9.5f;
    FILE *f = fopen("english_quads.tsv", "r");
    if (!f) { printf("Cannot open english_quads.tsv\n"); exit(1); }
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
static char real_ct10[N + 1];
static int ct_kr[N];
static int ct_std[N];
static int k2std[26];
static int hpos[256];

void load_real_ct10() {
    FILE *f = fopen("pk_all_ciphertexts.json", "r");
    if (!f) { printf("Cannot open json\n"); exit(1); }
    char buf[4096];
    size_t len = fread(buf, 1, sizeof(buf) - 1, f);
    buf[len] = '\0';
    fclose(f);

    char *p = strstr(buf, "\"PK10\": \"");
    p += 9;
    for (int i = 0; i < N; i++) {
        real_ct10[i] = p[i];
        ct_kr[i] = hpos[(unsigned char)p[i]];
        ct_std[i] = p[i] - 'A';
    }
    real_ct10[N] = '\0';
}

static signed char inv_matrices[N_POS][22][22];

void load_inv_matrices() {
    FILE *f = fopen("pk10_inv_matrices.bin", "rb");
    if (!f) { printf("Cannot open pk10_inv_matrices.bin\n"); exit(1); }
    size_t rd = fread(inv_matrices, sizeof(signed char), N_POS * 22 * 22, f);
    fclose(f);
    if (rd != N_POS * 22 * 22) {
        printf("Failed to read all inv matrices (%zu read)\n", rd); exit(1);
    }
    printf("Loaded 483 precomputed inverse matrices (22x22) successfully.\n");
}

typedef struct {
    char str[24];
    int kr[22];
    int std[22];
} Crib;

static Crib *cribs = NULL;
static int n_cribs = 0;

void load_cribs() {
    FILE *f = fopen("pk10_cribs_22.txt", "r");
    if (!f) { printf("Cannot open pk10_cribs_22.txt\n"); exit(1); }
    int cap = 50000;
    cribs = malloc(cap * sizeof(Crib));
    char buf[128];
    while (fscanf(f, "%127s", buf) == 1) {
        if (strlen(buf) >= 22) {
            strncpy(cribs[n_cribs].str, buf, 22);
            cribs[n_cribs].str[22] = '\0';
            for (int i = 0; i < 22; i++) {
                cribs[n_cribs].std[i] = cribs[n_cribs].str[i] - 'A';
                cribs[n_cribs].kr[i] = hpos[(unsigned char)cribs[n_cribs].str[i]];
            }
            n_cribs++;
        }
    }
    fclose(f);
    printf("Loaded %d candidate 22-character cribs.\n", n_cribs);
}

static inline float score_pt_fast(const int *pt) {
    float s = 0.0f;
    for (int i = 0; i < 40; i++) {
        s += quad[pt[i]][pt[i+1]][pt[i+2]][pt[i+3]];
    }
    return s / 40.0f;
}

static inline float score_pt_full(const int *pt) {
    float s = 0.0f;
    for (int i = 0; i < N - 3; i++) {
        s += quad[pt[i]][pt[i+1]][pt[i+2]][pt[i+3]];
    }
    return s / (N - 3);
}

int main() {
    for (int i = 0; i < 26; i++) {
        hpos[(unsigned char)KRYPTOS[i]] = i;
        k2std[i] = KRYPTOS[i] - 'A';
    }
    load_quads();
    load_real_ct10();
    load_inv_matrices();
    load_cribs();

    long total_tests = (long)n_cribs * N_POS;
    printf("Total evaluations to run: %ld (%d cribs x %d positions)\n\n", total_tests, n_cribs, N_POS);

    for (int mode = 0; mode < 2; mode++) {
        printf("======================================================================\n");
        printf("Dragging 22-char cribs under %s...\n", mode == 0 ? "Quagmire III (KRYPTOS)" : "Standard Alphabet");
        printf("======================================================================\n");

        double t0 = omp_get_wtime();
        float best_score = -999.0f;
        char best_crib[24] = "";
        int best_pos = -1;
        char best_pt[N + 1] = "";

        #pragma omp parallel
        {
            float loc_best = -999.0f;
            char loc_crib[24] = "";
            int loc_pos = -1;
            char loc_pt[N + 1] = "";

            #pragma omp for schedule(dynamic, 64)
            for (int c = 0; c < n_cribs; c++) {
                const int *crib_vals = (mode == 0) ? cribs[c].kr : cribs[c].std;

                for (int pos = 0; pos < N_POS; pos++) {
                    // Compute keystream vector b (length 22)
                    int b[22];
                    for (int i = 0; i < 22; i++) {
                        int ct_val = (mode == 0) ? ct_kr[pos + i] : ct_std[pos + i];
                        b[i] = (ct_val - crib_vals[i] + 26) % 26;
                    }

                    // Matrix-vector product mod 26: x = M_inv[pos] * b
                    // x has 22 entries:
                    // x[0..5]: q7[1..6] (since q7[0]=0)
                    // x[6..12]: q8[1..7] (since q8[0]=0)
                    // x[13..21]: q9[0..8] (all 9 vars)
                    int x[22];
                    const signed char (*M)[22] = inv_matrices[pos];

                    for (int i = 0; i < 22; i++) {
                        int sum = 0;
                        for (int j = 0; j < 22; j++) {
                            sum += (int)M[i][j] * b[j];
                        }
                        x[i] = (sum % 26 + 26) % 26;
                    }

                    // Unpack clocks:
                    int q7[7] = {0, x[0], x[1], x[2], x[3], x[4], x[5]};
                    int q8[8] = {0, x[6], x[7], x[8], x[9], x[10], x[11], x[12]};
                    int q9[9] = {x[13], x[14], x[15], x[16], x[17], x[18], x[19], x[20], x[21]};

                    // Fast check on first 43 characters
                    int pt[N];
                    for (int t = 0; t < 43; t++) {
                        int ks = (q7[t % 7] + q8[t % 8] + q9[t % 9]) % 26;
                        if (mode == 0) {
                            int p_kr = (ct_kr[t] - ks + 26) % 26;
                            pt[t] = k2std[p_kr];
                        } else {
                            pt[t] = (ct_std[t] - ks + 26) % 26;
                        }
                    }

                    float s_head = score_pt_fast(pt);
                    if (s_head < -6.8f) continue;

                    // Decrypt full 504 chars
                    for (int t = 43; t < N; t++) {
                        int ks = (q7[t % 7] + q8[t % 8] + q9[t % 9]) % 26;
                        if (mode == 0) {
                            int p_kr = (ct_kr[t] - ks + 26) % 26;
                            pt[t] = k2std[p_kr];
                        } else {
                            pt[t] = (ct_std[t] - ks + 26) % 26;
                        }
                    }

                    float sc = score_pt_full(pt);
                    if (sc > -5.2f) {
                        #pragma omp critical
                        {
                            char full_pt_str[N + 1];
                            for (int t = 0; t < N; t++) full_pt_str[t] = 'A' + pt[t];
                            full_pt_str[N] = '\0';
                            printf(">>> BREAKTHROUGH! Score: %.4f | Crib: %s at pos %d <<<\n", sc, cribs[c].str, pos);
                            printf("  PT: %s\n\n", full_pt_str);
                        }
                    }

                    if (sc > loc_best) {
                        loc_best = sc;
                        strcpy(loc_crib, cribs[c].str);
                        loc_pos = pos;
                        for (int t = 0; t < N; t++) loc_pt[t] = 'A' + pt[t];
                        loc_pt[N] = '\0';
                    }
                }
            }

            #pragma omp critical
            {
                if (loc_best > best_score) {
                    best_score = loc_best;
                    strcpy(best_crib, loc_crib);
                    best_pos = loc_pos;
                    strcpy(best_pt, loc_pt);
                }
            }
        }

        double elapsed = omp_get_wtime() - t0;
        printf("Completed %ld tests in %.3f s (%.1f million tests/sec)!\n",
               total_tests, elapsed, (total_tests / 1e6) / elapsed);
        printf("Best Score: %.4f | Crib: %s at pos %d\n", best_score, best_crib, best_pos);
        printf("PT: %.75s...\n\n", best_pt);
    }

    free(cribs);
    return 0;
}
