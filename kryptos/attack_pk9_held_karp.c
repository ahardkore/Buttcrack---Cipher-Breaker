#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>

#define N 144
#define W 12
#define H 12

static const char *ALPH = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
static const char *CT = "KSYAWFEYYOISZGEUFBLYATAIBYFAQBQYYVDWJKLJXMYIEPIFVHPQNHZGSUHUUDXLEHRHUMALHEGLHXSJMUXGNUIVBXGUJHZRZGUSVHMLSCTSUQXHSUMQQIFUQGKHJGUQGLHDKEWSKAMHIJXD";

static float bigram_table[26][26];
static float quad_table[26][26][26][26];

static const double ENG_FREQ[26] = {
    0.77, 5.99, 1.97, 1.93, 9.06, 7.51, 6.33, 8.17, 1.29, 2.78,
    4.25, 12.70, 2.23, 2.02, 6.09, 6.97, 0.15, 4.03, 2.41, 6.75,
    0.10, 2.76, 0.98, 2.36, 0.15, 0.07
};

static const int S13[7] = {0, 2, 9, 10, 10, 6, 7};
static int ct_idx[N];
static int k_to_std[26];

void load_models() {
    for (int a = 0; a < 26; a++) {
        for (int b = 0; b < 26; b++) {
            bigram_table[a][b] = -7.0f;
            for (int c = 0; c < 26; c++)
                for (int d = 0; d < 26; d++)
                    quad_table[a][b][c][d] = -9.5f;
        }
    }

    FILE *f = fopen("english_quads.tsv", "r");
    if (!f) f = fopen("english_quadgrams.txt", "r");
    if (!f) { printf("Cannot open quadgram file!\n"); exit(1); }
    char q[16]; float sc;
    while (fscanf(f, "%s\t%f", q, &sc) == 2) {
        if (strlen(q) == 4) {
            int a = q[0]-'A', b = q[1]-'A', c = q[2]-'A', d = q[3]-'A';
            if (a>=0 && a<26 && b>=0 && b<26 && c>=0 && c<26 && d>=0 && d<26)
                quad_table[a][b][c][d] = sc;
        }
    }
    fclose(f);

    // Build bigram table by marginalizing quadgrams or simple logs
    // Using empirical bigram frequencies
    double bi_counts[26][26] = {0};
    double bi_tot = 0;
    FILE *fb = fopen("english_quadgrams.txt", "r");
    if (fb) {
        char line[128];
        while (fgets(line, sizeof(line), fb)) {
            char gram[5]; double cnt;
            if (sscanf(line, "%4s %lf", gram, &cnt) == 2) {
                int a = gram[0]-'A', b = gram[1]-'A';
                if (a>=0&&a<26&&b>=0&&b<26) { bi_counts[a][b] += cnt; bi_tot += cnt; }
                a = gram[1]-'A'; b = gram[2]-'A';
                if (a>=0&&a<26&&b>=0&&b<26) { bi_counts[a][b] += cnt; bi_tot += cnt; }
                a = gram[2]-'A'; b = gram[3]-'A';
                if (a>=0&&a<26&&b>=0&&b<26) { bi_counts[a][b] += cnt; bi_tot += cnt; }
            }
        }
        fclose(fb);
        for (int a = 0; a < 26; a++) {
            for (int b = 0; b < 26; b++) {
                if (bi_counts[a][b] > 0)
                    bigram_table[a][b] = (float)log10(bi_counts[a][b] / bi_tot);
            }
        }
    }

    for (int i = 0; i < 26; i++) {
        k_to_std[i] = ALPH[i] - 'A';
    }
    for (int i = 0; i < N; i++) {
        ct_idx[i] = (int)(strchr(ALPH, CT[i]) - ALPH);
    }
}

// Solve optimal column permutation using Held-Karp TSP
float solve_columnar_held_karp(const int cols[W][H], int *best_order) {
    float cost[W][W];
    for (int i = 0; i < W; i++) {
        for (int j = 0; j < W; j++) {
            if (i == j) { cost[i][j] = -1e9f; continue; }
            float s = 0.0f;
            for (int r = 0; r < H; r++) {
                s += bigram_table[cols[i][r]][cols[j][r]];
            }
            cost[i][j] = s;
        }
    }

    // DP table: dp[mask][last_col]
    // mask has 12 bits: 1 << 12 = 4096
    float dp[4096][W];
    int parent[4096][W];

    for (int m = 0; m < 4096; m++)
        for (int c = 0; c < W; c++)
            dp[m][c] = -1e9f;

    // Base cases: 1 column chosen
    for (int c = 0; c < W; c++) {
        dp[1 << c][c] = 0.0f;
    }

    for (int m = 1; m < 4096; m++) {
        for (int u = 0; u < W; u++) {
            if (!(m & (1 << u))) continue;
            float cur_val = dp[m][u];
            if (cur_val <= -1e8f) continue;

            for (int v = 0; v < W; v++) {
                if (m & (1 << v)) continue;
                int next_m = m | (1 << v);
                float next_val = cur_val + cost[u][v];
                if (next_val > dp[next_m][v]) {
                    dp[next_m][v] = next_val;
                    parent[next_m][v] = u;
                }
            }
        }
    }

    int full_mask = (1 << W) - 1;
    float best_total = -1e9f;
    int best_end = -1;
    for (int c = 0; c < W; c++) {
        if (dp[full_mask][c] > best_total) {
            best_total = dp[full_mask][c];
            best_end = c;
        }
    }

    // Reconstruct path
    int curr_m = full_mask;
    int curr_c = best_end;
    for (int step = W - 1; step >= 0; step--) {
        best_order[step] = curr_c;
        int p = parent[curr_m][curr_c];
        curr_m &= ~(1 << curr_c);
        curr_c = p;
    }

    return best_total / (11.0f * H);
}

