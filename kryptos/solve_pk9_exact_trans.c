#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

#define N 144

const char *KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
const char *PK9_CT = "KSYAWFEYYOISZGEUFBLYATAIBYFAQBQYYVDWJKLJXMYIEPIFVHPQNHZGSUHUUDXLEHRHUMALHEGLHXSJMUXGNUIVBXGUJHZRZGUSVHMLSCTSUQXHSUMQQIFUQGKHJGUQGLHDKEWSKAMHIJXD";

static const int q4[4] = {16, 23, 22, 18};
static const int q7[7] = {10, 19, 17, 25, 16, 18, 10};

static int c_idx[N];
static int alpha_to_std[26];
static char X[N + 1];
static float bigram_table[26][26];

void init_tables() {
    for (int i = 0; i < 26; i++) alpha_to_std[i] = KRYPTOS[i] - 'A';
    for (int i = 0; i < N; i++) c_idx[i] = strchr(KRYPTOS, PK9_CT[i]) - KRYPTOS;

    for (int i = 0; i < N; i++) {
        int k = (q4[i % 4] + q7[i % 7]) % 26;
        int p = (c_idx[i] - k + 26) % 26;
        X[i] = 'A' + alpha_to_std[p];
    }
    X[N] = '\0';

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

int main() {
    init_tables();
    printf("Pre-transposition stream X:\n%s\n\n", X);

    // Grid: Row r, Col c is X[r * 12 + c]
    // Column c is Col[c][r] = X[r * 12 + c]
    char Col[12][12];
    for (int c = 0; c < 12; c++) {
        for (int r = 0; r < 12; r++) {
            Col[c][r] = X[r * 12 + c];
        }
    }

    // T[i][j]: score if column j immediately follows column i
    float T[12][12];
    float Wm[12][12]; // Wrap score: from end of row (column i) to start of next row (column j)

    for (int i = 0; i < 12; i++) {
        for (int j = 0; j < 12; j++) {
            if (i == j) {
                T[i][j] = -1e9f;
                Wm[i][j] = -1e9f;
            } else {
                float sT = 0.0f;
                for (int r = 0; r < 12; r++) sT += get_lp(Col[i][r], Col[j][r]);
                T[i][j] = sT;

                float sW = 0.0f;
                for (int r = 0; r < 11; r++) sW += get_lp(Col[i][r], Col[j][r+1]);
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

    printf("Optimal Column Sequence: [");
    for (int i = 0; i < 12; i++) printf("%d%s", global_best_seq[i], i==11?"]\n":", ");
    printf("Total Bigram Score = %.2f (avg = %.3f)\n\n", global_best_score, global_best_score / 144);

    char plain[N + 1];
    int idx = 0;
    for (int r = 0; r < 12; r++) {
        for (int c = 0; c < 12; c++) {
            plain[idx++] = Col[global_best_seq[c]][r];
        }
    }
    plain[N] = '\0';

    printf("Decrypted Plaintext (Row by Row):\n");
    for (int r = 0; r < 12; r++) {
        printf("Row %2d: %.12s\n", r, plain + r * 12);
    }
    printf("\nFull Plaintext:\n%s\n", plain);

    return 0;
}
