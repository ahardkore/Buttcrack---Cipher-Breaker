#include <stdio.h>
#include <stdlib.h>
#include <string.h>

// Gaussian elimination over Z_26 for 12 variables
int solve_linear_z26(int A[32][16], int B[32], int rows, int cols, int sol[16]) {
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

    // CRT reconstruction: sol = sol13 + 13 * ((sol2 - sol13) mod 2)
    for (int j = 0; j < cols; j++) {
        int diff = (sol2[j] - sol13[j] % 2 + 2) % 2;
        sol[j] = (sol13[j] + 13 * diff) % 26;
    }
    return 1;
}

int main() {
    int q4[4] = {0, 5, 12, 19};
    int q5[5] = {0, 8, 15, 21, 3};
    int q6[6] = {4, 11, 2, 9, 16, 0};
    int q7[7] = {0, 2, 9, 23, 23, 6, 20};

    int A[32][16] = {0};
    int B[32] = {0};
    for (int i = 0; i < 16; i++) {
        int r4 = i % 4, r5 = i % 5, r6 = i % 6, r7 = i % 7;
        if (r4 > 0) A[i][r4 - 1] = 1;
        if (r5 > 0) A[i][3 + r5 - 1] = 1;
        if (r6 < 5) A[i][7 + r6] = 1;
        B[i] = (q4[r4] + q5[r5] + q6[r6]) % 26;
    }

    int sol[16];
    int ok = solve_linear_z26(A, B, 16, 12, sol);
    printf("solve_linear_z26 returned: %d\n", ok);
    if (ok) {
        printf("Sol: ");
        for (int i = 0; i < 12; i++) printf("%d ", sol[i]);
        printf("\n");
        int exp[12] = {5, 12, 19, 8, 15, 21, 3, 4, 11, 2, 9, 16};
        printf("Exp: ");
        for (int i = 0; i < 12; i++) printf("%d ", exp[i]);
        printf("\n");
    }
    return 0;
}
