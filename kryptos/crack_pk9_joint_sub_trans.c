#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>

#define N 144

const char *KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
const char *PK9_CT = "KSYAWFEYYOISZGEUFBLYATAIBYFAQBQYYVDWJKLJXMYIEPIFVHPQNHZGSUHUUDXLEHRHUMALHEGLHXSJMUXGNUIVBXGUJHZRZGUSVHMLSCTSUQXHSUMQQIFUQGKHJGUQGLHDKEWSKAMHIJXD";

static const float eng_freq[26] = {
    0.08167, 0.01492, 0.02782, 0.04253, 0.12702, 0.02228, 0.02015,
    0.06094, 0.06966, 0.00153, 0.00772, 0.04025, 0.02406, 0.06749,
    0.07507, 0.01929, 0.00095, 0.05987, 0.06327, 0.09056, 0.02758,
    0.00978, 0.02360, 0.00150, 0.01974, 0.00074
};

static int c_idx[N];
static int alpha_to_std[26];
static float bigram_table[26][26];
static float bigram_floor = -7.0f;

void init_tables() {
    for (int i = 0; i < 26; i++) {
        alpha_to_std[i] = KRYPTOS[i] - 'A';
    }
    for (int i = 0; i < N; i++) {
        c_idx[i] = strchr(KRYPTOS, PK9_CT[i]) - KRYPTOS;
    }

    // Initialize bigram table to floor
    for (int i = 0; i < 26; i++) {
        for (int j = 0; j < 26; j++) {
            bigram_table[i][j] = bigram_floor;
        }
    }

    // Load bigrams from english_quads.tsv
    FILE *f = fopen("english_quads.tsv", "r");
    if (f) {
        char q[8];
        float logp;
        double bg_counts[26][26] = {{0}};
        double total_bg = 0.0;
        while (fscanf(f, "%s %f", q, &logp) == 2) {
            double p = pow(10.0, logp);
            for (int k = 0; k < 3; k++) {
                int c1 = q[k] - 'A';
                int c2 = q[k+1] - 'A';
                if (c1 >= 0 && c1 < 26 && c2 >= 0 && c2 < 26) {
                    bg_counts[c1][c2] += p;
                    total_bg += p;
                }
            }
        }
        fclose(f);
        if (total_bg > 0) {
            for (int i = 0; i < 26; i++) {
                for (int j = 0; j < 26; j++) {
                    if (bg_counts[i][j] > 0) {
                        bigram_table[i][j] = log10(bg_counts[i][j] / total_bg);
                    }
                }
            }
        }
        printf("Loaded bigram table from english_quads.tsv\n");
    }
}

static inline float get_lp(char a, char b) {
    return bigram_table[a - 'A'][b - 'A'];
}

// Held-Karp DP solver for complete columnar of width w
float solve_held_karp(const char *text, int w, int *best_order, char *out_plain) {
    int h = N / w;
    char B[16][144];
    for (int k = 0; k < w; k++) {
        for (int r = 0; r < h; r++) {
            B[k][r] = text[k * h + r];
        }
    }

    float T[16][16];
    float Wm[16][16];
    for (int i = 0; i < w; i++) {
        for (int j = 0; j < w; j++) {
            if (i == j) {
                T[i][j] = -1e9f;
                Wm[i][j] = -1e9f;
            } else {
                float sT = 0.0f;
                for (int r = 0; r < h; r++) sT += get_lp(B[i][r], B[j][r]);
                T[i][j] = sT;

                float sW = 0.0f;
                for (int r = 0; r < h - 1; r++) sW += get_lp(B[i][r], B[j][r+1]);
                Wm[i][j] = sW;
            }
        }
    }

    int full = (1 << w) - 1;
    float global_best_score = -1e9f;
    int global_best_seq[16];

    float dp[1 << 12][12];
    int par[1 << 12][12];


    for (int start = 0; start < w; start++) {
        for (int S = 0; S <= full; S++) {
            for (int last = 0; last < w; last++) {
                dp[S][last] = -1e9f;
                par[S][last] = -1;
            }
        }
        dp[1 << start][start] = 0.0f;

        for (int S = 1; S <= full; S++) {
            if (!((S >> start) & 1)) continue;
            for (int last = 0; last < w; last++) {
                float cur = dp[S][last];
                if (cur <= -1e8f) continue;
                for (int nxt = 0; nxt < w; nxt++) {
                    if ((S >> nxt) & 1) continue;
                    int S2 = S | (1 << nxt);
                    float val = cur + T[last][nxt];
                    if (val > dp[S2][nxt]) {
                        dp[S2][nxt] = val;
                        par[S2][nxt] = last;
                    }
                }
            }
        }

        for (int end = 0; end < w; end++) {
            if (dp[full][end] <= -1e8f) continue;
            float total = dp[full][end] + Wm[end][start];
            if (total > global_best_score) {
                global_best_score = total;
                int seq[16];
                int S = full, cur = end, pos = 0;
                while (cur != -1) {
                    seq[pos++] = cur;
                    int prev = par[S][cur];
                    S ^= (1 << cur);
                    cur = prev;
                }
                for (int i = 0; i < w; i++) {
                    global_best_seq[i] = seq[w - 1 - i];
                }
            }
        }
    }

    if (best_order) {
        for (int c = 0; c < w; c++) {
            best_order[global_best_seq[c]] = c;
        }
    }
    if (out_plain) {
        int idx = 0;
        for (int r = 0; r < h; r++) {
            for (int c = 0; c < w; c++) {
                out_plain[idx++] = B[global_best_seq[c]][r];
            }
        }
        out_plain[N] = '\0';
    }

    return global_best_score;
}

