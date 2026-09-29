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

static int ct_idx[N];
static int k_to_std[26];
static const int Q7_MASK0[7] = {0, 2, 9, 10, 10, 6, 7};

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
    if (!f) exit(1);
    char q[16]; float sc;
    while (fscanf(f, "%s %f", q, &sc) == 2) {
        if (strlen(q) == 4) {
            int a = q[0]-'A', b = q[1]-'A', c = q[2]-'A', d = q[3]-'A';
            if (a>=0 && a<26 && b>=0 && b<26 && c>=0 && c<26 && d>=0 && d<26)
                quad_table[a][b][c][d] = sc;
        }
    }
    fclose(f);

    double bi_counts[26][26] = {0};
    double bi_tot = 0;
    FILE *fb = fopen("english_quadgrams.txt", "r");
    if (fb) {
        char line[128];
        while (fgets(line, sizeof(line), fb)) {
            char gram[5]; double cnt;
            if (sscanf(line, "%4s %lf", gram, &cnt) == 2) {
                for (int i = 0; i < 3; i++) {
                    int a = gram[i]-'A', b = gram[i+1]-'A';
                    if (a>=0&&a<26&&b>=0&&b<26) { bi_counts[a][b] += cnt; bi_tot += cnt; }
                }
            }
        }
        fclose(fb);
        for (int a = 0; a < 26; a++)
            for (int b = 0; b < 26; b++)
                if (bi_counts[a][b] > 0)
                    bigram_table[a][b] = (float)log10(bi_counts[a][b] / bi_tot);
    }

    for (int i = 0; i < 26; i++) k_to_std[i] = ALPH[i] - 'A';
    for (int i = 0; i < N; i++) ct_idx[i] = (int)(strchr(ALPH, CT[i]) - ALPH);
}

float solve_held_karp(const int cols[W][H], int *best_order) {
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

    float dp[4096][W];
    int parent[4096][W];

    for (int m = 0; m < 4096; m++)
        for (int c = 0; c < W; c++)
            dp[m][c] = -1e9f;

    for (int c = 0; c < W; c++) dp[1 << c][c] = 0.0f;

    for (int m = 1; m < 4096; m++) {
        for (int u = 0; u < W; u++) {
            if (!(m & (1 << u))) continue;
            float cur = dp[m][u];
            if (cur <= -1e8f) continue;
            for (int v = 0; v < W; v++) {
                if (m & (1 << v)) continue;
                int nm = m | (1 << v);
                float nv = cur + cost[u][v];
                if (nv > dp[nm][v]) {
                    dp[nm][v] = nv;
                    parent[nm][v] = u;
                }
            }
        }
    }

    int full = (1 << W) - 1;
    float best_tot = -1e9f;
    int best_end = -1;
    for (int c = 0; c < W; c++) {
        if (dp[full][c] > best_tot) {
            best_tot = dp[full][c];
            best_end = c;
        }
    }

    int cm = full;
    int cc = best_end;
    for (int step = W - 1; step >= 0; step--) {
        best_order[step] = cc;
        int p = parent[cm][cc];
        cm &= ~(1 << cc);
        cc = p;
    }

    return best_tot / (11.0f * H);
}

int main() {
    setvbuf(stdout, NULL, _IONBF, 0);
    load_models();
    printf("Models loaded. Sweeping all 17,576 Q4 states with Held-Karp on Q7_MASK0...\n");

    float global_best_quad = -999.0f;
    int best_q4[4] = {0};
    int best_order[W] = {0};
    char best_pt[N+1];

    #pragma omp parallel for schedule(dynamic)
    for (int a1 = 0; a1 < 26; a1++) {
        for (int a2 = 0; a2 < 26; a2++) {
            for (int a3 = 0; a3 < 26; a3++) {
                int q4[4] = {0, a1, a2, a3};

                // Decrypt columns
                int cols[W][H];
                for (int c = 0; c < W; c++) {
                    for (int r = 0; r < H; r++) {
                        int i = c * H + r;
                        int shift = (q4[r % 4] + Q7_MASK0[(5 * c + r) % 7]) % 26;
                        int p = (ct_idx[i] - shift + 26) % 26;
                        cols[c][r] = k_to_std[p];
                    }
                }

                // Quick pairwise filter: sum of max outgoing bigrams
                float max_possible_tsp = 0.0f;
                for (int i = 0; i < W; i++) {
                    float best_out = -1e9f;
                    for (int j = 0; j < W; j++) {
                        if (i == j) continue;
                        float s = 0.0f;
                        for (int r = 0; r < H; r++) {
                            s += bigram_table[cols[i][r]][cols[j][r]];
                        }
                        if (s > best_out) best_out = s;
                    }
                    max_possible_tsp += best_out;
                }
                max_possible_tsp /= (11.0f * H);

                // Only run full Held-Karp if upper bound is promising
                if (max_possible_tsp > -3.2f) {
                    int order[W];
                    float tsp_sc = solve_held_karp(cols, order);

                    if (tsp_sc > -3.5f) {
                        char pt[N+1];
                        int idx = 0;
                        for (int r = 0; r < H; r++) {
                            for (int c = 0; c < W; c++) {
                                pt[idx++] = 'A' + cols[order[c]][r];
                            }
                        }
                        pt[N] = 0;

                        float qsc = 0.0f;
                        for (int i = 0; i < N - 3; i++) {
                            qsc += quad_table[pt[i]-'A'][pt[i+1]-'A'][pt[i+2]-'A'][pt[i+3]-'A'];
                        }
                        qsc /= (N - 3);

                        #pragma omp critical
                        {
                            if (qsc > -8.0f) {
                                global_best_quad = qsc;
                                memcpy(best_q4, q4, sizeof(q4));
                                memcpy(best_order, order, sizeof(order));
                                strcpy(best_pt, pt);
                                printf("\nHIT! Quad=%.3f | TSP=%.3f | Q4=[%d,%d,%d,%d]\n",
                                       qsc, tsp_sc, q4[0], q4[1], q4[2], q4[3]);
                                printf("  Order: ");
                                for (int c = 0; c < W; c++) printf("%d ", order[c]);
                                printf("\n  PT: %s\n", pt);
                            }
                        }
                    }
                }
            }
        }
    }

    printf("\n--- SWEEP COMPLETE ---\n");
    printf("Global Best Quad: %.3f\n", global_best_quad);
    if (global_best_quad > -900.0f) {
        printf("Optimal Q4: [%d, %d, %d, %d]\n", best_q4[0], best_q4[1], best_q4[2], best_q4[3]);
        printf("PT: %s\n", best_pt);
    }

    return 0;
}
