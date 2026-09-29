#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>

#define N 144

static const char *ALPH = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
static const char *PK9_CT = "KSYAWFEYYOISZGEUFBLYATAIBYFAQBQYYVDWJKLJXMYIEPIFVHPQNHZGSUHUUDXLEHRHUMALHEGLHXSJMUXGNUIVBXGUJHZRZGUSVHMLSCTSUQXHSUMQQIFUQGKHJGUQGLHDKEWSKAMHIJXD";

// English monogram frequencies
static const double eng_freq[26] = {
    0.08167, 0.01492, 0.02782, 0.04253, 0.12702,
    0.02228, 0.02015, 0.06094, 0.06966, 0.00153,
    0.00772, 0.04025, 0.02406, 0.06749, 0.07507,
    0.01929, 0.00095, 0.05987, 0.06327, 0.09056,
    0.02758, 0.00978, 0.02360, 0.00150, 0.01974,
    0.00074
};

static double log_p13[13];
static int c_mod13[N];

void init(void) {
    int std_to_kr[26];
    for (int i = 0; i < 26; i++) std_to_kr[ALPH[i] - 'A'] = i;
    for (int i = 0; i < N; i++) {
        c_mod13[i] = std_to_kr[PK9_CT[i] - 'A'] % 13;
    }

    // Fold English frequencies into Z_13 over Kryptos alphabet
    double p13[13] = {0};
    for (int i = 0; i < 26; i++) {
        int kr = std_to_kr[i];
        p13[kr % 13] += eng_freq[i];
    }
    for (int i = 0; i < 13; i++) {
        log_p13[i] = log(p13[i]);
    }
}

typedef struct {
    double ll;
    int s[7];
} Result;

int main(void) {
    init();

    // Slices
    int slice_len[7] = {0};
    int slices[7][32];
    for (int t = 0; t < N; t++) {
        int r = t % 7;
        slices[r][slice_len[r]++] = c_mod13[t];
    }

    printf("Coset lengths: ");
    for (int r = 0; r < 7; r++) printf("%d ", slice_len[r]);
    printf("\n");

    // Since each coset can be scored independently!
    // LL(s0, s1, ..., s6) = sum_{r=0}^6 LL_r(s_r)!
    // IT DECOUPLES COMPLETELY INTO 7 INDEPENDENT PROBLEMS!
    // EACH COSET HAS ONLY 13 CHOICES!
    // 7 x 13 = 91 EVALUATIONS!
    printf("\n--- Independent Coset Scoring on Z_13 ---\n");
    int best_s[7];
    for (int r = 0; r < 7; r++) {
        double max_ll = -1e9;
        int opt_s = 0;
        printf("Coset %d: ", r);
        for (int s = 0; s < 13; s++) {
            double ll = 0;
            for (int j = 0; j < slice_len[r]; j++) {
                int p = (slices[r][j] - s + 13) % 13;
                ll += log_p13[p];
            }
            if (ll > max_ll) {
                max_ll = ll;
                opt_s = s;
            }
        }
        best_s[r] = opt_s;
        printf("Best shift = %2d (LL = %6.2f)\n", opt_s, max_ll);
    }

    printf("\nDerived modulo-13 shift vector for PK9: [");
    for (int r = 0; r < 7; r++) printf("%d%s", best_s[r], r < 6 ? ", " : "]\n");

    // Normalize with best_s[0] = 0
    int norm_s[7];
    for (int r = 0; r < 7; r++) norm_s[r] = (best_s[r] - best_s[0] + 13) % 13;
    printf("Normalized (s[0]=0): [");
    for (int r = 0; r < 7; r++) printf("%d%s", norm_s[r], r < 6 ? ", " : "]\n");

    // Compare with PK8 s13: [0, 2, 9, 10, 10, 6, 7]
    int pk8_s13[7] = {0, 2, 9, 10, 10, 6, 7};
    printf("PK8 s13:             [");
    for (int r = 0; r < 7; r++) printf("%d%s", pk8_s13[r], r < 6 ? ", " : "]\n");

    int match = 1;
    for (int r = 0; r < 7; r++) {
        if (norm_s[r] != pk8_s13[r]) match = 0;
    }
    printf("Exact match to PK8 s13? %s\n", match ? "YES! 100% IDENTICAL!" : "NO");

    return 0;
}
