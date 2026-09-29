#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <time.h>
#include <omp.h>

#define W 12
#define H 12

static const char *G_rows[12] = {
    "UIRERTAHIHIO",
    "TSMRLOCNSDHH",
    "NWOWEMOSALSO",
    "MDTUNRNAUENO",
    "SOIHFSNLIRSN",
    "ASSETIRNFNSW",
    "OCEHMAHADCAE",
    "FTGTDNIONOCE",
    "WFETREEEEPSD",
    "SALRNEEIFDIH",
    "UITAONLOFSSI",
    "EHAHSSDSOOFU"
};

static int G[12][12];
static float trigrams[26][26][26];

void load_trigrams() {
    float floor_val = -7.5f;
    for (int i=0; i<26; i++)
        for (int j=0; j<26; j++)
            for (int k=0; k<26; k++)
                trigrams[i][j][k] = floor_val;

    // Load from english_quadgrams by marginalizing, or load quadgrams
    FILE *f = fopen("buttcrack/src/buttcrack/data/english_quadgrams.txt", "r");
    char line[64];
    double tri_counts[26][26][26] = {0};
    double total = 0;
    while (fgets(line, sizeof(line), f)) {
        char g[5]; double cnt;
        if (sscanf(line, "%4s %lf", g, &cnt) == 2) {
            int a = g[0]-'A', b = g[1]-'A', c = g[2]-'A';
            if (a>=0&&a<26&&b>=0&&b<26&&c>=0&&c<26) {
                tri_counts[a][b][c] += cnt;
                total += cnt;
            }
        }
    }
    fclose(f);

    for (int a=0; a<26; a++)
        for (int b=0; b<26; b++)
            for (int c=0; c<26; c++)
                if (tri_counts[a][b][c] > 0)
                    trigrams[a][b][c] = (float)log10(tri_counts[a][b][c] / total);
}

// Precomputed 3D transition table:
// cost[a][b][c] = sum_{r=0..11} trigrams[G[r][a]][G[r][b]][G[r][c]]
static float cost3[W][W][W];

void init_cost3() {
    for (int a=0; a<W; a++) {
        for (int b=0; b<W; b++) {
            for (int c=0; c<W; c++) {
                if (a == b || b == c || a == c) {
                    cost3[a][b][c] = -1e9f;
                    continue;
                }
                float s = 0.0f;
                for (int r=0; r<H; r++) {
                    s += trigrams[G[r][a]][G[r][b]][G[r][c]];
                }
                cost3[a][b][c] = s;
            }
        }
    }
}

// DP table: dp[mask][b][c] = best score for subset 'mask', ending with columns b then c
// mask has (1<<12) = 4096 states.
// b in 0..11, c in 0..11
static float dp[4096][W][W];
static unsigned char parent[4096][W][W];

int main() {
    load_trigrams();

    for (int r=0; r<12; r++) {
        for (int c=0; c<12; c++) {
            G[r][c] = G_rows[r][c] - 'A';
        }
    }

    init_cost3();
    printf("Trigram transition tensor initialized.\n");

    // Initialize DP with -infinity
    for (int m=0; m<4096; m++)
        for (int b=0; b<W; b++)
            for (int c=0; c<W; c++)
                dp[m][b][c] = -1e9f;

    // Base cases: all pairs (a, b) with mask = (1<<a) | (1<<b)
    // Score is bigram score or 0
    for (int a=0; a<W; a++) {
        for (int b=0; b<W; b++) {
            if (a == b) continue;
            int mask = (1 << a) | (1 << b);
            dp[mask][a][b] = 0.0f; // base score for 2 columns
        }
    }

    printf("Running exact Trigram DP across all 540,672 states...\n");
    double t0 = omp_get_wtime();

    // Iterate by popcount from 2 to 11
    for (int sz = 2; sz < W; sz++) {
        for (int mask = 0; mask < 4096; mask++) {
            if (__builtin_popcount(mask) != sz) continue;

            for (int a = 0; a < W; a++) {
                if (!(mask & (1 << a))) continue;
                for (int b = 0; b < W; b++) {
                    if (b == a || !(mask & (1 << b))) continue;

                    float cur_val = dp[mask][a][b];
                    if (cur_val < -1e8f) continue;

                    // Transition to next column c
                    for (int c = 0; c < W; c++) {
                        if (mask & (1 << c)) continue;

                        int nxt_mask = mask | (1 << c);
                        float nxt_val = cur_val + cost3[a][b][c];

                        if (nxt_val > dp[nxt_mask][b][c]) {
                            dp[nxt_mask][b][c] = nxt_val;
                            parent[nxt_mask][b][c] = (unsigned char)a;
                        }
                    }
                }
            }
        }
    }

    // Find global optimum at mask = 4095
    int full_mask = 4095;
    float global_best_sc = -1e9f;
    int best_b = -1, best_c = -1;

    for (int b = 0; b < W; b++) {
        for (int c = 0; c < W; c++) {
            if (b == c) continue;
            if (dp[full_mask][b][c] > global_best_sc) {
                global_best_sc = dp[full_mask][b][c];
                best_b = b;
                best_c = c;
            }
        }
    }

    double elapsed = omp_get_wtime() - t0;
    printf("Trigram DP finished in %.3f seconds! Global best score: %.2f\n", elapsed, global_best_sc);
    printf("Average trigram score per position: %.3f\n", global_best_sc / (H * 10));

    // Reconstruct path backwards
    int path[W];
    int cur_mask = full_mask;
    int cur_b = best_b;
    int cur_c = best_c;
    path[W - 1] = cur_c;
    path[W - 2] = cur_b;

    for (int step = W - 3; step >= 0; step--) {
        int prev_a = (int)parent[cur_mask][cur_b][cur_c];
        path[step] = prev_a;
        cur_mask &= ~(1 << cur_c);
        cur_c = cur_b;
        cur_b = prev_a;
    }

    printf("\nExact Global Optimal Column Permutation (Trigram DP):\n[");
    for (int i=0; i<W; i++) printf("%d%s", path[i], i<W-1?", ":"]\n");

    printf("\nDecrypted Rows with Global Trigram Optimum:\n");
    for (int r = 0; r < H; r++) {
        char line[13];
        for (int c = 0; c < W; c++) {
            line[c] = G[r][path[c]] + 'A';
        }
        line[12] = 0;
        printf("Row %2d: %s\n", r, line);
    }

    return 0;
}
