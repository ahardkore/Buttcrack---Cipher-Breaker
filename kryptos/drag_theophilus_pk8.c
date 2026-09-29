#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>

#define N 153

const char *KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
const char *PK8_CT = "COPVEJJVSVURTVIPYOTPLHGBTMAUCCPESIWIGZBWSJPKTRPUEKQFIFCLHMXTHIMHWOYIGURBOMPARCVXVKBDDVBVHDRHGCVNWWVLBMYWMWHICFIXZWBVZYCQGNOGJGUMLNPUTHQCXNWPQZOIRJZGSWVPY";

static const int q2_4[4] = {0, 1, 0, 0};
static const int q2_5[5] = {0, 0, 1, 0, 0};
static const int q2_6[6] = {0, 0, 0, 1, 0, 0};
static const int q2_7[7] = {0, 1, 1, 1, 0, 0, 0};

static int c_idx[N];
static int char_to_k[256];

void init_tables() {
    for (int i = 0; i < 256; i++) char_to_k[i] = -1;
    for (int i = 0; i < 26; i++) {
        char_to_k[(unsigned char)KRYPTOS[i]] = i;
    }
    for (int i = 0; i < N; i++) {
        c_idx[i] = char_to_k[(unsigned char)PK8_CT[i]];
    }
}

// Check consistency of k_vals[0..len-1] at position 'start'
// under Q4 + Q5 + Q6 + Q7 in Z13 and Z2
int check_consistency(const int *k_vals, int len, int start) {
    // 1. Binary parity check
    for (int idx = 0; idx < len; idx++) {
        int pos = start + idx;
        int exp_par = (q2_4[pos % 4] + q2_5[pos % 5] + q2_6[pos % 6] + q2_7[pos % 7]) % 2;
        if (k_vals[idx] % 2 != exp_par) return 0;
    }

    // 2. Z13 linear consistency check via Gaussian elimination
    // Variables: q4[0..3] (4), q5[0..4] (5), q6[0..5] (6), q7[0..6] (7). Total 22 variables.
    // Fix gauges: q5[4] = 0, q6[5] = 0, q7[6] = 0.
    int M[32][24];
    for (int r = 0; r < len; r++) {
        int pos = start + r;
        for (int c = 0; c < 23; c++) M[r][c] = 0;
        M[r][pos % 4] = 1;
        M[r][4 + (pos % 5)] = 1;
        M[r][9 + (pos % 6)] = 1;
        M[r][15 + (pos % 7)] = 1;
        M[r][22] = k_vals[r] % 13;
    }

    // Eliminate gauge columns (4+4=8, 9+5=14, 15+6=21)
    // Actually keep full 22 columns
    int num_rows = len;
    int num_cols = 22;
    int r = 0;

    for (int c = 0; c < num_cols && r < num_rows; c++) {
        int pivot = -1;
        for (int i = r; i < num_rows; i++) {
            if (M[i][c] % 13 != 0) { pivot = i; break; }
        }
        if (pivot == -1) continue;

        // Swap
        for (int j = 0; j <= num_cols; j++) {
            int tmp = M[r][j]; M[r][j] = M[pivot][j]; M[pivot][j] = tmp;
        }

        // Scale pivot to 1 in Z13
        int inv = 1;
        int val = (M[r][c] % 13 + 13) % 13;
        // Fermat's Little Theorem: val^11 mod 13
        for (int p = 0; p < 11; p++) inv = (inv * val) % 13;

        for (int j = 0; j <= num_cols; j++) {
            M[r][j] = (M[r][j] * inv) % 13;
        }

        // Eliminate
        for (int i = 0; i < num_rows; i++) {
            if (i != r && M[i][c] % 13 != 0) {
                int factor = (M[i][c] % 13 + 13) % 13;
                for (int j = 0; j <= num_cols; j++) {
                    M[i][j] = (M[i][j] - factor * M[r][j]) % 13;
                    if (M[i][j] < 0) M[i][j] += 13;
                }
            }
        }
        r++;
    }

    // Check for inconsistent rows (0 = non-zero)
    for (int i = r; i < num_rows; i++) {
        if (M[i][num_cols] % 13 != 0) return 0;
    }

    return 1;
}

int main() {
    init_tables();

    FILE *f = fopen("theophilus_hendrie.txt", "r");
    if (!f) {
        printf("Could not open theophilus_hendrie.txt\n");
        return 1;
    }

    fseek(f, 0, SEEK_END);
    long fsize = ftell(f);
    fseek(f, 0, SEEK_SET);

    char *raw = malloc(fsize + 1);
    fread(raw, 1, fsize, f);
    raw[fsize] = 0;
    fclose(f);

    // Extract all uppercase alpha characters
    char *clean = malloc(fsize + 1);
    long clen = 0;
    for (long i = 0; i < fsize; i++) {
        if (isalpha(raw[i])) clean[clen++] = toupper(raw[i]);
    }
    clean[clen] = 0;
    printf("Extracted %ld clean alphabetic characters from Theophilus\n", clen);

    int crib_len = 24;
    printf("Dragging %d-character sliding windows from Theophilus across PK8...\n", crib_len);

    int hits = 0;
    int k_vals[64];

    for (long pos = 0; pos <= clen - crib_len; pos++) {
        // Form crib
        char crib[32];
        for (int i = 0; i < crib_len; i++) crib[i] = clean[pos + i];
        crib[crib_len] = 0;

        for (int start = 0; start <= N - crib_len; start++) {
            // Kryptos Vigenere: p = (c - k) % 26 => k = (c - p) % 26
            for (int idx = 0; idx < crib_len; idx++) {
                int c = c_idx[start + idx];
                int p = char_to_k[(unsigned char)crib[idx]];
                k_vals[idx] = (c - p + 26) % 26;
            }

            if (check_consistency(k_vals, crib_len, start)) {
                hits++;
                printf(">>> HIT (Vigenere) at PK8 pos %d: '%.16s' (Theophilus text pos %ld)\n",
                       start, crib, pos);
                fflush(stdout);
            }
        }
    }

    printf("Search complete. Total hits: %d\n", hits);
    return 0;
}
