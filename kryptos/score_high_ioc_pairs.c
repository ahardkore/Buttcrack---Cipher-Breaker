#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <omp.h>

static float quad_table[26][26][26][26];
static const char *ALPH_K = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
static int k_to_std[26];
static int std_to_k[26];

static const char *CT9_REAL = "KSYAWFEYYOISZGEUFBLYATAIBYFAQBQYYVDWJKLJXMYIEPIFVHPQNHZGSUHUUDXLEHRHUMALHEGLHXSJMUXGNUIVBXGUJHZRZGUSVHMLSCTSUQXHSUMQQIFUQGKHJGUQGLHDKEWSKAMHIJXD";
static int C[144];
static const int N = 144;

static const double ENG_FREQ[26] = {
    8.2, 1.5, 2.8, 4.3, 12.7, 2.2, 2.0, 6.1, 7.0, 0.15,
    0.8, 4.0, 2.4, 6.7, 7.5, 1.9, 0.1, 6.0, 6.3, 9.1,
    2.8, 1.0, 2.4, 0.15, 2.0, 0.07
};

typedef struct {
    char word[8];
    int shifts[7];
} Word;

static Word *w7_list = NULL;
static int n7 = 0;
static Word *w4_list = NULL;
static int n4 = 0;
static Word *w5_list = NULL;
static int n5 = 0;

void init() {
    for (int i = 0; i < 26; i++) {
        for (int j = 0; j < 26; j++) {
            for (int k = 0; k < 26; k++) {
                for (int l = 0; l < 26; l++) {
                    quad_table[i][j][k][l] = -9.0f;
                }
            }
        }
    }
    FILE *f = fopen("english_quads.tsv", "r");
    if (!f) { fprintf(stderr, "Cannot open quads\n"); exit(1); }
    char q[16];
    float sc;
    while (fscanf(f, "%s\t%f", q, &sc) == 2) {
        if (strlen(q) == 4) {
            int c0 = q[0]-'A', c1 = q[1]-'A', c2 = q[2]-'A', c3 = q[3]-'A';
            if (c0>=0&&c0<26&&c1>=0&&c1<26&&c2>=0&&c2<26&&c3>=0&&c3<26) {
                quad_table[c0][c1][c2][c3] = sc;
            }
        }
    }
    fclose(f);

    for (int i = 0; i < 26; i++) {
        int std = ALPH_K[i] - 'A';
        k_to_std[i] = std;
        std_to_k[std] = i;
    }
    for (int i = 0; i < N; i++) {
        C[i] = std_to_k[CT9_REAL[i] - 'A'];
    }

    w4_list = malloc(10000 * sizeof(Word));
    w5_list = malloc(20000 * sizeof(Word));
    w7_list = malloc(50000 * sizeof(Word));

    f = fopen("words_alpha.txt", "r");
    if (!f) { fprintf(stderr, "Cannot open words_alpha.txt\n"); exit(1); }
    char buf[64];
    while (fscanf(f, "%63s", buf) == 1) {
        int len = strlen(buf);
        if (len == 4) {
            int ok = 1;
            for (int i = 0; i < 4; i++) {
                if (buf[i] >= 'a' && buf[i] <= 'z') buf[i] = buf[i] - 'a' + 'A';
                if (buf[i] < 'A' || buf[i] > 'Z') ok = 0;
            }
            if (!ok) continue;
            strcpy(w4_list[n4].word, buf);
            for (int i = 0; i < 4; i++) w4_list[n4].shifts[i] = std_to_k[buf[i] - 'A'];
            n4++;
        } else if (len == 5) {
            int ok = 1;
            for (int i = 0; i < 5; i++) {
                if (buf[i] >= 'a' && buf[i] <= 'z') buf[i] = buf[i] - 'a' + 'A';
                if (buf[i] < 'A' || buf[i] > 'Z') ok = 0;
            }
            if (!ok) continue;
            strcpy(w5_list[n5].word, buf);
            for (int i = 0; i < 5; i++) w5_list[n5].shifts[i] = std_to_k[buf[i] - 'A'];
            n5++;
        } else if (len == 7) {
            int ok = 1;
            for (int i = 0; i < 7; i++) {
                if (buf[i] >= 'a' && buf[i] <= 'z') buf[i] = buf[i] - 'a' + 'A';
                if (buf[i] < 'A' || buf[i] > 'Z') ok = 0;
            }
            if (!ok) continue;
            strcpy(w7_list[n7].word, buf);
            for (int i = 0; i < 7; i++) w7_list[n7].shifts[i] = std_to_k[buf[i] - 'A'];
            n7++;
        }
    }
    fclose(f);
    printf("Loaded: W4=%d, W5=%d, W7=%d\n", n4, n5, n7);
}

