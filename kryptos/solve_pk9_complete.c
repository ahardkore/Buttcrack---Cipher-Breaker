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

// Known universal parities
static const int q2_4[4] = {0, 1, 0, 0};
static const int q2_7[7] = {0, 1, 1, 1, 0, 0, 0};

static inline int crt(int q2, int q13) {
    return (13 * q2 + 14 * q13) % 26;
}

static int c_idx[N];
static int alpha_to_std[26];
static int char_to_k[256];
static float bigram_table[26][26];

void init_tables() {
    for (int i = 0; i < 256; i++) char_to_k[i] = -1;
    for (int i = 0; i < 26; i++) {
        alpha_to_std[i] = KRYPTOS[i] - 'A';
        char_to_k[(unsigned char)KRYPTOS[i]] = i;
    }
    for (int i = 0; i < N; i++) {
        c_idx[i] = char_to_k[(unsigned char)PK9_CT[i]];
    }

    for (int i = 0; i < 26; i++)
        for (int j = 0; j < 26; j++)
            bigram_table[i][j] = -7.0f;

    FILE *f = fopen("english_quads.tsv", "r");
    if (f) {
        char q[8]; float logp;
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
            for (int i = 0; i < 26; i++)
                for (int j = 0; j < 26; j++)
                    if (bg_counts[i][j] > 0)
                        bigram_table[i][j] = log10(bg_counts[i][j] / total_bg);
        }
    }
}

static inline float get_lp(char a, char b) {
    return bigram_table[a - 'A'][b - 'A'];
}

