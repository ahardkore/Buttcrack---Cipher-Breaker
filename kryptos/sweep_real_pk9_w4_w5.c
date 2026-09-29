#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <omp.h>

static const char *ALPH_K = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
static int std_to_k[26];

static const char *CT9_REAL = "KSYAWFEYYOISZGEUFBLYATAIBYFAQBQYYVDWJKLJXMYIEPIFVHPQNHZGSUHUUDXLEHRHUMALHEGLHXSJMUXGNUIVBXGUJHZRZGUSVHMLSCTSUQXHSUMQQIFUQGKHJGUQGLHDKEWSKAMHIJXD";
static int C[144];
static const int N = 144;

typedef struct {
    char word[6];
    int shifts[5];
} Word5;

typedef struct {
    char word[5];
    int shifts[4];
} Word4;

static Word4 *words4 = NULL;
static int n_w4 = 0;
static Word5 *words5 = NULL;
static int n_w5 = 0;

void init() {
    for (int i = 0; i < 26; i++) {
        std_to_k[ALPH_K[i] - 'A'] = i;
    }
    for (int i = 0; i < N; i++) {
        C[i] = std_to_k[CT9_REAL[i] - 'A'];
    }

    words4 = malloc(10000 * sizeof(Word4));
    words5 = malloc(20000 * sizeof(Word5));

    FILE *f = fopen("words_alpha.txt", "r");
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
            strcpy(words4[n_w4].word, buf);
            for (int i = 0; i < 4; i++) words4[n_w4].shifts[i] = std_to_k[buf[i] - 'A'];
            n_w4++;
        } else if (len == 5) {
            int ok = 1;
            for (int i = 0; i < 5; i++) {
                if (buf[i] >= 'a' && buf[i] <= 'z') buf[i] = buf[i] - 'a' + 'A';
                if (buf[i] < 'A' || buf[i] > 'Z') ok = 0;
            }
            if (!ok) continue;
            strcpy(words5[n_w5].word, buf);
            for (int i = 0; i < 5; i++) words5[n_w5].shifts[i] = std_to_k[buf[i] - 'A'];
            n_w5++;
        }
    }
    fclose(f);
    printf("Loaded words: W4=%d, W5=%d (Total pairs = %lld)\n",
           n_w4, n_w5, (long long)n_w4 * n_w5);
}

int main(int argc, char **argv) {
    (void)argc; (void)argv;
    init();

    // Baseline IoC of raw C at period 7
    double base_ioc = 0.0;
    for (int c = 0; c < 7; c++) {
        int counts[26] = {0};
        int L = 0;
        for (int i = c; i < N; i += 7) {
            counts[C[i]]++;
            L++;
        }
        int sum = 0;
        for (int k = 0; k < 26; k++) sum += counts[k] * (counts[k] - 1);
        base_ioc += (double)sum / (L * (L - 1));
    }
    base_ioc /= 7.0;
    printf("Baseline Period-7 IoC of raw C: %.5f\n\n", base_ioc);

    float global_max_ioc = 0.0f;
    char best_w4[8] = "";
    char best_w5[8] = "";
    long long hits = 0;

    #pragma omp parallel
    {
        float local_max = 0.0f;
        char local_w4[8] = "";
        char local_w5[8] = "";
        long long local_hits = 0;

        #pragma omp for schedule(dynamic, 100)
        for (int i4 = 0; i4 < n_w4; i4++) {
            const int *s4 = words4[i4].shifts;

            for (int i5 = 0; i5 < n_w5; i5++) {
                const int *s5 = words5[i5].shifts;

                // Fast computation of period-7 coset IoC
                double total_ioc = 0.0;
                for (int c = 0; c < 7; c++) {
                    int counts[26] = {0};
                    int L = 0;
                    for (int i = c; i < N; i += 7) {
                        int k = s4[i & 3] + s5[i % 5];
                        int p = (C[i] - k + 52) % 26;
                        counts[p]++;
                        L++;
                    }
                    int sum = 0;
                    for (int ch = 0; ch < 26; ch++) sum += counts[ch] * (counts[ch] - 1);
                    total_ioc += (double)sum / (L * (L - 1));
                }
                total_ioc /= 7.0;

                if (total_ioc > local_max) {
                    local_max = total_ioc;
                    strcpy(local_w4, words4[i4].word);
                    strcpy(local_w5, words5[i5].word);
                }

                if (total_ioc >= 0.065) {
                    local_hits++;
                    #pragma omp critical
                    {
                        printf("HIT: IoC=%.5f | W4=%s, W5=%s\n",
                               total_ioc, words4[i4].word, words5[i5].word);
                        fflush(stdout);
                    }
                }
            }
        }

        #pragma omp critical
        {
            hits += local_hits;
            if (local_max > global_max_ioc) {
                global_max_ioc = local_max;
                strcpy(best_w4, local_w4);
                strcpy(best_w5, local_w5);
            }
        }
    }

    printf("\nFinished sweep of 114,408,306 pairs on REAL raw PK9.\n");
    printf("Total hits >= 0.065: %lld\n", hits);
    printf("Global maximum IoC: %.5f with W4='%s', W5='%s'\n",
           global_max_ioc, best_w4, best_w5);

    return 0;
}
