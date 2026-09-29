#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>

#define N 153

static const char *ALPH = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
static const char *CT = "COPVEJJVSVURTVIPYOTPLHGBTMAUCCPESIWIGZBWSJPKTRPUEKQFIFCLHMXTHIMHWOYIGURBOMPARCVXVKBDDVBVHDRHGCVNWWVLBMYWMWHICFIXZWBVZYCQGNOGJGUMLNPUTHQCXNWPQZOIRJZGSWVPY";

static const double eng_freq[26] = {
    0.08167, 0.01492, 0.02782, 0.04253, 0.12702,
    0.02228, 0.02015, 0.06094, 0.06966, 0.00153,
    0.00772, 0.04025, 0.02406, 0.06749, 0.07507,
    0.01929, 0.00095, 0.05987, 0.06327, 0.09056,
    0.02758, 0.00978, 0.02360, 0.00150, 0.01974,
    0.00074
};

static double log_monogram[26];
static float quadgrams[26][26][26][26];

void load_quads() {
    float floor_val = -8.728227f;
    for (int i=0; i<26; i++)
        for (int j=0; j<26; j++)
            for (int k=0; k<26; k++)
                for (int l=0; l<26; l++)
                    quadgrams[i][j][k][l] = floor_val;

    FILE *f = fopen("buttcrack/src/buttcrack/data/english_quadgrams.txt", "r");
    char line[64];
    double total = 5348433.0;
    while (fgets(line, sizeof(line), f)) {
        char g[5]; double cnt;
        if (sscanf(line, "%4s %lf", g, &cnt) == 2) {
            int a = g[0]-'A', b = g[1]-'A', c = g[2]-'A', d = g[3]-'A';
            if (a>=0&&a<26&&b>=0&&b<26&&c>=0&&c<26&&d>=0&&d<26) {
                quadgrams[a][b][c][d] = (float)log10(cnt / total);
            }
        }
    }
    fclose(f);
}

void init_tables() {
    int k2std[26];
    for (int i=0; i<26; i++) k2std[i] = ALPH[i] - 'A';
    for (int i=0; i<26; i++) {
        log_monogram[i] = log(eng_freq[k2std[i]]);
    }
}

static inline float eval_quadgrams(const char *pt) {
    float sc = 0;
    for (int i=0; i<N-3; i++) {
        sc += quadgrams[pt[i]-'A'][pt[i+1]-'A'][pt[i+2]-'A'][pt[i+3]-'A'];
    }
    return sc / (N - 3);
}

int main() {
    load_quads();
    init_tables();

    int k2i[256];
    for (int i=0; i<256; i++) k2i[i] = -1;
    for (int i=0; i<26; i++) k2i[(int)ALPH[i]] = i;

    int ct_k[N];
    for (int i=0; i<N; i++) ct_k[i] = k2i[(int)CT[i]];

    // Base q7 mod 13
    int s13[7] = {0, 2, 9, 10, 10, 6, 7};

    // Candidate q5 vectors from Stride 84 with k5[2] - k5[3] = 7 and k5[4] = 1
    // Let's generate all 26 * 26 = 676 vectors satisfying this invariant!
    // k5[0]=0, k5[1] in 0..25, k5[2] in 0..25, k5[3]=(k5[2]-7+26)%26, k5[4]=1
    printf("Searching across 64 q7 masks x 676 q5 invariant vectors (43,264 combinations)...\n");

    float global_best_sc = -1e9f;
    char global_best_pt[N+1];
    int best_q7[7], best_q5[5], best_k12[12];

    #pragma omp parallel
    {
        float local_best_sc = -1e9f;
        char local_best_pt[N+1];
        int local_q7[7], local_q5[5], local_k12[12];

        #pragma omp for schedule(dynamic, 1)
        for (int mask = 0; mask < 64; mask++) {
            int q7[7];
            q7[0] = s13[0];
            for (int r=1; r<7; r++) {
                q7[r] = (s13[r] + ((mask >> (r - 1)) & 1) * 13) % 26;
            }

            for (int k1 = 0; k1 < 26; k1++) {
                for (int k2 = 0; k2 < 26; k2++) {
                    int q5[5];
                    q5[0] = 0;
                    q5[1] = k1;
                    q5[2] = k2;
                    q5[3] = (k2 - 7 + 26) % 26;
                    q5[4] = 1;

                    // Strip q5 and q7 from ct_k
                    // Z_12[t] = ct_k[t] - q5[t % 5] - q7[t % 7] (mod 26)
                    int z12[N];
                    for (int t=0; t<N; t++) {
                        z12[t] = (ct_k[t] - q5[t % 5] - q7[t % 7] + 52) % 26;
                    }

                    // For each of the 12 cosets of period 12:
                    // Find the shift s in 0..25 maximizing log-likelihood of English monograms
                    int k12[12];
                    for (int col = 0; col < 12; col++) {
                        double best_col_ll = -1e9;
                        int best_s = 0;
                        for (int s = 0; s < 26; s++) {
                            double col_ll = 0;
                            for (int t = col; t < N; t += 12) {
                                int pt_kr = (z12[t] - s + 26) % 26;
                                col_ll += log_monogram[pt_kr];
                            }
                            if (col_ll > best_col_ll) {
                                best_col_ll = col_ll;
                                best_s = s;
                            }
                        }
                        k12[col] = best_s;
                    }

                    // Decrypt full text
                    char pt[N+1];
                    for (int t=0; t<N; t++) {
                        int pt_kr = (z12[t] - k12[t % 12] + 26) % 26;
                        pt[t] = ALPH[pt_kr];
                    }
                    pt[N] = 0;

                    float sc = eval_quadgrams(pt);
                    if (sc > local_best_sc) {
                        local_best_sc = sc;
                        memcpy(local_best_pt, pt, sizeof(pt));
                        memcpy(local_q7, q7, sizeof(q7));
                        memcpy(local_q5, q5, sizeof(q5));
                        memcpy(local_k12, k12, sizeof(k12));
                    }
                }
            }
        }

        #pragma omp critical
        {
            if (local_best_sc > global_best_sc) {
                global_best_sc = local_best_sc;
                memcpy(global_best_pt, local_best_pt, sizeof(global_best_pt));
                memcpy(best_q7, local_q7, sizeof(best_q7));
                memcpy(best_q5, local_q5, sizeof(best_q5));
                memcpy(best_k12, local_k12, sizeof(best_k12));
            }
        }
    }

    printf("\nFinished! Global Best Quadgram Score: %.4f\n", global_best_sc);
    printf("q7:  [%d, %d, %d, %d, %d, %d, %d]\n", best_q7[0], best_q7[1], best_q7[2], best_q7[3], best_q7[4], best_q7[5], best_q7[6]);
    printf("q5:  [%d, %d, %d, %d, %d]\n", best_q5[0], best_q5[1], best_q5[2], best_q5[3], best_q5[4]);
    printf("k12: [");
    for (int i=0; i<12; i++) printf("%d%s", best_k12[i], i<11?", ":"]\n");
    printf("Plaintext:\n%s\n", global_best_pt);

    return 0;
}
