#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <omp.h>

const char *KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
const char *PK9_CT = "KSYAWFEYYOISZGEUFBLYATAIBYFAQBQYYVDWJKLJXMYIEPIFVHPQNHZGSUHUUDXLEHRHUMALHEGLHXSJMUXGNUIVBXGUJHZRZGUSVHMLSCTSUQXHSUMQQIFUQGKHJGUQGLHDKEWSKAMHIJXD";

static const int s13[7] = {0, 2, 9, 10, 10, 6, 7};
static const float eng_freq[26] = {
    0.08167, 0.01492, 0.02782, 0.04253, 0.12702, 0.02228, 0.02015,
    0.06094, 0.06966, 0.00153, 0.00772, 0.04025, 0.02406, 0.06749,
    0.07507, 0.01929, 0.00095, 0.05987, 0.06327, 0.09056, 0.02758,
    0.00978, 0.02360, 0.00150, 0.01974, 0.00074
};

int main() {
    int N = strlen(PK9_CT);
    int c_idx[144];
    int alpha_to_std[26];
    for (int i = 0; i < 26; i++) alpha_to_std[i] = KRYPTOS[i] - 'A';
    for (int i = 0; i < N; i++) c_idx[i] = strchr(KRYPTOS, PK9_CT[i]) - KRYPTOS;

    int slice_counts[28][26][26] = {0};
    for (int r = 0; r < 28; r++) {
        for (int s = 0; s < 26; s++) {
            for (int i = r; i < N; i += 28) {
                int p = (c_idx[i] - s + 26) % 26;
                slice_counts[r][s][alpha_to_std[p]]++;
            }
        }
    }

    int q7_candidates[128][7];
    for (int mask = 0; mask < 128; mask++) {
        for (int j = 0; j < 7; j++) {
            int bit = (mask >> j) & 1;
            q7_candidates[mask][j] = (s13[j] + bit * 13) % 26;
        }
    }

    FILE *fout = fopen("top_Z_candidates.txt", "w");
    int count = 0;

    #pragma omp parallel for schedule(dynamic)
    for (int mask = 0; mask < 128; mask++) {
        int q7[7];
        for (int j = 0; j < 7; j++) q7[j] = q7_candidates[mask][j];

        int q4[4];
        for (q4[0] = 0; q4[0] < 26; q4[0]++) {
            for (q4[1] = 0; q4[1] < 26; q4[1]++) {
                for (q4[2] = 0; q4[2] < 26; q4[2]++) {
                    for (q4[3] = 0; q4[3] < 26; q4[3]++) {
                        int tot_counts[26] = {0};
                        for (int r = 0; r < 28; r++) {
                            int shift = (q4[r % 4] + q7[r % 7]) % 26;
                            for (int c = 0; c < 26; c++) {
                                tot_counts[c] += slice_counts[r][shift][c];
                            }
                        }

                        float dot = 0.0f;
                        for (int c = 0; c < 26; c++) dot += tot_counts[c] * eng_freq[c];

                        if (dot >= 7.85f) {
                            #pragma omp critical
                            {
                                char Z[145];
                                for (int i = 0; i < N; i++) {
                                    int shift = (q4[i % 4] + q7[i % 7]) % 26;
                                    int p = (c_idx[i] - shift + 26) % 26;
                                    Z[i] = 'A' + alpha_to_std[p];
                                }
                                Z[N] = '\0';
                                fprintf(fout, "%.4f %d %d %d %d %d %d %d %d %d %d %d %s\n",
                                        dot, q4[0], q4[1], q4[2], q4[3],
                                        q7[0], q7[1], q7[2], q7[3], q7[4], q7[5], q7[6], Z);
                                count++;
                            }
                        }
                    }
                }
            }
        }
    }
    fclose(fout);
    printf("Saved %d candidates with dot >= 7.85\n", count);
    return 0;
}