// Compute dot contribution for slice j given Q7[j] = v and fixed Q4
float slice_dot(int j, int v, const int *q4) {
    float dot = 0.0f;
    for (int i = j; i < N; i += 7) {
        int k = (q4[i % 4] + v) % 26;
        int p = (c_idx[i] - k + 26) % 26;
        dot += eng_freq[alpha_to_std[p]];
    }
    return dot;
}

int main() {
    init_tables();

    printf("Starting Joint (Q4, Q7) + Held-Karp Transposition Attack on PK9...\n");

    int widths[4] = {6, 8, 9, 12};
    double t0 = omp_get_wtime();

    int hits_found = 0;

    #pragma omp parallel
    {
        #pragma omp for schedule(dynamic, 16)
        for (int q4_1 = 0; q4_1 < 26; q4_1++) {
            for (int q4_2 = 0; q4_2 < 26; q4_2++) {
                for (int q4_3 = 0; q4_3 < 26; q4_3++) {
                    int q4[4] = {0, q4_1, q4_2, q4_3};
                    int q7[7];
                    float total_dot = 0.0f;

                    for (int j = 0; j < 7; j++) {
                        float best_j_dot = -1.0f;
                        int best_v = 0;
                        for (int v = 0; v < 26; v++) {
                            float d = slice_dot(j, v, q4);
                            if (d > best_j_dot) {
                                best_j_dot = d;
                                best_v = v;
                            }
                        }
                        q7[j] = best_v;
                        total_dot += best_j_dot;
                    }

                    // Only test configurations with top monogram dot product
                    if (total_dot >= 8.0f) {
                        char X[N + 1];
                        for (int i = 0; i < N; i++) {
                            int k = (q4[i % 4] + q7[i % 7]) % 26;
                            int p = (c_idx[i] - k + 26) % 26;
                            X[i] = 'A' + alpha_to_std[p];
                        }
                        X[N] = '\0';

                        for (int widx = 0; widx < 4; widx++) {
                            int w = widths[widx];
                            int order[16];
                            char plain[N + 1];
                            float sc = solve_held_karp(X, w, order, plain);

                            if (sc > -420.0f) {
                                #pragma omp critical
                                {
                                    hits_found++;
                                    printf("\n>>> HIT! Dot=%.4f, Width=%d, HK_Score=%.2f (avg=%.3f)\n",
                                           total_dot, w, sc, sc / N);
                                    printf("  Q4: [%d, %d, %d, %d]\n", q4[0], q4[1], q4[2], q4[3]);
                                    printf("  Q7: [%d, %d, %d, %d, %d, %d, %d]\n",
                                           q7[0], q7[1], q7[2], q7[3], q7[4], q7[5], q7[6]);
                                    printf("  Plain: %s\n", plain);
                                    fflush(stdout);
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    double elapsed = omp_get_wtime() - t0;
    printf("\nCompleted in %.2f s. Total hits found: %d\n", elapsed, hits_found);

    return 0;
}