// Held-Karp solver for width 12
float solve_held_karp_12(const char *text, int *best_order, char *out_plain) {
    int w = 12;
    int h = 12; // 144 / 12
    char B[12][12];
    for (int k = 0; k < 12; k++) {
        for (int r = 0; r < 12; r++) {
            B[k][r] = text[k * 12 + r];
        }
    }

    float T[12][12], Wm[12][12];
    for (int i = 0; i < 12; i++) {
        for (int j = 0; j < 12; j++) {
            if (i == j) {
                T[i][j] = -1e9f;
                Wm[i][j] = -1e9f;
            } else {
                float sT = 0.0f;
                for (int r = 0; r < 12; r++) sT += get_lp(B[i][r], B[j][r]);
                T[i][j] = sT;

                float sW = 0.0f;
                for (int r = 0; r < 11; r++) sW += get_lp(B[i][r], B[j][r+1]);
                Wm[i][j] = sW;
            }
        }
    }

    int full = (1 << 12) - 1;
    float global_best_score = -1e9f;
    int global_best_seq[12];

    static float dp[1 << 12][12];
    static int par[1 << 12][12];

    for (int start = 0; start < 12; start++) {
        for (int S = 0; S <= full; S++) {
            for (int last = 0; last < 12; last++) {
                dp[S][last] = -1e9f;
                par[S][last] = -1;
            }
        }
        dp[1 << start][start] = 0.0f;

        for (int S = 1; S <= full; S++) {
            if (!((S >> start) & 1)) continue;
            for (int last = 0; last < 12; last++) {
                float cur = dp[S][last];
                if (cur <= -1e8f) continue;
                for (int nxt = 0; nxt < 12; nxt++) {
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

        for (int end = 0; end < 12; end++) {
            if (dp[full][end] <= -1e8f) continue;
            float total = dp[full][end] + Wm[end][start];
            if (total > global_best_score) {
                global_best_score = total;
                int seq[12];
                int S = full, cur = end, pos = 0;
                while (cur != -1) {
                    seq[pos++] = cur;
                    int prev = par[S][cur];
                    S ^= (1 << cur);
                    cur = prev;
                }
                for (int i = 0; i < 12; i++) global_best_seq[i] = seq[11 - i];
            }
        }
    }

    if (best_order) {
        for (int c = 0; c < 12; c++) best_order[global_best_seq[c]] = c;
    }
    if (out_plain) {
        int idx = 0;
        for (int r = 0; r < 12; r++) {
            for (int c = 0; c < 12; c++) {
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

typedef struct {
    float dot;
    int q4[4];
    int q7[7];
} CandKey;

int main() {
    init_tables();

    printf("Starting Ultra-Fast Exhaustive Search on PK9 (Q4 + Q7 + Held-Karp)...\n");

    double t0 = omp_get_wtime();

    // Stage 1: Sweep all 13^3 = 2,197 configurations of Q4 in Z13
    // For each, find optimal Q7
    CandKey top_keys[20000];
    int n_cand = 0;

    for (int q13_1 = 0; q13_1 < 13; q13_1++) {
        for (int q13_2 = 0; q13_2 < 13; q13_2++) {
            for (int q13_3 = 0; q13_3 < 13; q13_3++) {
                int q4[4] = {
                    crt(q2_4[0], 0),
                    crt(q2_4[1], q13_1),
                    crt(q2_4[2], q13_2),
                    crt(q2_4[3], q13_3)
                };

                int q7[7];
                float total_dot = 0.0f;

                for (int j = 0; j < 7; j++) {
                    float best_d = -1.0f;
                    int best_v = 0;
                    for (int v13 = 0; v13 < 13; v13++) {
                        int v = crt(q2_7[j], v13);
                        float d = slice_dot(j, v, q4);
                        if (d > best_d) {
                            best_d = d;
                            best_v = v;
                        }
                    }
                    q7[j] = best_v;
                    total_dot += best_d;
                }

                if (total_dot >= 7.2f && n_cand < 20000) {
                    top_keys[n_cand].dot = total_dot;
                    for (int i = 0; i < 4; i++) top_keys[n_cand].q4[i] = q4[i];
                    for (int i = 0; i < 7; i++) top_keys[n_cand].q7[i] = q7[i];
                    n_cand++;
                }
            }
        }
    }

    printf("Stage 1 Complete: Found %d candidates with Monogram Dot >= 7.2 in %.3f s\n",
           n_cand, omp_get_wtime() - t0);

    // Stage 2: Parallel Held-Karp across all candidates
    float global_best_hk = -9999.0f;
    char best_plain[N + 1] = "";
    int best_order[12];
    CandKey best_cand;

    #pragma omp parallel
    {
        float local_best_hk = -9999.0f;
        char local_plain[N + 1] = "";
        int local_order[12];
        CandKey local_cand;

        #pragma omp for schedule(dynamic, 16)
        for (int c = 0; c < n_cand; c++) {
            const CandKey *k = &top_keys[c];

            char X[N + 1];
            for (int i = 0; i < N; i++) {
                int shift = (k->q4[i % 4] + k->q7[i % 7]) % 26;
                int p = (c_idx[i] - shift + 26) % 26;
                X[i] = 'A' + alpha_to_std[p];
            }
            X[N] = '\0';

            int order[12];
            char plain[N + 1];
            float sc = solve_held_karp_12(X, order, plain);

            if (sc > -380.0f) {
                #pragma omp critical
                {
                    printf("\n>>> CANDIDATE HIT! HK_Score = %.2f (avg = %.3f) | Dot = %.4f\n",
                           sc, sc / N, k->dot);
                    printf("  Q4: [%d, %d, %d, %d]\n", k->q4[0], k->q4[1], k->q4[2], k->q4[3]);
                    printf("  Q7: [%d, %d, %d, %d, %d, %d, %d]\n",
                           k->q7[0], k->q7[1], k->q7[2], k->q7[3], k->q7[4], k->q7[5], k->q7[6]);
                    printf("  Order: [");
                    for (int i = 0; i < 12; i++) printf("%d%s", order[i], i==11?"]\n":", ");
                    printf("  Plain: %s\n\n", plain);
                    fflush(stdout);
                }
            }

            if (sc > local_best_hk) {
                local_best_hk = sc;
                strcpy(local_plain, plain);
                for (int i = 0; i < 12; i++) local_order[i] = order[i];
                local_cand = *k;
            }
        }

        #pragma omp critical
        {
            if (local_best_hk > global_best_hk) {
                global_best_hk = local_best_hk;
                strcpy(best_plain, local_plain);
                for (int i = 0; i < 12; i++) best_order[i] = local_order[i];
                best_cand = local_cand;
            }
        }
    }

    double elapsed = omp_get_wtime() - t0;
    printf("Stage 2 Complete in %.2f s\n", elapsed);
    printf("Global Best HK Score = %.2f (avg = %.3f) | Dot = %.4f\n",
           global_best_hk, global_best_hk / N, best_cand.dot);
    printf("Q4: [%d, %d, %d, %d]\n", best_cand.q4[0], best_cand.q4[1], best_cand.q4[2], best_cand.q4[3]);
    printf("Q7: [%d, %d, %d, %d, %d, %d, %d]\n",
           best_cand.q7[0], best_cand.q7[1], best_cand.q7[2], best_cand.q7[3],
           best_cand.q7[4], best_cand.q7[5], best_cand.q7[6]);
    printf("Order: [");
    for (int i = 0; i < 12; i++) printf("%d%s", best_order[i], i==11?"]\n":", ");
    printf("Plaintext:\n%s\n", best_plain);

    return 0;
}
