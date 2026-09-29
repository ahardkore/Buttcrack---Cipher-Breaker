#include <stdio.h>
#include <stdlib.h>
#include <string.h>

const char *ALPH = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
const char *CT = "KSYAWFEYYOISZGEUFBLYATAIBYFAQBQYYVDWJKLJXMYIEPIFVHPQNHZGSUHUUDXLEHRHUMALHEGLHXSJMUXGNUIVBXGUJHZRZGUSVHMLSCTSUQXHSUMQQIFUQGKHJGUQGLHDKEWSKAMHIJXD";

double ENG_FREQ[26] = {
    8.2, 1.5, 2.8, 4.3, 12.7, 2.2, 2.0, 6.1, 7.0, 0.15, 0.77, 4.0, 2.4,
    6.7, 7.5, 1.9, 0.095, 6.0, 6.3, 9.1, 2.8, 0.98, 2.4, 0.15, 2.0, 0.074
};

int main() {
    int n = strlen(CT);
    int c_arr[144];
    for (int i = 0; i < n; i++) {
        for (int k = 0; k < 26; k++) {
            if (ALPH[k] == CT[i]) {
                c_arr[i] = k;
                break;
            }
        }
    }

    double target[26];
    double sum = 0;
    for (int k = 0; k < 26; k++) {
        char ch = ALPH[k];
        double f = ENG_FREQ[ch - 'A'];
        target[k] = f;
        sum += f;
    }
    for (int k = 0; k < 26; k++) target[k] /= sum;

    double best_chi2 = 1e9;
    int best_A[5] = {0};
    int best_B[7] = {0};

    int pos[7][30];
    int len_r[7] = {0};
    for (int i = 0; i < n; i++) {
        int r = i % 7;
        pos[r][len_r[r]++] = i;
    }

    for (int a1 = 0; a1 < 26; a1++) {
        for (int a2 = 0; a2 < 26; a2++) {
            for (int a3 = 0; a3 < 26; a3++) {
                for (int a4 = 0; a4 < 26; a4++) {
                    int A[5] = {0, a1, a2, a3, a4};
                    double tot_chi2 = 0;
                    int B[7] = {0};

                    for (int r = 0; r < 7; r++) {
                        int counts[26] = {0};
                        int nr = len_r[r];
                        for (int j = 0; j < nr; j++) {
                            int idx_i = pos[r][j];
                            int m5 = idx_i % 5;
                            int val = (c_arr[idx_i] - A[m5] + 26) % 26;
                            counts[val]++;
                        }

                        double best_col_chi2 = 1e9;
                        int best_b = 0;

                        for (int b = 0; b < 26; b++) {
                            double chi = 0;
                            for (int k = 0; k < 26; k++) {
                                int cnt = counts[(k + b) % 26];
                                double exp_cnt = nr * target[k];
                                double diff = cnt - exp_cnt;
                                chi += (diff * diff) / exp_cnt;
                            }
                            if (chi < best_col_chi2) {
                                best_col_chi2 = chi;
                                best_b = b;
                            }
                        }
                        tot_chi2 += best_col_chi2;
                        B[r] = best_b;
                    }

                    if (tot_chi2 < best_chi2) {
                        best_chi2 = tot_chi2;
                        memcpy(best_A, A, sizeof(A));
                        memcpy(best_B, B, sizeof(B));
                        if (best_chi2 < 180.0) {
                            printf("New best chi2 = %6.2f | A=[%d,%d,%d,%d,%d] B=[%d,%d,%d,%d,%d,%d,%d]\n",
                                   best_chi2, A[0], A[1], A[2], A[3], A[4], B[0], B[1], B[2], B[3], B[4], B[5], B[6]);
                        }
                    }
                }
            }
        }
    }

    printf("\n(5, 7) Global Minimum: chi2 = %6.2f\n", best_chi2);
    char pt[145];
    for (int i = 0; i < n; i++) {
        int ks = (best_A[i % 5] + best_B[i % 7]) % 26;
        int p_idx = (c_arr[i] - ks + 26) % 26;
        pt[i] = ALPH[p_idx];
    }
    pt[n] = '\0';
    printf("Decrypted Plaintext:\n%s\n", pt);

    return 0;
}
