#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <time.h>
#include <omp.h>

#define N 504

static const char *ALPH = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
static int char_to_kr[256];
static int ct_kr[N];
static double log_eng[26];
static float quadgrams[26][26][26][26];

// English monogram frequencies
static const double eng_freq[26] = {
    0.08167, 0.01492, 0.02782, 0.04253, 0.12702,
    0.02228, 0.02015, 0.06094, 0.06966, 0.00153,
    0.00772, 0.04025, 0.02406, 0.06749, 0.07507,
    0.01929, 0.00095, 0.05987, 0.06327, 0.09056,
    0.02758, 0.00978, 0.02360, 0.00150, 0.01974,
    0.00074
};

void init(void) {
    for (int i = 0; i < 26; i++) {
        char_to_kr[(unsigned char)ALPH[i]] = i;
        log_eng[i] = log(eng_freq[i]);
    }

    FILE *f = fopen("pk_all_ciphertexts.json", "r");
    char buf[4096];
    fread(buf, 1, sizeof(buf) - 1, f);
    fclose(f);

    char *p = strstr(buf, "\"PK10\": \"");
    p += 9;
    char *end = strchr(p, '"');
    *end = '\0';

    for (int i = 0; i < N; i++) ct_kr[i] = char_to_kr[(unsigned char)p[i]];

    // Load quadgrams
    for (int a = 0; a < 26; a++)
        for (int b = 0; b < 26; b++)
            for (int c = 0; c < 26; c++)
                for (int d = 0; d < 26; d++)
                    quadgrams[a][b][c][d] = -12.0f;

    FILE *fq = fopen("english_quadgrams.txt", "r");
    if (!fq) return;
    char line[64];
    long long total = 0;
    while (fgets(line, sizeof(line), fq)) {
        char qg[5]; long long cnt;
        if (sscanf(line, "%4s %lld", qg, &cnt) == 2) total += cnt;
    }
    fseek(fq, 0, SEEK_SET);
    while (fgets(line, sizeof(line), fq)) {
        char qg[5]; long long cnt;
        if (sscanf(line, "%4s %lld", qg, &cnt) == 2) {
            int a = qg[0] - 'A', b = qg[1] - 'A', c = qg[2] - 'A', d = qg[3] - 'A';
            if (a >= 0 && a < 26 && b >= 0 && b < 26 && c >= 0 && c < 26 && d >= 0 && d < 26) {
                quadgrams[a][b][c][d] = log10f((float)cnt / total);
            }
        }
    }
    fclose(fq);
}

// Score a candidate (q8, q9) under monogram log-likelihood
static inline double score_monogram(const int *c72, const int *q8, const int *q9) {
    double ll = 0;
    for (int t = 0; t < N; t++) {
        int k = (q8[t % 8] + q9[t % 9]) % 26;
        int p = (c72[t] - k + 26) % 26;
        int ch = ALPH[p] - 'A';
        ll += log_eng[ch];
    }
    return ll;
}

