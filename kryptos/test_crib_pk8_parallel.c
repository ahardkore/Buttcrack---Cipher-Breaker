#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>

#define N 153

static const char *ALPH = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
static const char *PK8_CT = "COPVEJJVSVURTVIPYOTPLHGBTMAUCCPESIWIGZBWSJPKTRPUEKQFIFCLHMXTHIMHWOYIGURBOMPARCVXVKBDDVBVHDRHGCVNWWVLBMYWMWHICFIXZWBVZYCQGNOGJGUMLNPUTHQCXNWPQZOIRJZGSWVPY";

static int std_to_kr[26];
static int ct_kr[N];
static float quadgrams[26][26][26][26];

static void init_tables(void) {
    for (int i = 0; i < 26; i++) std_to_kr[ALPH[i] - 'A'] = i;
    for (int i = 0; i < N; i++) ct_kr[i] = std_to_kr[PK8_CT[i] - 'A'];

    for (int a = 0; a < 26; a++)
        for (int b = 0; b < 26; b++)
            for (int c = 0; c < 26; c++)
                for (int d = 0; d < 26; d++)
                    quadgrams[a][b][c][d] = -12.0f;

    FILE *f = fopen("english_quadgrams.txt", "r");
    if (!f) return;
    char line[64];
    long long total = 0;
    while (fgets(line, sizeof(line), f)) {
        char qg[5]; long long cnt;
        if (sscanf(line, "%4s %lld", qg, &cnt) == 2) total += cnt;
    }
    fseek(f, 0, SEEK_SET);
    while (fgets(line, sizeof(line), f)) {
        char qg[5]; long long cnt;
        if (sscanf(line, "%4s %lld", qg, &cnt) == 2) {
            int a = qg[0] - 'A', b = qg[1] - 'A', c = qg[2] - 'A', d = qg[3] - 'A';
            if (a >= 0 && a < 26 && b >= 0 && b < 26 && c >= 0 && c < 26 && d >= 0 && d < 26) {
                quadgrams[a][b][c][d] = log10f((float)cnt / total);
            }
        }
    }
    fclose(f);
}

// Gaussian elimination over Z_26
int solve_linear_z26(int A[32][16], int B[32], int rows, int cols, int sol[16]) {
    int A13[32][16], B13[32];
    for (int i = 0; i < rows; i++) {
        for (int j = 0; j < cols; j++) A13[i][j] = (A[i][j] % 13 + 13) % 13;
        B13[i] = (B[i] % 13 + 13) % 13;
    }
    int r = 0;
    for (int c = 0; c < cols && r < rows; c++) {
        int pivot = -1;
        for (int i = r; i < rows; i++) {
            if (A13[i][c] != 0) { pivot = i; break; }
        }
        if (pivot == -1) continue;
        for (int j = 0; j < cols; j++) { int tmp = A13[r][j]; A13[r][j] = A13[pivot][j]; A13[pivot][j] = tmp; }
        int tmp = B13[r]; B13[r] = B13[pivot]; B13[pivot] = tmp;

        int inv = 1;
        for (int x = 1; x < 13; x++) if ((A13[r][c] * x) % 13 == 1) { inv = x; break; }
        for (int j = 0; j < cols; j++) A13[r][j] = (A13[r][j] * inv) % 13;
        B13[r] = (B13[r] * inv) % 13;

        for (int i = 0; i < rows; i++) {
            if (i != r && A13[i][c] != 0) {
                int factor = A13[i][c];
                for (int j = 0; j < cols; j++) A13[i][j] = (A13[i][j] - factor * A13[r][j] + 130) % 13;
                B13[i] = (B13[i] - factor * B13[r] + 130) % 13;
            }
        }
        r++;
    }
    for (int i = r; i < rows; i++) {
        if (B13[i] != 0) return 0;
    }
    if (r < cols) return 0;

    int sol13[16];
    for (int j = 0; j < cols; j++) sol13[j] = B13[j];

    int A2[32][16], B2[32];
    for (int i = 0; i < rows; i++) {
        for (int j = 0; j < cols; j++) A2[i][j] = (A[i][j] % 2 + 2) % 2;
        B2[i] = (B[i] % 2 + 2) % 2;
    }
    r = 0;
    for (int c = 0; c < cols && r < rows; c++) {
        int pivot = -1;
        for (int i = r; i < rows; i++) {
            if (A2[i][c] != 0) { pivot = i; break; }
        }
        if (pivot == -1) continue;
        for (int j = 0; j < cols; j++) { int t = A2[r][j]; A2[r][j] = A2[pivot][j]; A2[pivot][j] = t; }
        int t = B2[r]; B2[r] = B2[pivot]; B2[pivot] = t;

        for (int i = 0; i < rows; i++) {
            if (i != r && A2[i][c] != 0) {
                for (int j = 0; j < cols; j++) A2[i][j] ^= A2[r][j];
                B2[i] ^= B2[r];
            }
        }
        r++;
    }
    for (int i = r; i < rows; i++) {
        if (B2[i] != 0) return 0;
    }
    if (r < cols) return 0;

    int sol2[16];
    for (int j = 0; j < cols; j++) sol2[j] = B2[j];

    for (int j = 0; j < cols; j++) {
        int diff = (sol2[j] - sol13[j] % 2 + 2) % 2;
        sol[j] = (sol13[j] + 13 * diff) % 26;
    }
    return 1;
}