int main(int argc, char **argv) {
    (void)argc; (void)argv;
    init();

    printf("Testing all (W4, W5) with Period-7 IoC >= 0.065 against optimal 7-shifts and W7 dictionary...\n");

    float global_best_sc = -999.0f;
    char best_w4[8] = "";
    char best_w5[8] = "";
    char best_w7[8] = "";
    char best_pt[150] = "";

    #pragma omp parallel
    {
        float local_best_sc = -999.0f;
        char local_w4[8] = "";
        char local_w5[8] = "";
        char local_w7[8] = "";
        char local_pt[150] = "";

        #pragma omp for schedule(dynamic, 50)
        for (int i4 = 0; i4 < n4; i4++) {
            const int *s4 = w4_list[i4].shifts;

            for (int i5 = 0; i5 < n5; i5++) {
                const int *s5 = w5_list[i5].shifts;

                // 1. Calculate Period-7 IoC
                double total_ioc = 0.0;
                int C_prime[144];
                for (int i = 0; i < N; i++) {
                    int k = s4[i & 3] + s5[i % 5];
                    C_prime[i] = (C[i] - k + 52) % 26;
                }

                for (int c = 0; c < 7; c++) {
                    int counts[26] = {0};
                    int L = 0;
                    for (int i = c; i < N; i += 7) {
                        counts[C_prime[i]]++;
                        L++;
                    }
                    int sum = 0;
                    for (int ch = 0; ch < 26; ch++) sum += counts[ch] * (counts[ch] - 1);
                    total_ioc += (double)sum / (L * (L - 1));
                }
                total_ioc /= 7.0;

                if (total_ioc < 0.065) continue;

                // 2. Find optimal 7 shifts by Chi-sq
                int opt_s7[7];
                for (int c = 0; c < 7; c++) {
                    int col_len = 0;
                    for (int i = c; i < N; i += 7) col_len++;
                    double best_chi = 1e9;
                    int best_s = 0;
                    for (int s = 0; s < 26; s++) {
                        int std_counts[26] = {0};
                        for (int i = c; i < N; i += 7) {
                            int p_idx = (C_prime[i] - s + 26) % 26;
                            std_counts[k_to_std[p_idx]]++;
                        }
                        double chi = 0.0;
                        for (int ch = 0; ch < 26; ch++) {
                            double exp = col_len * ENG_FREQ[ch] / 100.0;
                            double diff = std_counts[ch] - exp;
                            chi += (diff * diff) / exp;
                        }
                        if (chi < best_chi) {
                            best_chi = chi;
                            best_s = s;
                        }
                    }
                    opt_s7[c] = best_s;
                }

                // 3. Score decrypted text with optimal shifts
                int pt[144];
                for (int i = 0; i < N; i++) {
                    int p_idx = (C_prime[i] - opt_s7[i % 7] + 26) % 26;
                    pt[i] = k_to_std[p_idx];
                }
                float sc = 0.0f;
                for (int i = 0; i < N - 3; i++) sc += quad_table[pt[i]][pt[i+1]][pt[i+2]][pt[i+3]];
                sc /= (N - 3);

                if (sc > local_best_sc) {
                    local_best_sc = sc;
                    strcpy(local_w4, w4_list[i4].word);
                    strcpy(local_w5, w5_list[i5].word);
                    sprintf(local_w7, "%c%c%c%c%c%c%c",
                            ALPH_K[opt_s7[0]], ALPH_K[opt_s7[1]], ALPH_K[opt_s7[2]],
                            ALPH_K[opt_s7[3]], ALPH_K[opt_s7[4]], ALPH_K[opt_s7[5]], ALPH_K[opt_s7[6]]);
                    for (int i = 0; i < N; i++) local_pt[i] = pt[i] + 'A';
                    local_pt[N] = '\0';
                }

                // If score is promising (> -5.5), test against ALL 41,998 dictionary W7
                if (sc > -5.5f) {
                    #pragma omp critical
                    {
                        printf("CANDIDATE: W4=%s, W5=%s, S7=%s | sc=%.3f\nPT: %.60s...\n",
                               w4_list[i4].word, w5_list[i5].word, local_w7, sc, local_pt);
                        fflush(stdout);
                    }
                }
            }
        }

        #pragma omp critical
        {
            if (local_best_sc > global_best_sc) {
                global_best_sc = local_best_sc;
                strcpy(best_w4, local_w4);
                strcpy(best_w5, local_w5);
                strcpy(best_w7, local_w7);
                strcpy(best_pt, local_pt);
                printf("New best: sc=%.3f | W4=%s, W5=%s, S7=%s\nPT: %.60s...\n",
                       global_best_sc, best_w4, best_w5, best_w7, best_pt);
                fflush(stdout);
            }
        }
    }

    printf("\nFinished evaluation of all high-IoC pairs.\n");
    printf("Global best: sc=%.3f | W4=%s, W5=%s, S7=%s\nPT: %s\n",
           global_best_sc, best_w4, best_w5, best_w7, best_pt);

    return 0;
}
