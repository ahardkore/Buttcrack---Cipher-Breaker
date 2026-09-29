#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>

static float quad[26][26][26][26];

void load_quadgrams() {
    FILE *f = fopen("english_quadgrams.txt", "r");
    if (!f) { printf("Failed to open english_quadgrams.txt\n"); exit(1); }
    char line[128];
    double total = 0;
    static double counts[26][26][26][26];
    memset(counts, 0, sizeof(counts));
    while (fgets(line, sizeof(line), f)) {
        char gram[5]; double count;
        if (sscanf(line, "%4s %lf", gram, &count) == 2) {
            int a = gram[0] - 'A', b = gram[1] - 'A', c = gram[2] - 'A', d = gram[3] - 'A';
            if (a>=0 && a<26 && b>=0 && b<26 && c>=0 && c<26 && d>=0 && d<26) {
                counts[a][b][c][d] = count;
                total += count;
            }
        }
    }
    fclose(f);
    float floor_val = log10f(0.01f / total);
    for (int a=0; a<26; a++)
        for (int b=0; b<26; b++)
            for (int c=0; c<26; c++)
                for (int d=0; d<26; d++)
                    quad[a][b][c][d] = counts[a][b][c][d] > 0 ? log10f(counts[a][b][c][d] / total) : floor_val;
}

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

static char w4[1000][16], w5[1000][16], w6[1000][16], w7[1000][16];

int main() {
    load_quadgrams();
    int n4 = load_words("theophilus_w4.txt", w4, 1000, 4);
    int n5 = load_words("theophilus_w5.txt", w5, 1000, 5);
    int n6 = load_words("theophilus_w6.txt", w6, 1000, 6);
    int n7 = load_words("theophilus_w7.txt", w7, 1000, 7);
    int N = strlen(PK8_CT);

    printf("Loaded w4:%d, w5:%d, w6:%d, w7:%d\n", n4, n5, n6, n7);

    for (int model = 0; model < 2; model++) {
        const char *alpha = (model == 0) ? KRYPTOS : STD;
        const char *mname = (model == 0) ? "KRYPTOS" : "STD";

        int c_idx[600];
        int alpha_to_std[26];
        for (int i = 0; i < 26; i++) alpha_to_std[i] = alpha[i] - 'A';
        for (int i = 0; i < N; i++) c_idx[i] = strchr(alpha, PK8_CT[i]) - alpha;

        int i4[1000][4], i5[1000][5], i6[1000][6], i7[1000][7];
        for (int i = 0; i < n4; i++) for (int j = 0; j < 4; j++) i4[i][j] = strchr(alpha, w4[i][j]) - alpha;
        for (int i = 0; i < n5; i++) for (int j = 0; j < 5; j++) i5[i][j] = strchr(alpha, w5[i][j]) - alpha;
        for (int i = 0; i < n6; i++) for (int j = 0; j < 6; j++) i6[i][j] = strchr(alpha, w6[i][j]) - alpha;
        for (int i = 0; i < n7; i++) for (int j = 0; j < 7; j++) i7[i][j] = strchr(alpha, w7[i][j]) - alpha;

        // Stage 1: find top candidate pairs (w6, w7)
        #pragma omp parallel for schedule(dynamic)
        for (int a = 0; a < n6; a++) {
            for (int b = 0; b < n7; b++) {
                int k67[42];
                for (int j = 0; j < 42; j++) k67[j] = (i6[a][j % 6] + i7[b][j % 7]) % 26;

                int counts[20][26] = {0};
                for (int j = 0; j < N; j++) {
                    int c_prime = (c_idx[j] - k67[j % 42] + 26) % 26;
                    counts[j % 20][c_prime]++;
                }

                int coinc = 0;
                for (int r = 0; r < 20; r++)
                    for (int c = 0; c < 26; c++)
                        coinc += counts[r][c] * (counts[r][c] - 1) / 2;

                if (coinc >= 38) {
                    // Test all (w4, w5) against this (w6, w7)
                    for (int x = 0; x < n4; x++) {
                        for (int y = 0; y < n5; y++) {
                            // Check first 16 chars
                            int pt[16];
                            for (int j = 0; j < 16; j++) {
                                int k = (i4[x][j % 4] + i5[y][j % 5] + k67[j % 42]) % 26;
                                pt[j] = alpha_to_std[(c_idx[j] - k + 26) % 26];
                            }
                            float sc_early = 0;
                            for (int j = 0; j < 13; j++)
                                sc_early += quad[pt[j]][pt[j+1]][pt[j+2]][pt[j+3]];
                            if (sc_early < -70.0f) continue;

                            // Full score
                            int pt_full[600];
                            for (int j = 0; j < N; j++) {
                                int k = (i4[x][j % 4] + i5[y][j % 5] + k67[j % 42]) % 26;
                                pt_full[j] = alpha_to_std[(c_idx[j] - k + 26) % 26];
                            }
                            float sc_full = 0;
                            for (int j = 0; j < N - 3; j++)
                                sc_full += quad[pt_full[j]][pt_full[j+1]][pt_full[j+2]][pt_full[j+3]];
                            sc_full /= (N - 3);

                            if (sc_full > -5.2f) {
                                #pragma omp critical
                                {
                                    printf("HIT! [%s] (%s, %s, %s, %s) sc=%6.4f | ",
                                           mname, w4[x], w5[y], w6[a], w7[b], sc_full);
                                    for (int j = 0; j < 50; j++) printf("%c", 'A' + pt_full[j]);
                                    printf("\n");
                                    fflush(stdout);
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    printf("Done searching PK8!\n");
    return 0;
}