int main(int argc, char **argv) {
    init();

    int q7[7] = {0, 2, 9, 23, 23, 6, 20};

    // Precompute C72 for all 26 gauge offsets c of q7
    // And for both Vigenere (C - K) and Beaufort (K - C)
    int num_restarts = (argc > 1) ? atoi(argv[1]) : 1000;
    printf("Starting PK10 Coordinate Descent: %d restarts across 26 gauges and 2 modes\n", num_restarts);

    double global_best_ll = -1e9;
    int global_best_q8[8], global_best_q9[9];
    int global_best_c = 0;
    int global_best_mode = 0;
    char global_best_pt[N + 1];

    double t0 = omp_get_wtime();

    #pragma omp parallel
    {
        unsigned int seed = (unsigned int)(time(NULL) ^ (omp_get_thread_num() * 54321));

        #pragma omp for schedule(dynamic, 1)
        for (int run = 0; run < num_restarts; run++) {
            int c_gauge = run % 26;
            int is_beau = (run / 26) % 2;

            int c72[N];
            for (int t = 0; t < N; t++) {
                int k7 = (q7[t % 7] + c_gauge) % 26;
                if (is_beau) {
                    c72[t] = (k7 - ct_kr[t] + 26) % 26;
                } else {
                    c72[t] = (ct_kr[t] - k7 + 26) % 26;
                }
            }

            // Initialize random (q8, q9)
            int q8[8], q9[9];
            q8[0] = 0;
            for (int i = 1; i < 8; i++) q8[i] = rand_r(&seed) % 26;
            for (int i = 0; i < 9; i++) q9[i] = rand_r(&seed) % 26;

            double cur_ll = score_monogram(c72, q8, q9);
            int improved = 1;
            int iter = 0;

            while (improved && iter < 50) {
                improved = 0;
                iter++;

                // Optimize q8[1..7]
                for (int r = 1; r < 8; r++) {
                    int best_val = q8[r];
                    double best_l = cur_ll;

                    for (int v = 0; v < 26; v++) {
                        if (v == q8[r]) continue;
                        q8[r] = v;
                        double sc = score_monogram(c72, q8, q9);
                        if (sc > best_l) {
                            best_l = sc;
                            best_val = v;
                        }
                    }
                    if (best_val != q8[r] || best_l > cur_ll) {
                        q8[r] = best_val;
                        cur_ll = best_l;
                        improved = 1;
                    }
                }

                // Optimize q9[0..8]
                for (int r = 0; r < 9; r++) {
                    int best_val = q9[r];
                    double best_l = cur_ll;

                    for (int v = 0; v < 26; v++) {
                        if (v == q9[r]) continue;
                        q9[r] = v;
                        double sc = score_monogram(c72, q8, q9);
                        if (sc > best_l) {
                            best_l = sc;
                            best_val = v;
                        }
                    }
                    if (best_val != q9[r] || best_l > cur_ll) {
                        q9[r] = best_val;
                        cur_ll = best_l;
                        improved = 1;
                    }
                }
            }

            #pragma omp critical
            {
                if (cur_ll > global_best_ll) {
                    global_best_ll = cur_ll;
                    global_best_c = c_gauge;
                    global_best_mode = is_beau;
                    memcpy(global_best_q8, q8, sizeof(q8));
                    memcpy(global_best_q9, q9, sizeof(q9));

                    for (int t = 0; t < N; t++) {
                        int k = (q8[t % 8] + q9[t % 9]) % 26;
                        int p = (c72[t] - k + 26) % 26;
                        global_best_pt[t] = ALPH[p];
                    }
                    global_best_pt[N] = '\0';

                    // Compute quadgram score
                    float qsc = 0;
                    for (int t = 0; t < N - 3; t++) {
                        qsc += quadgrams[global_best_pt[t]-'A'][global_best_pt[t+1]-'A'][global_best_pt[t+2]-'A'][global_best_pt[t+3]-'A'];
                    }
                    qsc /= (N - 3);

                    printf("[Run %4d] New Global Best LL: %7.2f (avg %5.2f) | Quad: %5.2f | Mode: %s, c=%2d\n",
                        run, global_best_ll, global_best_ll / N, qsc,
                        is_beau ? "Beaufort" : "Vigenere", c_gauge);
                    printf("  PT: %.80s...\n", global_best_pt);
                }
            }
        }
    }

    double t1 = omp_get_wtime();
    printf("\nCompleted in %.2f seconds!\n", t1 - t0);
    printf("Global Best LL: %.2f (avg %.2f per letter)\n", global_best_ll, global_best_ll / N);
    printf("Best q8: [");
    for (int i = 0; i < 8; i++) printf("%d%s", global_best_q8[i], i < 7 ? ", " : "]\n");
    printf("Best q9: [");
    for (int i = 0; i < 9; i++) printf("%d%s", global_best_q9[i], i < 8 ? ", " : "]\n");
    printf("Decrypted PK10 Plaintext:\n%s\n", global_best_pt);

    return 0;
}
