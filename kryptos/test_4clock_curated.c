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
const char *PK9_CT = "CLQASVMEIXEDQJJQETHEWLYXCOCSBOUVTYAPQYFFJUSNWSJQUZGSMRGZXQCSLMRURKCSMHOFGYXESZCGYUXEWWYVAPEKVJCOZAYKLRXQVYCKBOSXOGGZAMUHQGKHYJUQGLTMRCSXQEXCGGTYAKCOZAGHSPAZVMAH";

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

void test_target_4clock(const char *tname, const char *ct_str,
                        char w4[][16], int n4,
                        char w5[][16], int n5,
                        char w6[][16], int n6,
                        char w7[][16], int n7) {
    int N = strlen(ct_str);
    printf("Testing %s (len %d): %d x %d x %d x %d = %ld configs...\n",
           tname, N, n4, n5, n6, n7, (long)n4 * n5 * n6 * n7);

    for (int model = 0; model < 2; model++) {
        const char *alpha = (model == 0) ? KRYPTOS : STD;
        const char *mname = (model == 0) ? "KRYPTOS" : "STD";

        int c_idx[600];
        int alpha_to_std[26];
        for (int i = 0; i < 26; i++) alpha_to_std[i] = alpha[i] - 'A';
        for (int i = 0; i < N; i++) c_idx[i] = strchr(alpha, ct_str[i]) - alpha;

        int i4[100][16], i5[100][16], i6[100][16], i7[100][16];
        for (int i = 0; i < n4; i++) for (int j = 0; j < 4; j++) i4[i][j] = strchr(alpha, w4[i][j]) - alpha;
        for (int i = 0; i < n5; i++) for (int j = 0; j < 5; j++) i5[i][j] = strchr(alpha, w5[i][j]) - alpha;
        for (int i = 0; i < n6; i++) for (int j = 0; j < 6; j++) i6[i][j] = strchr(alpha, w6[i][j]) - alpha;
        for (int i = 0; i < n7; i++) for (int j = 0; j < 7; j++) i7[i][j] = strchr(alpha, w7[i][j]) - alpha;

        #pragma omp parallel for schedule(dynamic)
        for (int a = 0; a < n4; a++) {
            for (int b = 0; b < n5; b++) {
                int kAB[600];
                for (int j = 0; j < N; j++) kAB[j] = (i4[a][j % 4] + i5[b][j % 5]) % 26;

                for (int c = 0; c < n6; c++) {
                    int kABC[600];
                    for (int j = 0; j < N; j++) kABC[j] = (kAB[j] + i6[c][j % 6]) % 26;

                    for (int d = 0; d < n7; d++) {
                        // Check early: 16 chars
                        int pt[16];
                        for (int j = 0; j < 16; j++) {
                            int k = (kABC[j] + i7[d][j % 7]) % 26;
                            int p = (c_idx[j] - k + 26) % 26;
                            pt[j] = alpha_to_std[p];
                        }
                        float sc_early = 0;
                        for (int j = 0; j < 13; j++) sc_early += quad[pt[j]][pt[j+1]][pt[j+2]][pt[j+3]];
                        if (sc_early < -70.0f) continue;

                        // Check full
                        int pt_full[600];
                        for (int j = 0; j < N; j++) {
                            int k = (kABC[j] + i7[d][j % 7]) % 26;
                            int p = (c_idx[j] - k + 26) % 26;
                            pt_full[j] = alpha_to_std[p];
                        }
                        float sc_full = 0;
                        for (int j = 0; j < N - 3; j++)
                            sc_full += quad[pt_full[j]][pt_full[j+1]][pt_full[j+2]][pt_full[j+3]];
                        sc_full /= (N - 3);

                        if (sc_full > -5.0f) {
                            #pragma omp critical
                            {
                                printf("HIT! [%s] (%s,%s,%s,%s) sc: %6.4f | ",
                                       mname, w4[a], w5[b], w6[c], w7[d], sc_full);
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

static char w4[100][16], w5[100][16], w6[100][16], w7[100][16];

int main() {
    load_quadgrams();
    int n4 = load_words("curated_w4.txt", w4, 51, 4);
    int n5 = load_words("curated_w5.txt", w5, 48, 5);
    int n6 = load_words("curated_w6.txt", w6, 46, 6);
    int n7 = load_words("curated_w7.txt", w7, 37, 7);

    printf("Loaded curated words: L4=%d, L5=%d, L6=%d, L7=%d\n", n4, n5, n6, n7);

    test_target_4clock("PK8", PK8_CT, w4, n4, w5, n5, w6, n6, w7, n7);
    test_target_4clock("PK9", PK9_CT, w4, n4, w5, n5, w6, n6, w7, n7);

    return 0;
}
