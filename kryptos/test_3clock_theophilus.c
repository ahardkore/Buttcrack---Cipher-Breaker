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

void test_target_3clock(const char *tname, const char *ct_str,
                        char wA[][16], int nA, int pA,
                        char wB[][16], int nB, int pB,
                        char wC[][16], int nC, int pC) {
    int N = strlen(ct_str);
    printf("Testing %s (len %d) with 3 clocks (%d,%d,%d): %d x %d x %d = %ld configs...\n",
           tname, N, pA, pB, pC, nA, nB, nC, (long)nA * nB * nC);

    for (int model = 0; model < 2; model++) {
        const char *alpha = (model == 0) ? KRYPTOS : STD;
        const char *mname = (model == 0) ? "KRYPTOS" : "STD";

        int c_idx[600];
        int alpha_to_std[26];
        for (int i = 0; i < 26; i++) alpha_to_std[i] = alpha[i] - 'A';
        for (int i = 0; i < N; i++) c_idx[i] = strchr(alpha, ct_str[i]) - alpha;

        // Convert wordlists to alpha indices
        int iA[1000][16], iB[1000][16], iC[1000][16];
        for (int i = 0; i < nA; i++)
            for (int j = 0; j < pA; j++) iA[i][j] = strchr(alpha, wA[i][j]) - alpha;
        for (int i = 0; i < nB; i++)
            for (int j = 0; j < pB; j++) iB[i][j] = strchr(alpha, wB[i][j]) - alpha;
        for (int i = 0; i < nC; i++)
            for (int j = 0; j < pC; j++) iC[i][j] = strchr(alpha, wC[i][j]) - alpha;

        #pragma omp parallel for schedule(dynamic)
        for (int a = 0; a < nA; a++) {
            int kA[600];
            for (int j = 0; j < N; j++) kA[j] = iA[a][j % pA];

            for (int b = 0; b < nB; b++) {
                int kAB[600];
                for (int j = 0; j < N; j++) kAB[j] = (kA[j] + iB[b][j % pB]) % 26;

                for (int c = 0; c < nC; c++) {
                    // Check early: first 16 chars
                    int pt[16];
                    for (int j = 0; j < 16; j++) {
                        int k = (kAB[j] + iC[c][j % pC]) % 26;
                        int p = (c_idx[j] - k + 26) % 26;
                        pt[j] = alpha_to_std[p];
                    }
                    float sc_early = 0;
                    for (int j = 0; j < 13; j++)
                        sc_early += quad[pt[j]][pt[j+1]][pt[j+2]][pt[j+3]];
                    if (sc_early < -70.0f) continue;

                    // Full check
                    int pt_full[600];
                    for (int j = 0; j < N; j++) {
                        int k = (kAB[j] + iC[c][j % pC]) % 26;
                        int p = (c_idx[j] - k + 26) % 26;
                        pt_full[j] = alpha_to_std[p];
                    }
                    float sc_full = 0;
                    for (int j = 0; j < N - 3; j++)
                        sc_full += quad[pt_full[j]][pt_full[j+1]][pt_full[j+2]][pt_full[j+3]];
                    sc_full /= (N - 3);

                    if (sc_full > -5.2f) {
                        #pragma omp critical
                        {
                            printf("HIT! [%s] (%s,%s,%s) sc: %6.4f | ",
                                   mname, wA[a], wB[b], wC[c], sc_full);
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

static char w4[1000][16], w5[1000][16], w6[1000][16], w7[1000][16];

int main() {
    load_quadgrams();
    int n4 = load_words("theophilus_w4.txt", w4, 1000, 4);
    int n5 = load_words("theophilus_w5.txt", w5, 1000, 5);
    int n6 = load_words("theophilus_w6.txt", w6, 1000, 6);
    int n7 = load_words("theophilus_w7.txt", w7, 1000, 7);

    printf("Loaded words: L4=%d, L5=%d, L6=%d, L7=%d\n", n4, n5, n6, n7);

    // Test PK8
    test_target_3clock("PK8", PK8_CT, w4, n4, 4, w5, n5, 5, w7, n7, 7);
    test_target_3clock("PK8", PK8_CT, w4, n4, 4, w6, n6, 6, w7, n7, 7);
    test_target_3clock("PK8", PK8_CT, w5, n5, 5, w6, n6, 6, w7, n7, 7);

    // Test PK9
    test_target_3clock("PK9", PK9_CT, w4, n4, 4, w5, n5, 5, w7, n7, 7);
    test_target_3clock("PK9", PK9_CT, w4, n4, 4, w6, n6, 6, w7, n7, 7);
    test_target_3clock("PK9", PK9_CT, w5, n5, 5, w6, n6, 6, w7, n7, 7);

    return 0;
}