typedef struct {
    double mono_sc;
    int q4[4];
    int q7[7];
} CandidateKey;

int compare_mono(const void *a, const void *b) {
    double diff = ((CandidateKey*)b)->mono_sc - ((CandidateKey*)a)->mono_sc;
    return (diff > 0) - (diff < 0);
}

int main() {
    setvbuf(stdout, NULL, _IONBF, 0);
    load_models();
    printf("Models loaded. Step 1: Pre-filtering top 2000 (Q4, Q7) candidates by monogram score...\n");

    // Precompute Q7 list
    int Q7_list[128][7];
    for (int mask = 0; mask < 128; mask++) {
        for (int j = 0; j < 7; j++) {
            Q7_list[mask][j] = S13[j] + ((mask >> j) & 1) * 13;
        }
    }

    CandidateKey *pool = malloc(2250000 * sizeof(CandidateKey));
    int pool_size = 0;

    #pragma omp parallel for schedule(dynamic)
    for (int mask = 0; mask < 128; mask++) {
        int q7[7];
        memcpy(q7, Q7_list[mask], sizeof(q7));

        for (int a1 = 0; a1 < 26; a1++) {
            for (int a2 = 0; a2 < 26; a2++) {
                for (int a3 = 0; a3 < 26; a3++) {
                    int q4[4] = {0, a1, a2, a3};
                    double sc = 0.0;
                    for (int i = 0; i < N; i++) {
                        int k = (q4[i % 4] + q7[i % 7]) % 26;
                        int p = (ct_idx[i] - k + 26) % 26;
                        sc += ENG_FREQ[p];
                    }

                    if (sc > 720.0) {
                        #pragma omp critical
                        {
                            pool[pool_size].mono_sc = sc;
                            memcpy(pool[pool_size].q4, q4, sizeof(q4));
                            memcpy(pool[pool_size].q7, q7, sizeof(q7));
                            pool_size++;
                        }
                    }
                }
            }
        }
    }

    printf("Generated pool of %d high-scoring monogram keys (score > 760).\n", pool_size);
    qsort(pool, pool_size, sizeof(CandidateKey), compare_mono);

    int test_count = pool_size > 2000 ? 2000 : pool_size;
    printf("Step 2: Running exact Held-Karp columnar solver on top %d candidates...\n", test_count);

    float global_best_quad = -999.0f;
    char global_best_pt[N+1];
    int global_best_order[W];
    CandidateKey global_best_key;

    #pragma omp parallel for schedule(dynamic)
    for (int idx = 0; idx < test_count; idx++) {
        int *q4 = pool[idx].q4;
        int *q7 = pool[idx].q7;

        // Decrypt stream T(P)
        int stream[N];
        for (int i = 0; i < N; i++) {
            int k = (q4[i % 4] + q7[i % 7]) % 26;
            int p = (ct_idx[i] - k + 26) % 26;
            stream[i] = k_to_std[p];
        }

        // Form 12 columns of height 12
        int cols[W][H];
        for (int c = 0; c < W; c++) {
            for (int r = 0; r < H; r++) {
                cols[c][r] = stream[c * H + r];
            }
        }

        int order[W];
        float tsp_sc = solve_columnar_held_karp(cols, order);

        // Reconstruct plaintext row by row
        char pt[N+1];
        int pos = 0;
        for (int r = 0; r < H; r++) {
            for (int c = 0; c < W; c++) {
                pt[pos++] = 'A' + cols[order[c]][r];
            }
        }
        pt[N] = 0;

        // Score with full quadgrams
        float qsc = 0.0f;
        for (int i = 0; i < N - 3; i++) {
            qsc += quad_table[pt[i]-'A'][pt[i+1]-'A'][pt[i+2]-'A'][pt[i+3]-'A'];
        }
        qsc /= (N - 3);

        if (qsc > -8.5f) {
            #pragma omp critical
            {
                if (qsc > global_best_quad) {
                    global_best_quad = qsc;
                    memcpy(&global_best_key, &pool[idx], sizeof(CandidateKey));
                    memcpy(global_best_order, order, sizeof(order));
                    strcpy(global_best_pt, pt);
                    printf("\nHIT! QuadScore=%.3f (TSP=%.3f, Mono=%.1f)\n", qsc, tsp_sc, pool[idx].mono_sc);
                    printf("  Order: ");
                    for (int c = 0; c < W; c++) printf("%d ", order[c]);
                    printf("\n  Q4=[%d,%d,%d,%d] Q7=[%d,%d,%d,%d,%d,%d,%d]\n",
                           q4[0], q4[1], q4[2], q4[3], q7[0], q7[1], q7[2], q7[3], q7[4], q7[5], q7[6]);
                    printf("  PT: %s\n", pt);
                }
            }
        }
    }

    printf("\n--- SEARCH COMPLETE ---\n");
    printf("Global Best QuadScore: %.3f\n", global_best_quad);
    if (global_best_quad > -900.0f) {
        printf("PT: %s\n", global_best_pt);
    }

    free(pool);
    return 0;
}
