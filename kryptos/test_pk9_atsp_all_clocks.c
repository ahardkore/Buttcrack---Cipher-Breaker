#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>

#define N 144

static const char *ALPH = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
static const char *PK9_REAL = "KSYAWFEYYOISZGEUFBLYATAIBYFAQBQYYVDWJKLJXMYIEPIFVHPQNHZGSUHUUDXLEHRHUMALHEGLHXSJMUXGNUIVBXGUJHZRZGUSVHMLSCTSUQXHSUMQQIFUQGKHJGUQGLHDKEWSKAMHIJXD";

static int ct_kr[N];
static int ct_std[N];
static int kr_to_std[26];
static int std_to_kr[26];

static float bigram_table[26][26];
static float quad_table[26][26][26][26];

void load_models() {
    for (int a = 0; a < 26; a++)
        for (int b = 0; b < 26; b++)
            bigram_table[a][b] = -7.0f;

    for (int a = 0; a < 26; a++)
        for (int b = 0; b < 26; b++)
            for (int c = 0; c < 26; c++)
                for (int d = 0; d < 26; d++)
                    quad_table[a][b][c][d] = -9.5f;

    FILE *f = fopen("english_quadgrams.txt", "r");
    if (!f) exit(1);
    char q[16]; double cnt; double total = 0;
    double bi_counts[26][26] = {0};
    double bi_tot = 0;
    while (fscanf(f, "%s %lf", q, &cnt) == 2) if (strlen(q) == 4) total += cnt;
    rewind(f);
    while (fscanf(f, "%s %lf", q, &cnt) == 2) {
        if (strlen(q) == 4) {
            int a = q[0]-'A', b = q[1]-'A', c = q[2]-'A', d = q[3]-'A';
            if (a>=0&&a<26&&b>=0&&b<26&&c>=0&&c<26&&d>=0&&d<26) {
                quad_table[a][b][c][d] = (float)log10((cnt + 0.01) / total);
                bi_counts[a][b] += cnt; bi_counts[b][c] += cnt; bi_counts[c][d] += cnt;
                bi_tot += 3 * cnt;
            }
        }
    }
    fclose(f);

    for (int a = 0; a < 26; a++) {
        for (int b = 0; b < 26; b++) {
            bigram_table[a][b] = (float)log10((bi_counts[a][b] + 0.1) / bi_tot);
        }
        kr_to_std[a] = ALPH[a] - 'A';
        std_to_kr[ALPH[a] - 'A'] = a;
    }
    for (int i = 0; i < N; i++) {
        ct_kr[i] = std_to_kr[PK9_REAL[i] - 'A'];
        ct_std[i] = PK9_REAL[i] - 'A';
    }
}

// Decrypt CT to Z given mode and (q4, q7)
void decrypt_to_z(int mode, const int *q4, const int *q7, int *z) {
    for (int i = 0; i < N; i++) {
        int sh = (q4[i % 4] + q7[i % 7]) % 26;
        if (mode == 0) { // Vigenere Std
            z[i] = (ct_std[i] - sh + 26) % 26;
        } else if (mode == 1) { // Beaufort Std
            z[i] = (sh - ct_std[i] + 26) % 26;
        } else if (mode == 2) { // Vigenere Kryptos
            int kr_p = (ct_kr[i] - sh + 26) % 26;
            z[i] = kr_to_std[kr_p];
        } else { // Beaufort Kryptos
            int kr_p = (sh - ct_kr[i] + 26) % 26;
            z[i] = kr_to_std[kr_p];
        }
    }
}

