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

// Modular inverse mod 26
static int inv26(int a) {
    a = (a % 26 + 26) % 26;
    for (int x = 1; x < 26; x++) {
        if ((a * x) % 26 == 1) return x;
    }
    return -1; // Not invertible
}

// Gaussian elimination over Z_26
// Returns 1 if unique solution found, 0 otherwise
int solve_linear_z26(int A[32][16], int B[32], int rows, int cols, int sol[16]) {
    // We solve mod 13 and mod 2 separately using CRT
    // Mod 13
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
        // Swap rows
        for (int j = 0; j < cols; j++) { int tmp = A13[r][j]; A13[r][j] = A13[pivot][j]; A13[pivot][j] = tmp; }
        int tmp = B13[r]; B13[r] = B13[pivot]; B13[pivot] = tmp;

        // Scale pivot to 1 mod 13
        int inv = 1;
        for (int x = 1; x < 13; x++) if ((A13[r][c] * x) % 13 == 1) { inv = x; break; }
        for (int j = 0; j < cols; j++) A13[r][j] = (A13[r][j] * inv) % 13;
        B13[r] = (B13[r] * inv) % 13;

        // Eliminate
        for (int i = 0; i < rows; i++) {
            if (i != r && A13[i][c] != 0) {
                int factor = A13[i][c];
                for (int j = 0; j < cols; j++) A13[i][j] = (A13[i][j] - factor * A13[r][j] + 130) % 13;
                B13[i] = (B13[i] - factor * B13[r] + 130) % 13;
            }
        }
        r++;
    }
    // Check consistency mod 13
    for (int i = r; i < rows; i++) {
        if (B13[i] != 0) return 0; // Inconsistent
    }
    if (r < cols) return 0; // Underdetermined

    int sol13[16];
    for (int j = 0; j < cols; j++) sol13[j] = B13[j];

    // Mod 2
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

    // Reconstruct mod 26 via CRT: sol = sol13 + 13 * ((sol2 - sol13) mod 2)
    for (int j = 0; j < cols; j++) {
        int diff = (sol2[j] - sol13[j] % 2 + 2) % 2;
        sol[j] = (sol13[j] + 13 * diff) % 26;
    }
    return 1;
}

int main(void) {
    init_tables();

    // Known q7
    int q7[7] = {0, 2, 9, 23, 23, 6, 20};

    // Test cribs from file
    FILE *fc = fopen("pk8_artisan_cribs.txt", "r");
    if (!fc) return 1;

    char crib[32];
    int crib_count = 0;
    int tested = 0;
    double t0 = omp_get_wtime();

    printf("Testing needlemaking cribs on PK8 across all positions...\n");

    while (fscanf(fc, "%31s", crib) == 1) {
        int L = strlen(crib);
        if (L < 15) continue;
        crib_count++;

        // Convert crib to Kryptos indices
        int p_kr[32];
        for (int i = 0; i < L; i++) p_kr[i] = std_to_kr[crib[i] - 'A'];

        for (int t0_pos = 0; t0_pos <= N - L; t0_pos++) {
            for (int c_gauge = 0; c_gauge < 26; c_gauge++) {
                // Build linear system for q4[1..3] (3 vars), q5[1..4] (4 vars), q6[0..5] (6 vars)
                // Total cols = 13 variables:
                // vars 0..2: q4[1..3] (with q4[0] = 0)
                // vars 3..6: q5[1..4] (with q5[0] = 0)
                // vars 7..12: q6[0..5]
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
                    // Unique consistent solution!
                    int q4_cand[4] = {0, sol[0], sol[1], sol[2]};
                    int q5_cand[5] = {0, sol[3], sol[4], sol[5], sol[6]};
                    int q6_cand[6] = {sol[7], sol[8], sol[9], sol[10], sol[11], sol[12]};

                    // Decrypt entire PK8!
                    char pt[N + 1];
                    for (int t = 0; t < N; t++) {
                        int k = (q4_cand[t % 4] + q5_cand[t % 5] + q6_cand[t % 6] + q7[t % 7] + c_gauge) % 26;
                        int p = (ct_kr[t] - k + 26) % 26;
                        pt[t] = ALPH[p];
                    }
                    pt[N] = '\0';

                    // Score quadgrams
                    float sc = 0;
                    for (int t = 0; t < N - 3; t++) {
                        sc += quadgrams[pt[t]-'A'][pt[t+1]-'A'][pt[t+2]-'A'][pt[t+3]-'A'];
                    }
                    float avg_sc = sc / (N - 3);

                    if (avg_sc > -6.0f) {
                        printf("\nHIT! Score = %.2f | Crib: %s at pos %d (c=%d)\n",
                            avg_sc, crib, t0_pos, c_gauge);
                        printf("PT: %s\n", pt);
                    }
                }
                tested++;
            }
        }
    }
    fclose(fc);

    double t1 = omp_get_wtime();
    printf("Completed %d tests across %d cribs in %.2f seconds!\n", tested, crib_count, t1 - t0);

    return 0;
}
