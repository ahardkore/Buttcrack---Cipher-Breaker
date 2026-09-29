#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>

#define N 144

static const char *ALPH = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
static const char *PK9_CT = "KSYAWFEYYOISZGEUFBLYATAIBYFAQBQYYVDWJKLJXMYIEPIFVHPQNHZGSUHUUDXLEHRHUMALHEGLHXSJMUXGNUIVBXGUJHZRZGUSVHMLSCTSUQXHSUMQQIFUQGKHJGUQGLHDKEWSKAMHIJXD";

static int std_to_kr[26];
static int ct_kr[N];
static int is_rare[26]; // Q(16), X(23), Z(25), J(9) in standard alphabet

// English monogram frequencies
static const double eng_freq[26] = {
    0.08167, 0.01492, 0.02782, 0.04253, 0.12702,
    0.02228, 0.02015, 0.06094, 0.06966, 0.00153,
    0.00772, 0.04025, 0.02406, 0.06749, 0.07507,
    0.01929, 0.00095, 0.05987, 0.06327, 0.09056,
    0.02758, 0.00978, 0.02360, 0.00150, 0.01974,
    0.00074
};

static void init_tables(void) {
    for (int i = 0; i < 26; i++) {
        std_to_kr[ALPH[i] - 'A'] = i;
    }
    for (int i = 0; i < N; i++) {
        ct_kr[i] = std_to_kr[PK9_CT[i] - 'A'];
    }
    memset(is_rare, 0, sizeof(is_rare));
    is_rare['Q' - 'A'] = 1;
    is_rare['X' - 'A'] = 1;
    is_rare['Z' - 'A'] = 1;
    is_rare['J' - 'A'] = 1;
}

typedef struct {
    double chi2;
    int rare;
    char w4[8];
    char w7[10];
    char text[N + 1];
} Hit;

