#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <omp.h>

const char *KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
const char *STD = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";

const char *PK8_CT = "COPVEJJVSVURTVIPYOTPLHGBTMAUCCPESIWIGZBWSJPKTRPUEKQFIFCLHMXTHIMHWOYIGURBOMPARCVXVKBDDVBVHDRHGCVNWWVLBMYWMWHICFIXZWBVZYCQGNOGJGUMLNPUTHQCXNWPQZOIRJZGSWVPY";

int load_words(const char *filename, char words[][16], int max_w, int expected_len) {
    FILE *f = fopen(filename, "r");
    if (!f) return 0;
    char line[64];
    int count = 0;
    while (fgets(line, sizeof(line), f) && count < max_w) {
        line[strcspn(line, "\r\n")] = 0;
        if ((int)strlen(line) == expected_len) {
            strcpy(words[count++], line);
        }
    }
    fclose(f);
    return count;
}

static char w6[1000][16], w7[1000][16];

int main() {
    int n6 = load_words("theophilus_w6.txt", w6, 1000, 6);
    int n7 = load_words("theophilus_w7.txt", w7, 1000, 7);
    int N = strlen(PK8_CT);

    printf("Loaded w6: %d, w7: %d. Total pairs: %d\n", n6, n7, n6 * n7);

    for (int model = 0; model < 2; model++) {
        const char *alpha = (model == 0) ? KRYPTOS : STD;
        const char *mname = (model == 0) ? "KRYPTOS" : "STD";

        int c_idx[600];
        for (int i = 0; i < N; i++) c_idx[i] = strchr(alpha, PK8_CT[i]) - alpha;

        int i6[1000][6], i7[1000][7];
        for (int i = 0; i < n6; i++) for (int j = 0; j < 6; j++) i6[i][j] = strchr(alpha, w6[i][j]) - alpha;
        for (int i = 0; i < n7; i++) for (int j = 0; j < 7; j++) i7[i][j] = strchr(alpha, w7[i][j]) - alpha;

        int best_coinc = 0;
        char best_w6[16] = "", best_w7[16] = "";

        #pragma omp parallel for schedule(dynamic) reduction(max:best_coinc)
        for (int a = 0; a < n6; a++) {
            for (int b = 0; b < n7; b++) {
                int k67[42];
                for (int j = 0; j < 42; j++) k67[j] = (i6[a][j % 6] + i7[b][j % 7]) % 26;

                // Strip k67 from ciphertext to get C'
                // Count coincidences within 20 slices
                int counts[20][26] = {0};
                for (int j = 0; j < N; j++) {
                    int c_prime = (c_idx[j] - k67[j % 42] + 26) % 26;
                    counts[j % 20][c_prime]++;
                }

                int coinc = 0;
                for (int r = 0; r < 20; r++) {
                    for (int c = 0; c < 26; c++) {
                        coinc += counts[r][c] * (counts[r][c] - 1) / 2;
                    }
                }

                if (coinc > best_coinc) {
                    best_coinc = coinc;
                }
                if (coinc >= 40) {
                    #pragma omp critical
                    {
                        printf("  [%s] Hit: (%s, %s) coinc = %d (expected noise ~21.5, English ~36.4)\n",
                               mname, w6[a], w7[b], coinc);
                    }
                }
            }
        }
        printf("[%s] Peak coinc: %d\n", mname, best_coinc);
    }
    return 0;
}
