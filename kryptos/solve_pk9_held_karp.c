#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

#define W 12
#define H 12
#define N 144

static const char *Z_text = "KLBQKNSFKCANNSKPPXCSGLQJEMUWQNKIOPOAHTCPMELWYNAJYRJUVTBPSSQBXLNRCMNRIEVZOROUQENLUEAPNSUCEOBOHMLHNSDHGTDUFVLAXDATSSXAWVAOMLMRDSDYTASHSXDAPWRTIRTW";

// Bigram log-probabilities for standard English
static double log_bi[26][26];

void load_bigrams(void) {
    for (int a = 0; a < 26; a++)
        for (int b = 0; b < 26; b++)
            log_bi[a][b] = -10.0;

    FILE *f = fopen("english_quadgrams.txt", "r");
    if (!f) { printf("english_quadgrams.txt missing\n"); exit(1); }
    char q[16]; double cnt; double total = 0;
    double bi_counts[26][26] = {0};
    while (fscanf(f, "%s %lf", q, &cnt) == 2) {
        if (strlen(q) == 4) {
            bi_counts[q[0]-'A'][q[1]-'A'] += cnt;
            bi_counts[q[1]-'A'][q[2]-'A'] += cnt;
            bi_counts[q[2]-'A'][q[3]-'A'] += cnt;
            total += 3 * cnt;
        }
    }
    fclose(f);

    for (int a = 0; a < 26; a++) {
        for (int b = 0; b < 26; b++) {
            if (bi_counts[a][b] > 0) {
                log_bi[a][b] = log10(bi_counts[a][b] / total);
            }
        }
    }
}

int main(void) {
    load_bigrams();

    // Extract 12 columns (each column has length 12)
    // Case 1: Z was written down columns: column j is Z[j*12 .. j*12 + 11]
    // Case 2: Z was written by rows: column j is Z[j, j+12, j+24, ...]
    for (int col_format = 0; col_format < 2; col_format++) {
        char cols[W][H];
        if (col_format == 0) {
            // Z written down columns
            for (int c = 0; c < W; c++) {
                for (int r = 0; r < H; r++) cols[c][r] = Z_text[c * H + r];
            }
            printf("\n=== Case 1: Z represents columns (C[c*12 + r]) ===\n");
        } else {
            // Z written by rows
            for (int c = 0; c < W; c++) {
                for (int r = 0; r < H; r++) cols[c][r] = Z_text[r * W + c];
            }
            printf("\n=== Case 2: Z represents rows (C[r*12 + c]) ===\n");
        }

        // Pairwise adjacency cost: placing column B after column A
        double cost[W][W];
        for (int a = 0; a < W; a++) {
            for (int b = 0; b < W; b++) {
                if (a == b) { cost[a][b] = -1e9; continue; }
                double s = 0;
                for (int r = 0; r < H; r++) {
                    int ca = cols[a][r] - 'A';
                    int cb = cols[b][r] - 'A';
                    s += log_bi[ca][cb];
                }
                cost[a][b] = s;
            }
        }

        // Held-Karp DP: dp[mask][last]
        // mask in 0 .. (1<<12)-1, last in 0 .. 11
        int num_states = 1 << W;
        double (*dp)[W] = malloc(num_states * sizeof(*dp));
        int (*parent)[W] = malloc(num_states * sizeof(*parent));

        for (int m = 0; m < num_states; m++) {
            for (int j = 0; j < W; j++) {
                dp[m][j] = -1e9;
                parent[m][j] = -1;
            }
        }

        // Base cases: paths of length 1 (mask with single bit set)
        for (int j = 0; j < W; j++) {
            dp[1 << j][j] = 0.0;
        }

        // Iterate over mask sizes
        for (int m = 1; m < num_states; m++) {
            for (int last = 0; last < W; last++) {
                if (!(m & (1 << last))) continue;
                if (dp[m][last] < -1e8) continue;

                for (int next = 0; next < W; next++) {
                    if (m & (1 << next)) continue;
                    int next_m = m | (1 << next);
                    double next_sc = dp[m][last] + cost[last][next];
                    if (next_sc > dp[next_m][next]) {
                        dp[next_m][next] = next_sc;
                        parent[next_m][next] = last;
                    }
                }
            }
        }

        // Find best path covering all 12 columns
        int full_mask = (1 << W) - 1;
        double best_total = -1e9;
        int best_last = -1;
        for (int j = 0; j < W; j++) {
            if (dp[full_mask][j] > best_total) {
                best_total = dp[full_mask][j];
                best_last = j;
            }
        }

        // Backtrack optimal permutation
        int order[W];
        int curr_m = full_mask;
        int curr_node = best_last;
        for (int step = W - 1; step >= 0; step--) {
            order[step] = curr_node;
            int p = parent[curr_m][curr_node];
            curr_m &= ~(1 << curr_node);
            curr_node = p;
        }

        printf("Held-Karp Exact Optimal Column Permutation: [");
        for (int j = 0; j < W; j++) printf("%d%s", order[j], j < W - 1 ? ", " : "]\n");
        printf("Total Bigram Score: %.2f (avg per bigram: %.2f)\n",
            best_total, best_total / (11 * 12));

        // Reconstruct decrypted plaintext
        printf("Decrypted Rows:\n");
        for (int r = 0; r < H; r++) {
            printf("  Row %2d: ", r);
            for (int c = 0; c < W; c++) {
                putchar(cols[order[c]][r]);
            }
            putchar('\n');
        }

        free(dp);
        free(parent);
    }

    return 0;
}
