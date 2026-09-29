#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

#define N 504

static const char *ALPH = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
static int char_to_kr[256];

void init(void) {
    for (int i = 0; i < 26; i++) char_to_kr[(unsigned char)ALPH[i]] = i;
}

int main(void) {
    init();

    FILE *f = fopen("pk_all_ciphertexts.json", "r");
    char buf[4096];
    fread(buf, 1, sizeof(buf) - 1, f);
    fclose(f);

    char *p = strstr(buf, "\"PK10\": \"");
    p += 9;
    char *end = strchr(p, '"');
    *end = '\0';

    int C[N];
    for (int i = 0; i < N; i++) C[i] = char_to_kr[(unsigned char)p[i]];

    // Fixed q7 from PK8
    int q7[7] = {0, 2, 9, 23, 23, 6, 20};

    // Stride 8: eliminates Q8, depends on Q7 and Q9
    // Stride 8 mod 7 = 1
    // Delta_8 q7[t] = q7[(t+1)%7] - q7[t%7]
    int count_zero_8 = 0;
    printf("Evaluating Stride 8 (eliminates Q8, 496 pairs)...\n");
    for (int t = 0; t < N - 8; t++) {
        int d8_ct = (C[t + 8] - C[t] + 26) % 26;
        int d8_q7 = (q7[(t + 1) % 7] - q7[t % 7] + 26) % 26;
        int diff = (d8_ct - d8_q7 + 26) % 26;
        // diff = (P[t+8] - P[t]) + d9[t % 9]
    }

    // Check raw difference distributions at stride 8 and stride 9
    for (int stride = 1; stride <= 16; stride++) {
        int counts[26] = {0};
        for (int t = 0; t < N - stride; t++) {
            int d = (C[t + stride] - C[t] + 26) % 26;
            counts[d]++;
        }
        int num_pairs = N - stride;
        double ioc = 0;
        for (int d = 0; d < 26; d++) ioc += counts[d] * (counts[d] - 1);
        ioc /= (double)num_pairs * (num_pairs - 1);
        printf("Raw Stride %2d: IoC = %.5f | zeroes = %2d (exp %.1f)\n",
            stride, ioc, counts[0], num_pairs / 26.0);
    }

    return 0;
}
