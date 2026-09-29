#include <stdio.h>
#include <stdlib.h>
#include <math.h>

const char *KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ";

int main() {
    int shifts[28] = {25, 15, 13, 18, 19, 6, 6, 16, 9, 25, 8, 25, 14, 7, 16, 10, 7, 23, 0, 6, 21, 3, 22, 5, 0, 10, 7, 6};

    int best_err = 9999;
    int best_q4[4], best_q7[7];

    for (int q0 = 0; q0 < 26; q0++) {
        for (int q1 = 0; q1 < 26; q1++) {
            for (int q2 = 0; q2 < 26; q2++) {
                for (int q3 = 0; q3 < 26; q3++) {
                    int q4[4] = {q0, q1, q2, q3};
                    int tot_err = 0;
                    int cur_q7[7];

                    for (int j = 0; j < 7; j++) {
                        int min_dist = 999;
                        int best_v = 0;
                        for (int v = 0; v < 26; v++) {
                            int dist = 0;
                            for (int m = 0; m < 4; m++) {
                                int pos = j + m * 7;
                                int diff = (shifts[pos] - (q4[pos % 4] + v) + 52) % 26;
                                if (diff > 13) diff = 26 - diff;
                                dist += diff;
                            }
                            if (dist < min_dist) {
                                min_dist = dist;
                                best_v = v;
                            }
                        }
                        cur_q7[j] = best_v;
                        tot_err += min_dist;
                    }

                    if (tot_err < best_err) {
                        best_err = tot_err;
                        for (int i = 0; i < 4; i++) best_q4[i] = q4[i];
                        for (int j = 0; j < 7; j++) best_q7[j] = cur_q7[j];
                    }
                }
            }
        }
    }

    printf("Best (q4, q7) Projection:\n");
    printf("Total Error: %d (Avg error per shift: %.2f units mod 26)\n",
           best_err, (float)best_err / 28.0f);
    printf("q4: [%d, %d, %d, %d] (KR: %c%c%c%c)\n",
           best_q4[0], best_q4[1], best_q4[2], best_q4[3],
           KRYPTOS[best_q4[0]], KRYPTOS[best_q4[1]], KRYPTOS[best_q4[2]], KRYPTOS[best_q4[3]]);
    printf("q7: [%d, %d, %d, %d, %d, %d, %d] (KR: %c%c%c%c%c%c%c)\n",
           best_q7[0], best_q7[1], best_q7[2], best_q7[3], best_q7[4], best_q7[5], best_q7[6],
           KRYPTOS[best_q7[0]], KRYPTOS[best_q7[1]], KRYPTOS[best_q7[2]], KRYPTOS[best_q7[3]],
           KRYPTOS[best_q7[4]], KRYPTOS[best_q7[5]], KRYPTOS[best_q7[6]]);

    return 0;
}
