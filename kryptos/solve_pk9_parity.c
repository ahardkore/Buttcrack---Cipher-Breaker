#include <stdio.h>
#include <stdlib.h>
#include <string.h>

const char *KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
const char *STD = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";
const char *PK9_CT = "KSYAWFEYYOISZGEUFBLYATAIBYFAQBQYYVDWJKLJXMYIEPIFVHPQNHZGSUHUUDXLEHRHUMALHEGLHXSJMUXGNUIVBXGUJHZRZGUSVHMLSCTSUQXHSUMQQIFUQGKHJGUQGLHDKEWSKAMHIJXD";

int main() {
    int N = strlen(PK9_CT);
    int c_kryptos[160], c_std[160];
    for (int i = 0; i < N; i++) {
        c_kryptos[i] = (strchr(KRYPTOS, PK9_CT[i]) - KRYPTOS) % 2;
        c_std[i] = (PK9_CT[i] - 'A') % 2;
    }

    printf("Evaluating binary clock states for PK9 (N=144)...\n");

    for (int model = 0; model < 4; model++) {
        const char *mname = (model < 2) ? "KRYPTOS" : "STD";
        int is_beau = (model % 2 == 1);
        int *c_bit = (model < 2) ? c_kryptos : c_std;
        int target_bit = (model < 2) ? 1 : 0;

        // Model 1: {4, 7}
        int max47 = 0, best47_q4[4], best47_q7[7], cnt47 = 0;
        for (int b4 = 0; b4 < 16; b4++) {
            int q4[4] = {b4 & 1, (b4 >> 1) & 1, (b4 >> 2) & 1, (b4 >> 3) & 1};
            for (int b7 = 0; b7 < 64; b7++) {
                int q7[7] = {b7 & 1, (b7 >> 1) & 1, (b7 >> 2) & 1, (b7 >> 3) & 1, (b7 >> 4) & 1, (b7 >> 5) & 1, 0};
                int m = 0;
                for (int i = 0; i < N; i++) {
                    int k = q4[i % 4] ^ q7[i % 7];
                    int p = is_beau ? (k ^ c_bit[i]) : (c_bit[i] ^ k);
                    if (p == target_bit) m++;
                }
                if (m > max47) {
                    max47 = m;
                    for (int k = 0; k < 4; k++) best47_q4[k] = q4[k];
                    for (int k = 0; k < 7; k++) best47_q7[k] = q7[k];
                    cnt47 = 1;
                } else if (m == max47) cnt47++;
            }
        }
        printf("[%s %s] {4, 7}: Max matches = %d / %d (%.2f%%), count = %d\n",
               mname, is_beau ? "Beaufort" : "Vigenere", max47, N, (float)max47 / N * 100.0f, cnt47);
        printf("  q4: [%d, %d, %d, %d], q7: [%d, %d, %d, %d, %d, %d, %d]\n",
               best47_q4[0], best47_q4[1], best47_q4[2], best47_q4[3],
               best47_q7[0], best47_q7[1], best47_q7[2], best47_q7[3],
               best47_q7[4], best47_q7[5], best47_q7[6]);

        // Model 2: {4, 5, 6, 7}
        int max4567 = 0, best_q4[4], best_q5[5], best_q6[6], best_q7[7], cnt_all = 0;
        for (int b4 = 0; b4 < 16; b4++) {
            int q4[4] = {b4 & 1, (b4 >> 1) & 1, (b4 >> 2) & 1, (b4 >> 3) & 1};
            for (int b5 = 0; b5 < 16; b5++) {
                int q5[5] = {b5 & 1, (b5 >> 1) & 1, (b5 >> 2) & 1, (b5 >> 3) & 1, 0};
                for (int b6 = 0; b6 < 32; b6++) {
                    int q6[6] = {b6 & 1, (b6 >> 1) & 1, (b6 >> 2) & 1, (b6 >> 3) & 1, (b6 >> 4) & 1, 0};
                    for (int b7 = 0; b7 < 64; b7++) {
                        int q7[7] = {b7 & 1, (b7 >> 1) & 1, (b7 >> 2) & 1, (b7 >> 3) & 1, (b7 >> 4) & 1, (b7 >> 5) & 1, 0};
                        int m = 0;
                        for (int i = 0; i < N; i++) {
                            int k = q4[i % 4] ^ q5[i % 5] ^ q6[i % 6] ^ q7[i % 7];
                            int p = is_beau ? (k ^ c_bit[i]) : (c_bit[i] ^ k);
                            if (p == target_bit) m++;
                        }
                        if (m > max4567) {
                            max4567 = m;
                            for (int k = 0; k < 4; k++) best_q4[k] = q4[k];
                            for (int k = 0; k < 5; k++) best_q5[k] = q5[k];
                            for (int k = 0; k < 6; k++) best_q6[k] = q6[k];
                            for (int k = 0; k < 7; k++) best_q7[k] = q7[k];
                            cnt_all = 1;
                        } else if (m == max4567) cnt_all++;
                    }
                }
            }
        }
        printf("[%s %s] {4, 5, 6, 7}: Max matches = %d / %d (%.2f%%), count = %d\n",
               mname, is_beau ? "Beaufort" : "Vigenere", max4567, N, (float)max4567 / N * 100.0f, cnt_all);
        printf("  q4: [%d, %d, %d, %d], q5: [%d, %d, %d, %d, %d], q6: [%d, %d, %d, %d, %d, %d], q7: [%d, %d, %d, %d, %d, %d, %d]\n\n",
               best_q4[0], best_q4[1], best_q4[2], best_q4[3],
               best_q5[0], best_q5[1], best_q5[2], best_q5[3], best_q5[4],
               best_q6[0], best_q6[1], best_q6[2], best_q6[3], best_q6[4], best_q6[5],
               best_q7[0], best_q7[1], best_q7[2], best_q7[3], best_q7[4], best_q7[5], best_q7[6]);
    }
    return 0;
}
