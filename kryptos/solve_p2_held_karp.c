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

// Thread-local DP table for Held-Karp
typedef struct {
    float dp[1 << W1][W1];
    unsigned char parent[1 << W1][W1];
} HKContext;

float solve_held_karp_ctx(HKContext *ctx, const int *mid, int *best_order) {
    int cols[W1][H1];
    for (int c = 0; c < W1; c++) {
        for (int r = 0; r < H1; r++) {
            cols[c][r] = mid[r * W1 + c];
        }
    }

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

    int total_states = 1 << W1;
    for (int m = 0; m < total_states; m++) {
        for (int c = 0; c < W1; c++) {
            ctx->dp[m][c] = -999999.0f;
        }
    }

    for (int c = 0; c < W1; c++) {
        ctx->dp[1 << c][c] = 0.0f;
    }

    for (int mask = 1; mask < total_states; mask++) {
        int bits = __builtin_popcount(mask);
        if (bits <= 0 || bits >= W1) continue;

        for (int last = 0; last < W1; last++) {
            if (!(mask & (1 << last))) continue;
            float cur_val = ctx->dp[mask][last];
            if (cur_val < -900000.0f) continue;

            for (int next = 0; next < W1; next++) {
                if (mask & (1 << next)) continue;
                int next_mask = mask | (1 << next);
                float next_val = cur_val + trans[last][next];
                if (next_val > ctx->dp[next_mask][next]) {
                    ctx->dp[next_mask][next] = next_val;
                    ctx->parent[next_mask][next] = last;
                }
            }
        }
    }

    int full_mask = (1 << W1) - 1;
    float best_total = -999999.0f;
    int best_end = -1;
    for (int c = 0; c < W1; c++) {
        if (ctx->dp[full_mask][c] > best_total) {
            best_total = ctx->dp[full_mask][c];
            best_end = c;
        }
    }

    if (best_order) {
        int cur_mask = full_mask;
        int cur_col = best_end;
        for (int step = W1 - 1; step >= 0; step--) {
            best_order[step] = cur_col;
            int prev_col = ctx->parent[cur_mask][cur_col];
            cur_mask ^= (1 << cur_col);
            cur_col = prev_col;
        }
    }

    return best_total;
}

int main(int argc, char **argv) {
    load_bigrams();
    init_z();

    int n_restarts = (argc > 1) ? atoi(argv[1]) : 200;

    printf("======================================================================\n");
    printf("Exact Outer-Held-Karp Solver for PK9: Searching S_8 with Exact W18 DP\n");
    printf("Number of S_8 seeds: %d\n", n_restarts);
    printf("======================================================================\n\n");

    float global_best_sc = -999999.0f;
    int g_p2[W2], g_p1[W1];
    char g_pt[N + 1];

    double t0 = omp_get_wtime();

    #pragma omp parallel
    {
        HKContext *ctx = malloc(sizeof(HKContext));
        unsigned int seed = 42 + omp_get_thread_num() * 1999;
        float loc_best_sc = -999999.0f;
        int l_p2[W2], l_p1[W1];
        char l_pt[N + 1];

        #pragma omp for schedule(dynamic, 1)
        for (int rep = 0; rep < n_restarts; rep++) {
            int p2[W2];
            for (int i = 0; i < W2; i++) p2[i] = i;
            for (int i = W2 - 1; i > 0; i--) {
                int j = rand_r(&seed) % (i + 1);
                int tmp = p2[i]; p2[i] = p2[j]; p2[j] = tmp;
            }

            int mid[N];
            invert_col(z_arr, W2, H2, p2, mid);
            float cur_sc = solve_held_karp_ctx(ctx, mid, NULL);

            // Coordinate descent on p2 (2-opt swaps)
            int improved = 1;
            while (improved) {
                improved = 0;
                for (int i = 0; i < W2 - 1; i++) {
                    for (int j = i + 1; j < W2; j++) {
                        int t = p2[i]; p2[i] = p2[j]; p2[j] = t;
                        invert_col(z_arr, W2, H2, p2, mid);
                        float sc = solve_held_karp_ctx(ctx, mid, NULL);
                        if (sc > cur_sc + 1e-4f) {
                            cur_sc = sc;
                            improved = 1;
                        } else {
                            p2[j] = p2[i]; p2[i] = t;
                        }
                    }
                }
            }

            if (cur_sc > loc_best_sc) {
                loc_best_sc = cur_sc;
                memcpy(l_p2, p2, W2 * sizeof(int));
                invert_col(z_arr, W2, H2, p2, mid);
                solve_held_karp_ctx(ctx, mid, l_p1);

                int pt[N];
                invert_col(mid, W1, H1, l_p1, pt);
                for (int t = 0; t < N; t++) l_pt[t] = 'A' + pt[t];
                l_pt[N] = '\0';
            }
        }

        #pragma omp critical
        {
            if (loc_best_sc > global_best_sc) {
                global_best_sc = loc_best_sc;
                memcpy(g_p2, l_p2, W2 * sizeof(int));
                memcpy(g_p1, l_p1, W1 * sizeof(int));
                strcpy(g_pt, l_pt);
                printf("[Thread %d] NEW RECORD Bigram Score = %.4f (Avg: %.4f)\n",
                       omp_get_thread_num(), global_best_sc, global_best_sc / (H1 * (W1 - 1)));
                printf("  p2: [");
                for (int i = 0; i < W2; i++) printf("%d%s", g_p2[i], i==W2-1?"":", ");
                printf("]\n");
                printf("  PT: %.80s...\n\n", g_pt);
            }
        }

        free(ctx);
    }

    double elapsed = omp_get_wtime() - t0;
    printf("======================================================================\n");
    printf("FINAL GLOBAL OPTIMAL RESULT (%d seeds in %.3f s)\n", n_restarts, elapsed);
    printf("======================================================================\n");
    printf("Best Total Bigram Score: %.4f (Avg per bigram: %.4f)\n",
           global_best_sc, global_best_sc / (H1 * (W1 - 1)));
    printf("Order 2 (W2=8):  [");
    for (int i = 0; i < W2; i++) printf("%d%s", g_p2[i], i==W2-1?"":", ");
    printf("]\n");
    printf("Order 1 (W1=18): [");
    for (int i = 0; i < W1; i++) printf("%d%s", g_p1[i], i==W1-1?"":", ");
    printf("]\n\n");
    printf("Plaintext:\n%s\n\n", g_pt);
    printf("Plaintext in 8 rows of 18 chars:\n");
    for (int r = 0; r < H1; r++) {
        char buf[19];
        memcpy(buf, g_pt + r * W1, W1);
        buf[W1] = '\0';
        printf("  Row %d: %s\n", r, buf);
    }

    return 0;
}
