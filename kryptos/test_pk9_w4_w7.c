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
static int ct_std[N];

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
        ct_std[i] = PK9_CT[i] - 'A';
    }
}

typedef struct {
    double chi2;
    int rare_cnt;
    int top_cnt;
    char w4[8];
    char w7[10];
    int mode;
    int alph_type;
    char text[N + 1];
} Result;

int main(int argc, char **argv) {
    init_tables();

    const char *f4_name = (argc > 1) ? argv[1] : "theophilus_w4.txt";
    const char *f7_name = (argc > 2) ? argv[2] : "theophilus_w7.txt";

    // Read word lists
    char (*w4_list)[8] = malloc(50000 * sizeof(*w4_list));
    int n4 = 0;
    FILE *f4 = fopen(f4_name, "r");
    if (!f4) { printf("Cannot open %s\n", f4_name); return 1; }
    while (fscanf(f4, "%7s", w4_list[n4]) == 1) {
        if (strlen(w4_list[n4]) == 4) n4++;
    }
    fclose(f4);

    char (*w7_list)[10] = malloc(50000 * sizeof(*w7_list));
    int n7 = 0;
    FILE *f7 = fopen(f7_name, "r");
    if (!f7) { printf("Cannot open %s\n", f7_name); return 1; }
    while (fscanf(f7, "%9s", w7_list[n7]) == 1) {
        if (strlen(w7_list[n7]) == 7) n7++;
    }
    fclose(f7);

    printf("Testing %s (%d) x %s (%d) = %lld pairs\n",
        f4_name, n4, f7_name, n7, (long long)n4 * n7);

    // Precompute numerical representations
    int (*q4_kr)[4] = malloc(n4 * sizeof(*q4_kr));
    int (*q4_std)[4] = malloc(n4 * sizeof(*q4_std));
    for (int i = 0; i < n4; i++) {
        for (int j = 0; j < 4; j++) {
            q4_kr[i][j] = std_to_kr[w4_list[i][j] - 'A'];
            q4_std[i][j] = w4_list[i][j] - 'A';
        }
    }

    int (*q7_kr)[7] = malloc(n7 * sizeof(*q7_kr));
    int (*q7_std)[7] = malloc(n7 * sizeof(*q7_std));
    for (int i = 0; i < n7; i++) {
        for (int j = 0; j < 7; j++) {
            q7_kr[i][j] = std_to_kr[w7_list[i][j] - 'A'];
            q7_std[i][j] = w7_list[i][j] - 'A';
        }
    }

    Result best[20];
    for (int i = 0; i < 20; i++) best[i].chi2 = 1e9;

    double t0 = omp_get_wtime();

    #pragma omp parallel
    {
        Result local_best[20];
        for (int i = 0; i < 20; i++) local_best[i].chi2 = 1e9;

        #pragma omp for schedule(dynamic, 100)
        for (int i4 = 0; i4 < n4; i4++) {
            for (int i7 = 0; i7 < n7; i7++) {
                // Test 4 configurations: (Kryptos/Std) x (Vig/Beau)
                for (int cfg = 0; cfg < 4; cfg++) {
                    int use_kr = (cfg < 2);
                    int is_beau = (cfg % 2 == 1);
                    const int *ct = use_kr ? ct_kr : ct_std;
                    const int *k4 = use_kr ? q4_kr[i4] : q4_std[i4];
                    const int *k7 = use_kr ? q7_kr[i7] : q7_std[i7];

                    int counts[26] = {0};
                    for (int t = 0; t < N; t++) {
                        int k = (k4[t % 4] + k7[t % 7]) % 26;
                        int p = is_beau ? (k - ct[t] + 26) % 26 : (ct[t] - k + 26) % 26;
                        int std_char = use_kr ? (ALPH[p] - 'A') : p;
                        counts[std_char]++;
                    }

                    // Count rare: Q(16), X(23), Z(25), J(9)
                    int rare = counts[16] + counts[23] + counts[25] + counts[9];
                    if (rare > 6) continue; // Early prune! Natural English has <= 2

                    // Top 9 letters: E, T, A, O, I, N, S, H, R
                    int top9 = counts[4] + counts[19] + counts[0] + counts[14] + counts[8] +
                               counts[13] + counts[18] + counts[7] + counts[17];

                    // Compute Chi2 against English
                    double chi2 = 0;
                    for (int a = 0; a < 26; a++) {
                        double exp_cnt = N * eng_freq[a];
                        double diff = counts[a] - exp_cnt;
                        chi2 += (diff * diff) / exp_cnt;
                    }

                    if (chi2 < local_best[19].chi2) {
                        int pos = 19;
                        while (pos > 0 && chi2 < local_best[pos - 1].chi2) {
                            local_best[pos] = local_best[pos - 1];
                            pos--;
                        }
                        local_best[pos].chi2 = chi2;
                        local_best[pos].rare_cnt = rare;
                        local_best[pos].top_cnt = top9;
                        local_best[pos].mode = is_beau;
                        local_best[pos].alph_type = use_kr;
                        strcpy(local_best[pos].w4, w4_list[i4]);
                        strcpy(local_best[pos].w7, w7_list[i7]);

                        // Reconstruct text
                        for (int t = 0; t < N; t++) {
                            int k = (k4[t % 4] + k7[t % 7]) % 26;
                            int p = is_beau ? (k - ct[t] + 26) % 26 : (ct[t] - k + 26) % 26;
                            local_best[pos].text[t] = use_kr ? ALPH[p] : ('A' + p);
                        }
                        local_best[pos].text[N] = '\0';
                    }
                }
            }
        }

        #pragma omp critical
        {
            for (int i = 0; i < 20; i++) {
                double c = local_best[i].chi2;
                if (c < best[19].chi2) {
                    int pos = 19;
                    while (pos > 0 && c < best[pos - 1].chi2) {
                        best[pos] = best[pos - 1];
                        pos--;
                    }
                    best[pos] = local_best[i];
                }
            }
        }
    }

    double t1 = omp_get_wtime();
    printf("Completed in %.3f seconds!\n\n", t1 - t0);

    printf("Top 10 candidates for (w4, w7):\n");
    for (int i = 0; i < 10; i++) {
        if (best[i].chi2 > 1e8) break;
        printf("#%2d: Chi2 = %6.2f | Rare = %d | Top9 = %2d/144 | %s %s | (%s, %s)\n",
            i + 1, best[i].chi2, best[i].rare_cnt, best[i].top_cnt,
            best[i].alph_type ? "Kryptos" : "Standard",
            best[i].mode ? "Beaufort" : "Vigenere",
            best[i].w4, best[i].w7);
        printf("    Z: %s\n", best[i].text);
    }

    return 0;
}
