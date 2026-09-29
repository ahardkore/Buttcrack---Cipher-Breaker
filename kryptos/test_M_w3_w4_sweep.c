#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <omp.h>

static float quad_table[26][26][26][26];
static const char *ALPH_K = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
static int k_to_std[26];
static int std_to_k[26];

static const char *M_STR = "QGKVHPZGUKSYHEGBYFHJGQNHSVHAWFLHXAQBUQGZGSMLSEYYSJMQYYLHDUHUCTSOISUXGVDWKEWUDXUQXZGENUIJKLSKALEHHSUUFBVBXJXMMHIRHUMQQLYAGUJYIEJXDMALIFUTAIHZRPIF";
static int M[144];
static const int N = 144;

static const double ENG_FREQ[26] = {
    8.2, 1.5, 2.8, 4.3, 12.7, 2.2, 2.0, 6.1, 7.0, 0.15,
    0.8, 4.0, 2.4, 6.7, 7.5, 1.9, 0.1, 6.0, 6.3, 9.1,
    2.8, 1.0, 2.4, 0.15, 2.0, 0.07
};

typedef struct {
    char word[8];
    int shifts[4];
} Word;

static Word *w3_list = NULL;
static int n3 = 0;
static Word *w4_list = NULL;
static int n4 = 0;

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
        M[i] = std_to_k[M_STR[i] - 'A'];
    }

    w3_list = malloc(5000 * sizeof(Word));
    w4_list = malloc(10000 * sizeof(Word));

    f = fopen("words_alpha.txt", "r");
    if (!f) { fprintf(stderr, "Cannot open words_alpha.txt\n"); exit(1); }
    char buf[64];
    while (fscanf(f, "%63s", buf) == 1) {
        int len = strlen(buf);
        if (len == 3) {
            int ok = 1;
            for (int i = 0; i < 3; i++) {
                if (buf[i] >= 'a' && buf[i] <= 'z') buf[i] = buf[i] - 'a' + 'A';
                if (buf[i] < 'A' || buf[i] > 'Z') ok = 0;
            }
            if (!ok) continue;
            strcpy(w3_list[n3].word, buf);
            for (int i = 0; i < 3; i++) w3_list[n3].shifts[i] = std_to_k[buf[i] - 'A'];
            n3++;
        } else if (len == 4) {
            int ok = 1;
            for (int i = 0; i < 4; i++) {
                if (buf[i] >= 'a' && buf[i] <= 'z') buf[i] = buf[i] - 'a' + 'A';
                if (buf[i] < 'A' || buf[i] > 'Z') ok = 0;
            }
            if (!ok) continue;
            strcpy(w4_list[n4].word, buf);
            for (int i = 0; i < 4; i++) w4_list[n4].shifts[i] = std_to_k[buf[i] - 'A'];
            n4++;
        }
    }
    fclose(f);
    printf("Loaded: W3=%d, W4=%d\n", n3, n4);
}

int main(int argc, char **argv) {
    (void)argc; (void)argv;
    init();

    printf("Evaluating all %lld pairs of (W3, W4) with Chi-sq optimal 7-shifts on M...\n",
           (long long)n3 * n4);

    float best_sc = -999.0f;
    char best_hit[64] = "";
    char best_pt[150] = "";
    int best_s7[7];

    #pragma omp parallel
    {
        float local_best = -999.0f;
        char local_hit[64] = "";
        char local_pt[150] = "";
        int local_s7[7];

        #pragma omp for schedule(dynamic, 50)
        for (int i3 = 0; i3 < n3; i3++) {
            const int *s3 = w3_list[i3].shifts;
            for (int i4 = 0; i4 < n4; i4++) {
                const int *s4 = w4_list[i4].shifts;

                // Compute peeled stream M' = (M - s3 - s4) mod 26
                int M_prime[144];
                for (int i = 0; i < N; i++) {
                    int k = s3[i % 3] + s4[i & 3];
                    M_prime[i] = (M[i] - k + 52) % 26;
                }

                // For each of the 7 columns, pick optimal shift by Chi-sq
                int opt_s7[7];
                for (int c = 0; c < 7; c++) {
                    int counts[26] = {0};
                    int col_len = 0;
                    for (int i = c; i < N; i += 7) {
                        col_len++;
                    }
                    double best_chi = 1e9;
                    int best_s = 0;
                    for (int s = 0; s < 26; s++) {
                        int std_counts[26] = {0};
                        for (int i = c; i < N; i += 7) {
                            int p_idx = (M_prime[i] - s + 26) % 26;
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

                // Score first 24 characters
                int pt[144];
                for (int i = 0; i < 24; i++) {
                    int p_idx = (M_prime[i] - opt_s7[i % 7] + 26) % 26;
                    pt[i] = k_to_std[p_idx];
                }
                float sc = 0.0f;
                for (int i = 0; i < 21; i++) sc += quad_table[pt[i]][pt[i+1]][pt[i+2]][pt[i+3]];
                sc /= 21.0f;
                if (sc < -5.4f) continue;

                // Full text
                for (int i = 24; i < N; i++) {
                    int p_idx = (M_prime[i] - opt_s7[i % 7] + 26) % 26;
                    pt[i] = k_to_std[p_idx];
                }
                float full_sc = sc * 21.0f;
                for (int i = 21; i < N - 3; i++) full_sc += quad_table[pt[i]][pt[i+1]][pt[i+2]][pt[i+3]];
                full_sc /= (N - 3);

                if (full_sc > local_best) {
                    local_best = full_sc;
                    sprintf(local_hit, "%s + %s", w3_list[i3].word, w4_list[i4].word);
                    for (int i = 0; i < 7; i++) local_s7[i] = opt_s7[i];
                    for (int i = 0; i < N; i++) local_pt[i] = pt[i] + 'A';
                    local_pt[N] = '\0';
                }
            }
        }

        #pragma omp critical
        {
            if (local_best > best_sc) {
                best_sc = local_best;
                strcpy(best_hit, local_hit);
                strcpy(best_pt, local_pt);
                for (int i = 0; i < 7; i++) best_s7[i] = local_s7[i];
                printf("New best: sc=%.3f | %s | S7=[%d,%d,%d,%d,%d,%d,%d]\nPT: %.55s...\n",
                       best_sc, best_hit, best_s7[0], best_s7[1], best_s7[2], best_s7[3],
                       best_s7[4], best_s7[5], best_s7[6], best_pt);
                fflush(stdout);
            }
        }
    }

    printf("\nFinished (W3, W4) sweep on M.\n");
    printf("Global best: sc=%.3f (%s) S7=[%d,%d,%d,%d,%d,%d,%d]\nPT: %s\n",
           best_sc, best_hit, best_s7[0], best_s7[1], best_s7[2], best_s7[3],
           best_s7[4], best_s7[5], best_s7[6], best_pt);
    return 0;
}
