#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <time.h>
#include <omp.h>

#define N 504

static const char *Z_text = "POZMIYMSENAKOAHAEQXNMJTISSDIEBAONEHZILNLBAAZSZTZEMAKSBYVSKNMQUTWRELUNEZASINREEWCEEKGPEQBELDZEXHPSGEBEUBIEECXEWEILOLEDCQIHOELNEPRSFFBDAESGRGOTDHXIJHXALSNIEPOISEAAIRZPFLCMMTAYXAKUIYHPWFOSFCSPTYRYBMSITTFCILELNZSNQNANHUAIEXHQTEGNMLBEAEPYDWTNIHNUTFUHREGCEQOEEPSELCWNNCZEOCTTEERVEILEDREHBWGYESOHKAATTSQCAICKLDYNRMHXYGFYCRRUOTQPKAHTEEPCJITOHSAXQXJASGETOEIEDCATCRSSHIERKEYZTPOWIPDMPCRAKDCKUMOYGEURTZUIEKTMAATVLNHNFZRECGTWEHXNMVNRHOMXXTDRJSEOIUCMSHSHDOETEIEZNXFRWLEETELTDVUOMOTBIEMXNEPRWTBMHILRREJWEIGUGVFTSLFWSGF";

static float quadgrams[26][26][26][26];

void load_quads() {
    float floor_val = -8.728227f;
    for (int i=0; i<26; i++)
        for (int j=0; j<26; j++)
            for (int k=0; k<26; k++)
                for (int l=0; l<26; l++)
                    quadgrams[i][j][k][l] = floor_val;

    FILE *f = fopen("buttcrack/src/buttcrack/data/english_quadgrams.txt", "r");
    if (!f) f = fopen("english_quadgrams.txt", "r");
    char line[64];
    double total = 5348433.0;
    while (fgets(line, sizeof(line), f)) {
        char g[5]; double cnt;
        if (sscanf(line, "%4s %lf", g, &cnt) == 2) {
            int a = g[0]-'A', b = g[1]-'A', c = g[2]-'A', d = g[3]-'A';
            if (a>=0&&a<26&&b>=0&&b<26&&c>=0&&c<26&&d>=0&&d<26) {
                quadgrams[a][b][c][d] = (float)log10(cnt / total);
            }
        }
    }
    fclose(f);
}

static inline unsigned int xorshift32(unsigned int *state) {
    unsigned int x = *state;
    x ^= x << 13;
    x ^= x >> 17;
    x ^= x << 5;
    *state = x;
    return x;
}

void sa_width(int W, int restarts, int steps) {
    int H = N / W;
    int Z_int[N];
    for (int i=0; i<N; i++) Z_int[i] = Z_text[i] - 'A';

    float global_best_sc = -1e9;
    int global_best_order[64];
    char global_best_pt[N+1];

    double t0 = omp_get_wtime();

    #pragma omp parallel
    {
        unsigned int seed = (unsigned int)(time(NULL) ^ (omp_get_thread_num() * 777 + W * 31));

        #pragma omp for schedule(dynamic, 1)
        for (int r = 0; r < restarts; r++) {
            int order[64];
            for (int i = 0; i < W; i++) order[i] = i;
            for (int i = W - 1; i > 0; i--) {
                int j = xorshift32(&seed) % (i + 1);
                int t = order[i]; order[i] = order[j]; order[j] = t;
            }

            int grid[600][64];
            int plain[N];

            // Decode
            int k = 0;
            for (int c = 0; c < W; c++) {
                int col = order[c];
                for (int row = 0; row < H; row++) grid[row][col] = Z_int[k++];
            }
            k = 0;
            for (int row = 0; row < H; row++)
                for (int c = 0; c < W; c++) plain[k++] = grid[row][c];

            float cur_sc = 0;
            for (int i = 0; i < N - 3; i++) {
                cur_sc += quadgrams[plain[i]][plain[i+1]][plain[i+2]][plain[i+3]];
            }
            cur_sc /= (N - 3);

            float best_sc = cur_sc;
            int best_order[64];
            memcpy(best_order, order, W * sizeof(int));

            float temp = 1.5f;
            float cooling = expf(logf(0.005f / 1.5f) / steps);

            for (int s = 0; s < steps; s++) {
                int i = xorshift32(&seed) % W;
                int j = xorshift32(&seed) % W;
                while (i == j) j = xorshift32(&seed) % W;

                // Swap columns
                int tmp = order[i]; order[i] = order[j]; order[j] = tmp;

                // Re-decode
                k = 0;
                for (int c = 0; c < W; c++) {
                    int col = order[c];
                    for (int row = 0; row < H; row++) grid[row][col] = Z_int[k++];
                }
                k = 0;
                for (int row = 0; row < H; row++)
                    for (int c = 0; c < W; c++) plain[k++] = grid[row][c];

                float new_sc = 0;
                for (int idx = 0; idx < N - 3; idx++) {
                    new_sc += quadgrams[plain[idx]][plain[idx+1]][plain[idx+2]][plain[idx+3]];
                }
                new_sc /= (N - 3);

                float delta = new_sc - cur_sc;
                if (delta > 0 || ((float)xorshift32(&seed) / 4294967296.0f) < expf(delta / temp)) {
                    cur_sc = new_sc;
                    if (cur_sc > best_sc) {
                        best_sc = cur_sc;
                        memcpy(best_order, order, W * sizeof(int));
                    }
                } else {
                    order[j] = order[i]; order[i] = tmp;
                }

                temp *= cooling;
            }

            #pragma omp critical
            {
                if (best_sc > global_best_sc) {
                    global_best_sc = best_sc;
                    memcpy(global_best_order, best_order, W * sizeof(int));
                    // Recompute pt
                    k = 0;
                    for (int c = 0; c < W; c++) {
                        int col = best_order[c];
                        for (int row = 0; row < H; row++) grid[row][col] = Z_int[k++];
                    }
                    k = 0;
                    for (int row = 0; row < H; row++)
                        for (int c = 0; c < W; c++) global_best_pt[k++] = grid[row][c] + 'A';
                    global_best_pt[N] = 0;
                }
            }
        }
    }

    double elapsed = omp_get_wtime() - t0;
    printf("Width %2d (grid %2d x %2d) finished in %.2fs: Best Score = %.4f\nOrder: [",
           W, H, W, elapsed, global_best_sc);
    for (int i = 0; i < W; i++) printf("%d%s", global_best_order[i], i < W - 1 ? ", " : "]\n");
    printf("PT: %.100s...\n\n", global_best_pt);
}

int main() {
    load_quads();
    printf("Starting OpenMP Simulated Annealing on PK10 intermediate text Z across widths...\n");
    sa_width(12, 32, 100000);
    sa_width(14, 32, 100000);
    sa_width(18, 32, 100000);
    sa_width(21, 32, 100000);
    sa_width(24, 32, 100000);
    return 0;
}
