#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>
#include <time.h>

#define N 144

static const char *KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
static const char *PK9_CT = "KSYAWFEYYOISZGEUFBLYATAIBYFAQBQYYVDWJKLJXMYIEPIFVHPQNHZGSUHUUDXLEHRHUMALHEGLHXSJMUXGNUIVBXGUJHZRZGUSVHMLSCTSUQXHSUMQQIFUQGKHJGUQGLHDKEWSKAMHIJXD";

static const double eng_freq[26] = {
    0.08167, 0.01492, 0.02782, 0.04253, 0.12702,
    0.02228, 0.02015, 0.06094, 0.06966, 0.00153,
    0.00772, 0.04025, 0.02406, 0.06749, 0.07507,
    0.01929, 0.00095, 0.05987, 0.06327, 0.09056,
    0.02758, 0.00978, 0.02360, 0.00150, 0.01974,
    0.00074
};

static int c_kr[N];
static int k2std[26];
static double p_k[26];

// Mod-13 base schedule for Clock 7
static const int s13[7] = {0, 2, 9, 10, 10, 6, 7};

typedef struct {
    float ioc;
    float dot;
    int mask;
    int q4[4];
    int q7[7];
} Candidate;

int main() {
    int k2i[256];
    for (int i=0; i<256; i++) k2i[i] = -1;
    for (int i=0; i<26; i++) {
        k2i[(int)KRYPTOS[i]] = i;
        k2std[i] = KRYPTOS[i] - 'A';
    }
    for (int i=0; i<26; i++) p_k[i] = eng_freq[k2std[i]];

    for (int i=0; i<N; i++) c_kr[i] = k2i[(int)PK9_CT[i]];

    printf("Starting exhaustive sweep of all 58,492,928 (q4, q7) keys on PK9...\n");
    double t0 = omp_get_wtime();

    #define MAX_KEEP 100
    Candidate top_cands[MAX_KEEP];
    int n_top = 0;
    float min_top_ioc = -1.0f;

    #pragma omp parallel
    {
        Candidate local_top[MAX_KEEP];
        int local_n = 0;
        float local_min_ioc = -1.0f;

        #pragma omp for schedule(dynamic, 1)
        for (int mask = 0; mask < 128; mask++) {
            int q7[7];
            for (int j = 0; j < 7; j++) {
                int b = (mask >> j) & 1;
                q7[j] = (s13[j] + 13 * b) % 26;
            }

            // Compute Y[t] = (c_kr[t] - q7[t % 7] + 26) % 26
            int Y[N];
            for (int t = 0; t < N; t++) {
                Y[t] = (c_kr[t] - q7[t % 7] + 26) % 26;
            }

            // Precompute counts for each r in {0, 1, 2, 3} and each shift s in {0..25}
            // sub_counts[r][s][c] is the count of letter c when sub-stream r is shifted by s
            int sub_counts[4][26][26] = {{{0}}};
            for (int r = 0; r < 4; r++) {
                for (int t = r; t < N; t += 4) {
                    int y = Y[t];
                    for (int s = 0; s < 26; s++) {
                        int z = (y - s + 26) % 26;
                        sub_counts[r][s][z]++;
                    }
                }
            }

            // Fix gauge: q4[0] = 0 (we can absorb global offset into q7 or test all q4[0])
            // To be 100% complete and not miss anything, let's test ALL q4[0] in 0..25!
            // Wait, fixing q4[0] = 0 reduces 456,976 to 17,576!
            // But does a global shift change the IoC?
            // NO! A global shift on all 144 letters PERMUTES the counts, preserving IoC EXACTLY!
            // IoC = sum c_i (c_i - 1) / (N*(N-1)) is INVARIANT under global shifts!
            // So we can fix q4[0] = 0 without losing ANY IoC peak!
            // Then after finding the best (q4[1], q4[2], q4[3]), we can test all 26 global shifts for English dot product!

            for (int s1 = 0; s1 < 26; s1++) {
                int c01[26];
                for (int c = 0; c < 26; c++) c01[c] = sub_counts[0][0][c] + sub_counts[1][s1][c];

                for (int s2 = 0; s2 < 26; s2++) {
                    int c012[26];
                    for (int c = 0; c < 26; c++) c012[c] = c01[c] + sub_counts[2][s2][c];

                    for (int s3 = 0; s3 < 26; s3++) {
                        int num = 0;
                        for (int c = 0; c < 26; c++) {
                            int cnt = c012[c] + sub_counts[3][s3][c];
                            num += cnt * (cnt - 1);
                        }
                        float ioc = (float)num / (float)(N * (N - 1));

                        if (ioc > local_min_ioc || local_n < MAX_KEEP) {
                            // Find best global shift for dot product
                            float best_dot = 0.0f;
                            int best_g = 0;
                            for (int g = 0; g < 26; g++) {
                                float dot = 0.0f;
                                for (int c = 0; c < 26; c++) {
                                    int cnt = c012[(c + g) % 26] + sub_counts[3][s3][(c + g) % 26];
                                    dot += (float)cnt * (float)p_k[c];
                                }
                                dot /= (float)N;
                                if (dot > best_dot) {
                                    best_dot = dot;
                                    best_g = g;
                                }
                            }

                            if (local_n < MAX_KEEP) {
                                local_top[local_n].ioc = ioc;
                                local_top[local_n].dot = best_dot;
                                local_top[local_n].mask = mask;
                                local_top[local_n].q4[0] = best_g;
                                local_top[local_n].q4[1] = (s1 + best_g) % 26;
                                local_top[local_n].q4[2] = (s2 + best_g) % 26;
                                local_top[local_n].q4[3] = (s3 + best_g) % 26;
                                for (int j = 0; j < 7; j++) local_top[local_n].q7[j] = q7[j];
                                local_n++;
                            } else if (ioc > local_min_ioc) {
                                int min_idx = 0;
                                for (int k = 1; k < MAX_KEEP; k++) {
                                    if (local_top[k].ioc < local_top[min_idx].ioc) min_idx = k;
                                }
                                local_top[min_idx].ioc = ioc;
                                local_top[min_idx].dot = best_dot;
                                local_top[min_idx].mask = mask;
                                local_top[min_idx].q4[0] = best_g;
                                local_top[min_idx].q4[1] = (s1 + best_g) % 26;
                                local_top[min_idx].q4[2] = (s2 + best_g) % 26;
                                local_top[min_idx].q4[3] = (s3 + best_g) % 26;
                                for (int j = 0; j < 7; j++) local_top[min_idx].q7[j] = q7[j];

                                local_min_ioc = local_top[0].ioc;
                                for (int k = 1; k < MAX_KEEP; k++) {
                                    if (local_top[k].ioc < local_min_ioc) local_min_ioc = local_top[k].ioc;
                                }
                            }
                        }
                    }
                }
            }
        }

        #pragma omp critical
        {
            for (int i = 0; i < local_n; i++) {
                if (n_top < MAX_KEEP) {
                    top_cands[n_top++] = local_top[i];
                } else if (local_top[i].ioc > min_top_ioc) {
                    int min_idx = 0;
                    for (int k = 1; k < MAX_KEEP; k++) {
                        if (top_cands[k].ioc < top_cands[min_idx].ioc) min_idx = k;
                    }
                    top_cands[min_idx] = local_top[i];
                    min_top_ioc = top_cands[0].ioc;
                    for (int k = 1; k < MAX_KEEP; k++) {
                        if (top_cands[k].ioc < min_top_ioc) min_top_ioc = top_cands[k].ioc;
                    }
                }
            }
        }
    }

    double elapsed = omp_get_wtime() - t0;
    printf("Sweep completed in %.3f seconds!\n", elapsed);
    printf("Total top candidates retained: %d\n\n", n_top);

    // Sort by IoC descending
    for (int i = 0; i < n_top - 1; i++) {
        for (int j = i + 1; j < n_top; j++) {
            if (top_cands[j].ioc > top_cands[i].ioc) {
                Candidate tmp = top_cands[i];
                top_cands[i] = top_cands[j];
                top_cands[j] = tmp;
            }
        }
    }

    printf("=== TOP 20 CLOCK CANDIDATES ON PK9 ===\n");
    for (int i = 0; i < (n_top < 20 ? n_top : 20); i++) {
        Candidate *c = &top_cands[i];
        printf("Rank %2d: IoC = %.5f | EngDot = %.5f | Mask %3d\n", i + 1, c->ioc, c->dot, c->mask);
        printf("  q4 = [%d, %d, %d, %d] ('%c%c%c%c')\n",
               c->q4[0], c->q4[1], c->q4[2], c->q4[3],
               KRYPTOS[c->q4[0]], KRYPTOS[c->q4[1]], KRYPTOS[c->q4[2]], KRYPTOS[c->q4[3]]);
        printf("  q7 = [%d, %d, %d, %d, %d, %d, %d] ('%c%c%c%c%c%c%c')\n",
               c->q7[0], c->q7[1], c->q7[2], c->q7[3], c->q7[4], c->q7[5], c->q7[6],
               KRYPTOS[c->q7[0]], KRYPTOS[c->q7[1]], KRYPTOS[c->q7[2]],
               KRYPTOS[c->q7[3]], KRYPTOS[c->q7[4]], KRYPTOS[c->q7[5]], KRYPTOS[c->q7[6]]);

        // Decrypt Z
        char Z[N + 1];
        for (int t = 0; t < N; t++) {
            int k = (c->q4[t % 4] + c->q7[t % 7]) % 26;
            int z_kr = (c_kr[t] - k + 26) % 26;
            Z[t] = 'A' + k2std[z_kr];
        }
        Z[N] = '\0';
        printf("  Z: %.70s...\n\n", Z);
    }

    return 0;
}