int main(int argc, char **argv) {
    init_tables();
    int q7[7] = {0, 2, 9, 23, 23, 6, 20};

    const char *crib_file = (argc > 1) ? argv[1] : "pk8_narrative_cribs.txt";
    FILE *fc = fopen(crib_file, "r");
    if (!fc) return 1;

    char (*cribs)[32] = malloc(50000 * sizeof(*cribs));
    int num_cribs = 0;
    while (fscanf(fc, "%31s", cribs[num_cribs]) == 1) {
        if (strlen(cribs[num_cribs]) >= 15) num_cribs++;
    }
    fclose(fc);

    printf("Loaded %d cribs from %s. Starting parallel sweep...\n", num_cribs, crib_file);
    double t0 = omp_get_wtime();

    #pragma omp parallel for schedule(dynamic, 100)
    for (int c_idx = 0; c_idx < num_cribs; c_idx++) {
        char *crib = cribs[c_idx];
        int L = strlen(crib);
        int p_kr[32];
        for (int i = 0; i < L; i++) p_kr[i] = std_to_kr[crib[i] - 'A'];

        for (int t0_pos = 0; t0_pos <= N - L; t0_pos++) {
            for (int c_gauge = 0; c_gauge < 26; c_gauge++) {
                int A[32][16] = {0};
                int B[32] = {0};

                for (int i = 0; i < L; i++) {
                    int pos = t0_pos + i;
                    int r4 = pos % 4;
                    int r5 = pos % 5;
                    int r6 = pos % 6;
                    int r7 = pos % 7;

                    if (r4 > 0) A[i][r4 - 1] = 1;
                    if (r5 > 0) A[i][3 + (r5 - 1)] = 1;
                    A[i][7 + r6] = 1;

                    int k_obs = (ct_kr[pos] - p_kr[i] + 26) % 26;
                    int k_target = (k_obs - (q7[r7] + c_gauge) % 26 + 26) % 26;
                    B[i] = k_target;
                }

                int sol[16];
                if (solve_linear_z26(A, B, L, 13, sol)) {
                    int q4_cand[4] = {0, sol[0], sol[1], sol[2]};
                    int q5_cand[5] = {0, sol[3], sol[4], sol[5], sol[6]};
                    int q6_cand[6] = {sol[7], sol[8], sol[9], sol[10], sol[11], sol[12]};

                    char pt[N + 1];
                    for (int t = 0; t < N; t++) {
                        int k = (q4_cand[t % 4] + q5_cand[t % 5] + q6_cand[t % 6] + q7[t % 7] + c_gauge) % 26;
                        int p = (ct_kr[t] - k + 26) % 26;
                        pt[t] = ALPH[p];
                    }
                    pt[N] = '\0';

                    float sc = 0;
                    for (int t = 0; t < N - 3; t++) {
                        sc += quadgrams[pt[t]-'A'][pt[t+1]-'A'][pt[t+2]-'A'][pt[t+3]-'A'];
                    }
                    float avg_sc = sc / (N - 3);

                    if (avg_sc > -5.5f) {
                        #pragma omp critical
                        {
                            printf("\nHIT! Score = %.2f | Crib: %s at pos %d (c=%d)\n",
                                avg_sc, crib, t0_pos, c_gauge);
                            printf("PT: %s\n", pt);
                        }
                    }
                }
            }
        }
    }

    double t1 = omp_get_wtime();
    printf("Completed all %d cribs in %.2f seconds!\n", num_cribs, t1 - t0);
    free(cribs);
    return 0;
}
