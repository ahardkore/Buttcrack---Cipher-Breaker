#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

static const char *ALPH = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
static int char_to_kr[256];
static int char_to_std[256];
static double log_p_diff[26];

static void init_tables(void) {
    for (int i = 0; i < 26; i++) {
        char_to_kr[(unsigned char)ALPH[i]] = i;
        char_to_std['A' + i] = i;
    }
    double eng[26] = {
        0.08167, 0.01492, 0.02782, 0.04253, 0.12702,
        0.02228, 0.02015, 0.06094, 0.06966, 0.00153,
        0.00772, 0.04025, 0.02406, 0.06749, 0.07507,
        0.01929, 0.00095, 0.05987, 0.06327, 0.09056,
        0.02758, 0.00978, 0.02360, 0.00150, 0.01974,
        0.00074
    };
    for (int d = 0; d < 26; d++) {
        double sum = 0;
        for (int a = 0; a < 26; a++) {
            sum += eng[a] * eng[(a + d) % 26];
        }
        log_p_diff[d] = log(sum);
    }
}

int main(void) {
    init_tables();

    // Read PK10 from pk_all_ciphertexts.json
    FILE *f = fopen("pk_all_ciphertexts.json", "r");
    if (!f) { printf("Cannot open pk_all_ciphertexts.json\n"); return 1; }
    char buf[4096];
    size_t len = fread(buf, 1, sizeof(buf) - 1, f);
    buf[len] = '\0';
    fclose(f);

    char *p = strstr(buf, "\"PK10\": \"");
    if (!p) { printf("Cannot find PK10 in json\n"); return 1; }
    p += 9;
    char *end = strchr(p, '"');
    if (!end) { printf("Bad format\n"); return 1; }
    *end = '\0';

    int N = strlen(p);
    printf("PK10 ciphertext length: %d\n", N);

    int C_kr[504], C_std[504];
    for (int i = 0; i < N; i++) {
        C_kr[i] = char_to_kr[(unsigned char)p[i]];
        C_std[i] = char_to_std[(unsigned char)p[i]];
    }

    int stride = 72;
    int num_pairs = N - stride; // 432 pairs!

    // The PK8 d7 vector:
    int d7_pk8[7] = {9, 21, 14, 9, 23, 20, 8};

    // Test d7_pk8 under Kryptos and Standard alphabets
    for (int alph = 0; alph < 2; alph++) {
        int *C = (alph == 0) ? C_kr : C_std;
        const char *alph_name = (alph == 0) ? "Kryptos" : "Standard";

        double ll = 0;
        int zeroes = 0;
        for (int t = 0; t < num_pairs; t++) {
            int d72 = (C[t + stride] - C[t] + 26) % 26;
            int diff_P = (d72 - d7_pk8[t % 7] + 26) % 26;
            ll += log_p_diff[diff_P];
            if (diff_P == 0) zeroes++;
        }

        // Random baseline:
        double rand_ll = 0;
        for (int d = 0; d < 26; d++) rand_ll += log_p_diff[d] / 26.0;
        rand_ll *= num_pairs;
        double exp_zeroes = num_pairs * 0.065;

        printf("\n=== Alphabet: %s ===\n", alph_name);
        printf("With PK8 d7 vector:\n");
        printf("  Log-Likelihood: %8.2f (Random baseline: %8.2f)\n", ll, rand_ll);
        printf("  Exact Zeroes:   %d (Random expectation: %.1f)\n", zeroes, exp_zeroes);
    }

    return 0;
}
