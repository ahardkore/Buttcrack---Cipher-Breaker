#include <stdio.h>
#include <stdlib.h>
#include <string.h>

const char *KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
const char *STD = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";
const char *PK8_CT = "COPVEJJVSVURTVIPYOTPLHGBTMAUCCPESIWIGZBWSJPKTRPUEKQFIFCLHMXTHIMHWOYIGURBOMPARCVXVKBDDVBVHDRHGCVNWWVLBMYWMWHICFIXZWBVZYCQGNOGJGUMLNPUTHQCXNWPQZOIRJZGSWVPY";

int main() {
    int N = strlen(PK8_CT);
    int c_kryptos[160], c_std[160];
    for (int i = 0; i < N; i++) {
        c_kryptos[i] = (strchr(KRYPTOS, PK8_CT[i]) - KRYPTOS) % 2;
        c_std[i] = (PK8_CT[i] - 'A') % 2;
    }

    printf("Evaluating all 2^19 = 524,288 binary clock states for PK8...\n");

    for (int model = 0; model < 4; model++) {
        const char *mname = (model < 2) ? "KRYPTOS" : "STD";
        int is_beau = (model % 2 == 1);
        int *c_bit = (model < 2) ? c_kryptos : c_std;

        // In KRYPTOS, English letters have 64.02% odd parity (bit = 1)
        // In STD, English letters have 56.83% even parity (bit = 0)
        int target_bit = (model < 2) ? 1 : 0;

        int max_matches = 0;
        int best_q4[4], best_q5[5], best_q6[6], best_q7[7];
        int num_top = 0;

        // Loop over all binary states
        // Fix gauge: q5[4] = 0, q6[5] = 0, q7[6] = 0
        for (int b4 = 0; b4 < 16; b4++) {
            int q4[4] = {b4 & 1, (b4 >> 1) & 1, (b4 >> 2) & 1, (b4 >> 3) & 1};
            for (int b5 = 0; b5 < 16; b5++) {
                int q5[5] = {b5 & 1, (b5 >> 1) & 1, (b5 >> 2) & 1, (b5 >> 3) & 1, 0};
                for (int b6 = 0; b6 < 32; b6++) {
                    int q6[6] = {b6 & 1, (b6 >> 1) & 1, (b6 >> 2) & 1, (b6 >> 3) & 1, (b6 >> 4) & 1, 0};
                    for (int b7 = 0; b7 < 64; b7++) {
                        int q7[7] = {b7 & 1, (b7 >> 1) & 1, (b7 >> 2) & 1, (b7 >> 3) & 1, (b7 >> 4) & 1, (b7 >> 5) & 1, 0};

                        int matches = 0;
                        for (int i = 0; i < N; i++) {
                            int k_bit = q4[i % 4] ^ q5[i % 5] ^ q6[i % 6] ^ q7[i % 7];
                            int p_bit = is_beau ? (k_bit ^ c_bit[i]) : (c_bit[i] ^ k_bit);
                            if (p_bit == target_bit) matches++;
                        }

                        if (matches > max_matches) {
                            max_matches = matches;
                            for (int k = 0; k < 4; k++) best_q4[k] = q4[k];
                            for (int k = 0; k < 5; k++) best_q5[k] = q5[k];
                            for (int k = 0; k < 6; k++) best_q6[k] = q6[k];
                            for (int k = 0; k < 7; k++) best_q7[k] = q7[k];
                            num_top = 1;
                        } else if (matches == max_matches) {
                            num_top++;
                        }
                    }
                }
            }
        }

        printf("[%s %s] Max matches = %d / %d (%.2f%%, expected 50%%), count with max = %d\n",
               mname, is_beau ? "Beaufort" : "Vigenere",
               max_matches, N, (float)max_matches / N * 100.0f, num_top);
        printf("  Best binary clocks:\n");
        printf("  q4: [%d, %d, %d, %d]\n", best_q4[0], best_q4[1], best_q4[2], best_q4[3]);
        printf("  q5: [%d, %d, %d, %d, %d]\n", best_q5[0], best_q5[1], best_q5[2], best_q5[3], best_q5[4]);
        printf("  q6: [%d, %d, %d, %d, %d, %d]\n", best_q6[0], best_q6[1], best_q6[2], best_q6[3], best_q6[4], best_q6[5]);
        printf("  q7: [%d, %d, %d, %d, %d, %d, %d]\n", best_q7[0], best_q7[1], best_q7[2], best_q7[3], best_q7[4], best_q7[5], best_q7[6]);
    }
    return 0;
}
