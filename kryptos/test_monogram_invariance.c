#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

#define N 144

static const char *ALPH = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
static const char *PK9_REAL = "KSYAWFEYYOISZGEUFBLYATAIBYFAQBQYYVDWJKLJXMYIEPIFVHPQNHZGSUHUUDXLEHRHUMALHEGLHXSJMUXGNUIVBXGUJHZRZGUSVHMLSCTSUQXHSUMQQIFUQGKHJGUQGLHDKEWSKAMHIJXD";

// English monogram probabilities
static const double english_freq[26] = {
    0.08167, 0.01492, 0.02782, 0.04253, 0.12702, 0.02228, 0.02015, // A-G
    0.06094, 0.06966, 0.00153, 0.00772, 0.04025, 0.02406, 0.06749, // H-N
    0.07507, 0.01929, 0.00095, 0.05987, 0.06327, 0.09056, 0.02758, // O-U
    0.00978, 0.02360, 0.00150, 0.01974, 0.00074                    // V-Z
};

static int ct_kr[N];
static int ct_std[N];
static int kr_to_std[26];
static int std_to_kr[26];

void init() {
    for (int a = 0; a < 26; a++) {
        kr_to_std[a] = ALPH[a] - 'A';
        std_to_kr[ALPH[a] - 'A'] = a;
    }
    for (int i = 0; i < N; i++) {
        ct_kr[i] = std_to_kr[PK9_REAL[i] - 'A'];
        ct_std[i] = PK9_REAL[i] - 'A';
    }
}

// Compute Chi-square of decrypted multiset
double eval_chi2(const int *shifts, int mode) {
    int counts[26] = {0};
    for (int i = 0; i < N; i++) {
        int sh = shifts[i % 28];
        int p_val;
        if (mode == 0) { // Vigenere Std
            p_val = (ct_std[i] - sh + 26) % 26;
        } else if (mode == 1) { // Beaufort Std: P = K - C
            p_val = (sh - ct_std[i] + 26) % 26;
        } else if (mode == 2) { // Vigenere Kryptos
            int kr_p = (ct_kr[i] - sh + 26) % 26;
            p_val = kr_to_std[kr_p];
        } else { // Beaufort Kryptos: P = K - C
            int kr_p = (sh - ct_kr[i] + 26) % 26;
            p_val = kr_to_std[kr_p];
        }
        counts[p_val]++;
    }

    double chi2 = 0.0;
    for (int a = 0; a < 26; a++) {
        double exp = N * english_freq[a];
        double diff = counts[a] - exp;
        chi2 += (diff * diff) / exp;
    }
    return chi2;
}

int main() {
    init();
    printf("Evaluating best independent 28 shifts for each mode via slice-wise log-likelihood and Chi2...\n");

    for (int mode = 0; mode < 4; mode++) {
        const char *mname[] = {"Vigenere Std", "Beaufort Std", "Vigenere Kryptos", "Beaufort Kryptos"};
        int best_shifts[28];

        for (int s = 0; s < 28; s++) {
            double best_score = -1e9;
            int best_sh = 0;

            for (int sh = 0; sh < 26; sh++) {
                double cur_score = 0.0;
                for (int i = s; i < N; i += 28) {
                    int p_val;
                    if (mode == 0) p_val = (ct_std[i] - sh + 26) % 26;
                    else if (mode == 1) p_val = (sh - ct_std[i] + 26) % 26;
                    else if (mode == 2) {
                        int kr_p = (ct_kr[i] - sh + 26) % 26;
                        p_val = kr_to_std[kr_p];
                    } else {
                        int kr_p = (sh - ct_kr[i] + 26) % 26;
                        p_val = kr_to_std[kr_p];
                    }
                    cur_score += log(english_freq[p_val] + 0.0001);
                }
                if (cur_score > best_score) {
                    best_score = cur_score;
                    best_sh = sh;
                }
            }
            best_shifts[s] = best_sh;
        }

        double chi2 = eval_chi2(best_shifts, mode);
        printf("\nMode %d (%s): Chi2 = %.2f\n", mode, mname[mode], chi2);
        printf("Shifts: [");
        for (int s = 0; s < 28; s++) printf("%d%s", best_shifts[s], s==27?"":", ");
        printf("]\n");

        // Print decrypted letter counts
        int counts[26] = {0};
        for (int i = 0; i < N; i++) {
            int sh = best_shifts[i % 28];
            int p_val;
            if (mode == 0) p_val = (ct_std[i] - sh + 26) % 26;
            else if (mode == 1) p_val = (sh - ct_std[i] + 26) % 26;
            else if (mode == 2) {
                int kr_p = (ct_kr[i] - sh + 26) % 26;
                p_val = kr_to_std[kr_p];
            } else {
                int kr_p = (sh - ct_kr[i] + 26) % 26;
                p_val = kr_to_std[kr_p];
            }
            counts[p_val]++;
        }
        printf("Letters (A-Z): ");
        for (int a = 0; a < 26; a++) printf("%c:%d ", 'A'+a, counts[a]);
        printf("\n");
    }

    return 0;
}