// Exact Held-Karp ATSP for width W (W <= 16)
float solve_atsp(const int *z, int W, int *best_order, int *pt_out) {
    int H = N / W;
    float cost[W][W];

    // Read variant 1: columns are contiguous blocks in z: col c is z[c*H .. c*H + H - 1]
    for (int u = 0; u < W; u++) {
        for (int v = 0; v < W; v++) {
            if (u == v) { cost[u][v] = -999.0f; continue; }
            float s = 0.0f;
            for (int r = 0; r < H; r++) {
                int c1 = z[u * H + r];
                int c2 = z[v * H + r];
                s += bigram_table[c1][c2];
            }
            cost[u][v] = s;
        }
    }

    int n_masks = 1 << W;
    float *dp = (float *)malloc(n_masks * W * sizeof(float));
    int *parent = (int *)malloc(n_masks * W * sizeof(int));
    for (int i = 0; i < n_masks * W; i++) dp[i] = -1e9f;

    for (int i = 0; i < W; i++) {
        dp[(1 << i) * W + i] = 0.0f;
        parent[(1 << i) * W + i] = -1;
    }

    for (int mask = 1; mask < n_masks; mask++) {
        for (int last = 0; last < W; last++) {
            if (!(mask & (1 << last))) continue;
            float cur_val = dp[mask * W + last];
            if (cur_val < -1e8f) continue;

            for (int nxt = 0; nxt < W; nxt++) {
                if (mask & (1 << nxt)) continue;
                int nxt_mask = mask | (1 << nxt);
                float nxt_val = cur_val + cost[last][nxt];
                if (nxt_val > dp[nxt_mask * W + nxt]) {
                    dp[nxt_mask * W + nxt] = nxt_val;
                    parent[nxt_mask * W + nxt] = last;
                }
            }
        }
    }

    int full_mask = (1 << W) - 1;
    float best_total = -1e9f;
    int best_last = -1;
    for (int i = 0; i < W; i++) {
        if (dp[full_mask * W + i] > best_total) {
            best_total = dp[full_mask * W + i];
            best_last = i;
        }
    }

    // Reconstruct path
    int curr = best_last;
    int cur_mask = full_mask;
    for (int step = W - 1; step >= 0; step--) {
        best_order[step] = curr;
        int p = parent[cur_mask * W + curr];
        cur_mask ^= (1 << curr);
        curr = p;
    }

    free(dp);
    free(parent);

    // Reconstruct plaintext
    for (int r = 0; r < H; r++) {
        for (int c = 0; c < W; c++) {
            int col = best_order[c];
            pt_out[r * W + c] = z[col * H + r];
        }
    }

    // Compute quadgram score
    float quad_sc = 0.0f;
    for (int i = 0; i < N - 3; i++) {
        quad_sc += quad_table[pt_out[i]][pt_out[i+1]][pt_out[i+2]][pt_out[i+3]];
    }
    return quad_sc / (N - 3);
}

typedef struct {
    int mode;
    double ll;
    int q4[4];
    int q7[7];
} ClockCand;

int main() {
    load_models();
    printf("Models loaded.\nReading top_clocks.csv...\n");

    FILE *f = fopen("top_clocks.csv", "r");
    if (!f) { printf("Cannot open top_clocks.csv\n"); return 1; }
    char line[256];
    fgets(line, sizeof(line), f); // skip header

    ClockCand cands[2000];
    int count = 0;
    while (fgets(line, sizeof(line), f) && count < 2000) {
        ClockCand *c = &cands[count];
        char dummy1[32], dummy2[32], dummy3[32], dummy4[32];
        if (sscanf(line, "%d,%lf,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%s,%s,%s,%s",
                   &c->mode, &c->ll,
                   &c->q4[0], &c->q4[1], &c->q4[2], &c->q4[3],
                   &c->q7[0], &c->q7[1], &c->q7[2], &c->q7[3], &c->q7[4], &c->q7[5], &c->q7[6],
                   dummy1, dummy2, dummy3, dummy4) >= 13) {
            count++;
        }
    }
    fclose(f);
    printf("Loaded %d clock candidates from top_clocks.csv.\n", count);

    int test_widths[4] = {8, 9, 12, 16};
    for (int widx = 0; widx < 4; widx++) {
        int W = test_widths[widx];
        printf("\n==========================================\n");
        printf("--- Testing Single Columnar ATSP for Width %d (%d x %d) ---\n", W, N/W, W);
        printf("==========================================\n");

        float best_w_sc = -999.0f;
        int best_cand_idx = -1;
        int best_order[16];
        int best_pt[N];

        double t0 = omp_get_wtime();

        #pragma omp parallel for schedule(dynamic)
        for (int i = 0; i < count; i++) {
            int z[N];
            decrypt_to_z(cands[i].mode, cands[i].q4, cands[i].q7, z);

            int order[16];
            int pt[N];
            float sc = solve_atsp(z, W, order, pt);

            #pragma omp critical
            {
                if (sc > best_w_sc) {
                    best_w_sc = sc;
                    best_cand_idx = i;
                    memcpy(best_order, order, W * sizeof(int));
                    memcpy(best_pt, pt, N * sizeof(int));

                    char pt_str[N+1];
                    for (int k = 0; k < N; k++) pt_str[k] = pt[k] + 'A';
                    pt_str[N] = 0;

                    printf("[Width %2d] New Best: %.4f | Mode %d | Cand #%d | Order: [",
                           W, sc, cands[i].mode, i);
                    for (int c = 0; c < W; c++) printf("%d%s", order[c], c==W-1?"":", ");
                    printf("]\n  PT: %.80s...\n", pt_str);
                }
            }
        }

        double elapsed = omp_get_wtime() - t0;
        printf("Width %d scan finished in %.2f seconds. Best Score: %.4f\n", W, elapsed, best_w_sc);
        char final_pt[N+1];
        for (int k = 0; k < N; k++) final_pt[k] = best_pt[k] + 'A';
        final_pt[N] = 0;
        printf("Decrypted text (Width %d):\n%s\n", W, final_pt);
    }

    return 0;
}