int main(void) {
    init_tables();

    // Read words_4.txt and words_7.txt
    char (*w4_list)[8] = malloc(50000 * sizeof(*w4_list));
    int n4 = 0;
    FILE *f4 = fopen("words_4.txt", "r");
    if (!f4) return 1;
    while (fscanf(f4, "%7s", w4_list[n4]) == 1) {
        if (strlen(w4_list[n4]) == 4) n4++;
    }
    fclose(f4);

    char (*w7_list)[10] = malloc(50000 * sizeof(*w7_list));
    int n7 = 0;
    FILE *f7 = fopen("words_7.txt", "r");
    if (!f7) return 1;
    while (fscanf(f7, "%9s", w7_list[n7]) == 1) {
        if (strlen(w7_list[n7]) == 7) n7++;
    }
    fclose(f7);

    printf("Full Dictionary: w4=%d, w7=%d -> %lld pairs (%lld evaluations with 2 modes)\n",
        n4, n7, (long long)n4 * n7, (long long)n4 * n7 * 2);

    // Precompute numerical shifts for w7
    int (*q7_kr)[7] = malloc(n7 * sizeof(*q7_kr));
    for (int i = 0; i < n7; i++) {
        for (int j = 0; j < 7; j++) {
            q7_kr[i][j] = std_to_kr[w7_list[i][j] - 'A'];
        }
    }

    Hit top_hits[20];
    for (int i = 0; i < 20; i++) top_hits[i].chi2 = 1e9;

    double t0 = omp_get_wtime();
    long long evaluated = 0;

    #pragma omp parallel
    {
        Hit local_hits[20];
        for (int i = 0; i < 20; i++) local_hits[i].chi2 = 1e9;

        // Preallocated thread-local tables
        int R_table[7][26];       // rare counts: [coset][shift]
        int H_table[7][26][26];    // full counts: [coset][shift][letter]

        #pragma omp for schedule(dynamic, 16) reduction(+:evaluated)
        for (int i4 = 0; i4 < n4; i4++) {
            int k4[4];
            for (int j = 0; j < 4; j++) k4[j] = std_to_kr[w4_list[i4][j] - 'A'];

            for (int is_beau = 0; is_beau < 2; is_beau++) {
                // Build tables for this w4 and mode
                for (int r = 0; r < 7; r++) {
                    for (int v = 0; v < 26; v++) {
                        R_table[r][v] = 0;
                        for (int a = 0; a < 26; a++) H_table[r][v][a] = 0;
                    }
                }

                for (int t = 0; t < N; t++) {
                    int r = t % 7;
                    int k_4 = k4[t % 4];
                    int ct_val = ct_kr[t];
                    // If vig: p = ct - k_4 - v
                    // If beau: p = k_4 + v - ct
                    for (int v = 0; v < 26; v++) {
                        int p = is_beau ? (k_4 + v - ct_val + 52) % 26 : (ct_val - k_4 - v + 52) % 26;
                        int std_char = ALPH[p] - 'A';
                        H_table[r][v][std_char]++;
                        if (is_rare[std_char]) R_table[r][v]++;
                    }
                }

                // Now sweep all w7!
                for (int i7 = 0; i7 < n7; i7++) {
                    int *k7 = q7_kr[i7];
                    // Ultra fast rare letter check
                    int rare = R_table[0][k7[0]] + R_table[1][k7[1]] + R_table[2][k7[2]] +
                               R_table[3][k7[3]] + R_table[4][k7[4]] + R_table[5][k7[5]] +
                               R_table[6][k7[6]];

                    if (rare > 3) continue; // Natural English has <= 2 rare letters!

                    // Survives rare filter! Compute full Chi2
                    int counts[26] = {0};
                    for (int a = 0; a < 26; a++) {
                        counts[a] = H_table[0][k7[0]][a] + H_table[1][k7[1]][a] +
                                    H_table[2][k7[2]][a] + H_table[3][k7[3]][a] +
                                    H_table[4][k7[4]][a] + H_table[5][k7[5]][a] +
                                    H_table[6][k7[6]][a];
                    }

                    double chi2 = 0;
                    for (int a = 0; a < 26; a++) {
                        double exp_cnt = N * eng_freq[a];
                        double diff = counts[a] - exp_cnt;
                        chi2 += (diff * diff) / exp_cnt;
                    }

                    if (chi2 < local_hits[19].chi2) {
                        int pos = 19;
                        while (pos > 0 && chi2 < local_hits[pos - 1].chi2) {
                            local_hits[pos] = local_hits[pos - 1];
                            pos--;
                        }
                        local_hits[pos].chi2 = chi2;
                        local_hits[pos].rare = rare;
                        strcpy(local_hits[pos].w4, w4_list[i4]);
                        strcpy(local_hits[pos].w7, w7_list[i7]);

                        // Decrypt text
                        for (int t = 0; t < N; t++) {
                            int k = (k4[t % 4] + k7[t % 7]) % 26;
                            int p = is_beau ? (k - ct_kr[t] + 26) % 26 : (ct_kr[t] - k + 26) % 26;
                            local_hits[pos].text[t] = ALPH[p];
                        }
                        local_hits[pos].text[N] = '\0';
                    }
                }
            }
            evaluated += n7 * 2;
        }

        #pragma omp critical
        {
            for (int i = 0; i < 20; i++) {
                double c = local_hits[i].chi2;
                if (c < top_hits[19].chi2) {
                    int pos = 19;
                    while (pos > 0 && c < top_hits[pos - 1].chi2) {
                        top_hits[pos] = top_hits[pos - 1];
                        pos--;
                    }
                    top_hits[pos] = local_hits[i];
                }
            }
        }
    }

    double t1 = omp_get_wtime();
    printf("Evaluated %lld states in %.2f seconds (%.2f M states/sec)!\n\n",
        evaluated, t1 - t0, (double)evaluated / (t1 - t0) / 1e6);

    printf("Top 10 candidates for (w4, w7):\n");
    for (int i = 0; i < 10; i++) {
        if (top_hits[i].chi2 > 1e8) break;
        printf("#%2d: Chi2 = %6.2f | Rare = %d | (%s, %s)\n",
            i + 1, top_hits[i].chi2, top_hits[i].rare,
            top_hits[i].w4, top_hits[i].w7);
        printf("    Z: %s\n", top_hits[i].text);
    }

    return 0;
}
