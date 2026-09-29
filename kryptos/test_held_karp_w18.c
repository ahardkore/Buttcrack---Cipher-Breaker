#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>
#include <time.h>

#define N 144
#define W1 18
#define H1 8
#define W2 8
#define H2 18

static float bigram[26][26];

void load_bigrams() {
    FILE *f = fopen("english_bigrams.bin", "rb");
    if (!f) { printf("Cannot open english_bigrams.bin\n"); exit(1); }
    if (fread(bigram, sizeof(float), 26 * 26, f) != 26 * 26) {
        printf("Failed to read bigrams\n"); exit(1);
    }
    fclose(f);
}

const char *Z_STR = "EVIJSAOMWYTEESREOXDVFTIDNMZTOXAEELTGEWSUDEMOTNBSRHEITTFDLERTTOMASEJNAEWAARSENXHEPEEDTEYOLNAEEEHSESEVITEEECFRSDEELEOPPDSEIDINYSEDSAATOEOREWOEKSEN";

static int z_arr[N];

void init_z() {
    for (int i = 0; i < N; i++) z_arr[i] = Z_STR[i] - 'A';
}

static inline void invert_col(const int *src, int w, int h, const int *perm, int *dst) {
    int idx = 0;
    for (int c_idx = 0; c_idx < w; c_idx++) {
        int col = perm[c_idx];
        for (int r = 0; r < h; r++) dst[r * w + col] = src[idx++];
    }
}

// Held-Karp solver for 18 columns
// State: (mask, last_col). mask has 18 bits.
// dp[mask][last] = best sum of log bigrams
static float dp[1 << W1][W1];
static unsigned char parent[1 << W1][W1];

float solve_held_karp_w18(const int *mid, int *best_order) {
    // Extract the 18 columns of length 8
    int cols[W1][H1];
    for (int c = 0; c < W1; c++) {
        for (int r = 0; r < H1; r++) {
            cols[c][r] = mid[r * W1 + c];
        }
    }

    // Precompute transition cost between column c1 and c2
    float trans[W1][W1];
    for (int c1 = 0; c1 < W1; c1++) {
        for (int c2 = 0; c2 < W1; c2++) {
            if (c1 == c2) { trans[c1][c2] = -9999.0f; continue; }
            float s = 0.0f;
            for (int r = 0; r < H1; r++) {
                s += bigram[cols[c1][r]][cols[c2][r]];
            }
            trans[c1][c2] = s;
        }
    }

    // Initialize DP table
    int total_states = 1 << W1;
    for (int m = 0; m < total_states; m++) {
        for (int c = 0; c < W1; c++) {
            dp[m][c] = -999999.0f;
        }
    }

    // Base cases: single column
    for (int c = 0; c < W1; c++) {
        dp[1 << c][c] = 0.0f;
    }

    // DP transitions
    for (int mask = 1; mask < total_states; mask++) {
        // Count set bits
        int bits = __builtin_popcount(mask);
        if (bits <= 0 || bits >= W1) continue;

        for (int last = 0; last < W1; last++) {
            if (!(mask & (1 << last))) continue;
            float cur_val = dp[mask][last];
            if (cur_val < -900000.0f) continue;

            // Try adding next column
            for (int next = 0; next < W1; next++) {
                if (mask & (1 << next)) continue;
                int next_mask = mask | (1 << next);
                float next_val = cur_val + trans[last][next];
                if (next_val > dp[next_mask][next]) {
                    dp[next_mask][next] = next_val;
                    parent[next_mask][next] = last;
                }
            }
        }
    }

    // Find best ending column for full mask
    int full_mask = (1 << W1) - 1;
    float best_total = -999999.0f;
    int best_end = -1;
    for (int c = 0; c < W1; c++) {
        if (dp[full_mask][c] > best_total) {
            best_total = dp[full_mask][c];
            best_end = c;
        }
    }

    // Reconstruct optimal order
    int cur_mask = full_mask;
    int cur_col = best_end;
    for (int step = W1 - 1; step >= 0; step--) {
        best_order[step] = cur_col;
        int prev_col = parent[cur_mask][cur_col];
        cur_mask ^= (1 << cur_col);
        cur_col = prev_col;
    }

    return best_total;
}

int main() {
    load_bigrams();
    init_z();

    // Test with our top p2 from -5.2647 basin:
    int p2_top[W2] = {4, 0, 6, 5, 3, 2, 7, 1};

    printf("======================================================================\n");
    printf("Running Exact Held-Karp TSP on PK9 18 Columns (Global DP Optimization)\n");
    printf("p2: [4, 0, 6, 5, 3, 2, 7, 1]\n");
    printf("======================================================================\n");

    int mid[N];
    invert_col(z_arr, W2, H2, p2_top, mid);

    int best_order[W1];
    double t0 = omp_get_wtime();
    float best_score = solve_held_karp_w18(mid, best_order);
    double elapsed = omp_get_wtime() - t0;

    printf("Held-Karp Exact Solve completed in %.3f s!\n", elapsed);
    printf("Global Best Bigram Score: %.4f (Avg per bigram: %.4f)\n",
           best_score, best_score / (H1 * (W1 - 1)));
    printf("Provably Optimal 18-Column Order: [");
    for (int i = 0; i < W1; i++) printf("%d%s", best_order[i], i==W1-1?"":", ");
    printf("]\n\n");

    // Output plaintext
    int pt[N];
    invert_col(mid, W1, H1, best_order, pt);
    char pt_str[N + 1];
    for (int i = 0; i < N; i++) pt_str[i] = 'A' + pt[i];
    pt_str[N] = '\0';

    printf("Reconstructed Plaintext:\n%s\n\n", pt_str);
    printf("Plaintext in 8 rows of 18 chars:\n");
    for (int r = 0; r < H1; r++) {
        char buf[19];
        memcpy(buf, pt_str + r * W1, W1);
        buf[W1] = '\0';
        printf("  Row %d: %s\n", r, buf);
    }

    return 0;
}
