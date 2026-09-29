#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>

#define N 144

const char *KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
const char *PK9_CT = "KSYAWFEYYOISZGEUFBLYATAIBYFAQBQYYVDWJKLJXMYIEPIFVHPQNHZGSUHUUDXLEHRHUMALHEGLHXSJMUXGNUIVBXGUJHZRZGUSVHMLSCTSUQXHSUMQQIFUQGKHJGUQGLHDKEWSKAMHIJXD";

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

float solve_held_karp(const char *text, int w, int *best_order, char *out_plain) {
    int h = N / w;
    char B[16][144];
    for (int k = 0; k < w; k++) {
        for (int r = 0; r < h; r++) {
            B[k][r] = text[k * h + r];
        }
    }

    float T[16][16], Wm[16][16];
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

    float dp[1 << 10][10];
    int par[1 << 10][10];

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
                for (int i = 0; i < w; i++) global_best_seq[i] = seq[w - 1 - i];
            }
        }
    }

    if (best_order) {
        for (int c = 0; c < w; c++) best_order[global_best_seq[c]] = c;
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

typedef struct {
    char word[8];
    int idx[7];
} Word7;

static Word7 words7[50000];
static int n7 = 0;

void load_words() {
    FILE *f = fopen("words_7.txt", "r");
    char buf[64];
    while (fgets(buf, sizeof(buf), f) && n7 < 50000) {
        buf[strcspn(buf, "\r\n")] = 0;
        if (strlen(buf) == 7) {
            int valid = 1;
            for (int i = 0; i < 7; i++) {
                int k = char_to_k[(unsigned char)buf[i]];
                if (k < 0) { valid = 0; break; }
                words7[n7].idx[i] = k;
            }
            if (valid) {
                strcpy(words7[n7].word, buf);
                n7++;
            }
        }
    }
    fclose(f);
    printf("Loaded %d 7-letter words\n", n7);
}

int main() {
    init_tables();
    load_words();

    int test_widths[3] = {6, 8, 9};

    for (int widx = 0; widx < 3; widx++) {
        int w = test_widths[widx];
        printf("\n=== Sweeping all %d words for Width %d Columnar on PK9 ===\n", n7, w);

        float best_sc = -999.0f;
        char best_word[8] = "";
        char best_pt[N + 1] = "";
        int best_order[16];

        double t0 = omp_get_wtime();

        #pragma omp parallel
        {
            float local_best_sc = -999.0f;
            char local_best_word[8] = "";
            char local_best_pt[N + 1] = "";
            int local_best_order[16];

            #pragma omp for schedule(dynamic, 64)
            for (int i = 0; i < n7; i++) {
                const Word7 *pw = &words7[i];

                char X[N + 1];
                for (int j = 0; j < N; j++) {
                    int k = pw->idx[j % 7];
                    int p = (c_idx[j] - k + 26) % 26;
                    X[j] = 'A' + alpha_to_std[p];
                }
                X[N] = '\0';

                int order[16];
                char plain[N + 1];
                float sc = solve_held_karp(X, w, order, plain);

                if (sc > -380.0f) {
                    #pragma omp critical
                    {
                        printf("\n>>> CANDIDATE HIT! Score=%.2f (avg=%.3f) | Word: %s\n",
                               sc, sc / N, pw->word);
                        printf("  Order: [");
                        for (int k = 0; k < w; k++) printf("%d%s", order[k], k == w - 1 ? "]\n" : ", ");
                        printf("  PT: %s\n\n", plain);
                        fflush(stdout);
                    }
                }

                if (sc > local_best_sc) {
                    local_best_sc = sc;
                    strcpy(local_best_word, pw->word);
                    strcpy(local_best_pt, plain);
                    for (int k = 0; k < w; k++) local_best_order[k] = order[k];
                }
            }

            #pragma omp critical
            {
                if (local_best_sc > best_sc) {
                    best_sc = local_best_sc;
                    strcpy(best_word, local_best_word);
                    strcpy(best_pt, local_best_pt);
                    for (int k = 0; k < w; k++) best_order[k] = local_best_order[k];
                }
            }
        }

        double elapsed = omp_get_wtime() - t0;
        printf("Completed Width %d in %.2f s (%.1f words/sec)\n", elapsed, n7 / elapsed);
        printf("Best Score = %.2f (avg = %.3f) | Word: %s\n", best_sc, best_sc / N, best_word);
        printf("Order: [");
        for (int k = 0; k < w; k++) printf("%d%s", best_order[k], k == w - 1 ? "]\n" : ", ");
        printf("Plaintext: %.80s...\n", best_pt);
    }

    return 0;
}
