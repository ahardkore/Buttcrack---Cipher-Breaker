#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
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

int next_perm(int *arr, int n) {
    int i = n - 2;
    while (i >= 0 && arr[i] >= arr[i+1]) i--;
    if (i < 0) return 0;
    int j = n - 1;
    while (arr[j] <= arr[i]) j--;
    int tmp = arr[i]; arr[i] = arr[j]; arr[j] = tmp;
    int l = i + 1, r = n - 1;
    while (l < r) {
        tmp = arr[l]; arr[l] = arr[r]; arr[r] = tmp;
        l++; r--;
    }
    return 1;
}

void test_width(int W) {
    int H = N / W;
    long long total_perms = 1;
    for (int i = 1; i <= W; i++) total_perms *= i;

    printf("Generating %lld permutations for Width %d (grid %d x %d)...\n",
           total_perms, W, H, W);

    int (*perms)[W] = malloc(total_perms * sizeof(*perms));
    int cur[W];
    for (int i = 0; i < W; i++) cur[i] = i;
    long long idx = 0;
    do {
        for (int i = 0; i < W; i++) perms[idx][i] = cur[i];
        idx++;
    } while (next_perm(cur, W));

    int Z_int[N];
    for (int i = 0; i < N; i++) Z_int[i] = Z_text[i] - 'A';

    float best_sc = -1e9;
    int best_perm[W];
    char best_pt[N + 1];

    double t0 = omp_get_wtime();

    #pragma omp parallel
    {
        float local_best = -1e9;
        int local_perm[W];
        char local_pt[N + 1];

        #pragma omp for schedule(dynamic, 1000)
        for (long long p = 0; p < total_perms; p++) {
            const int *order = perms[p];

            // Invert columnar:
            // order specifies column order
            // grid[r][order[c]] = Z_int[c * H + r]
            int plain[N];
            int pt_idx = 0;

            // Fill grid
            int grid[H][W];
            int k = 0;
            for (int c = 0; c < W; c++) {
                int col = order[c];
                for (int r = 0; r < H; r++) {
                    grid[r][col] = Z_int[k++];
                }
            }

            // Read by rows
            for (int r = 0; r < H; r++) {
                for (int c = 0; c < W; c++) {
                    plain[pt_idx++] = grid[r][c];
                }
            }

            // Score quadgrams
            float sc = 0;
            for (int i = 0; i < N - 3; i++) {
                sc += quadgrams[plain[i]][plain[i+1]][plain[i+2]][plain[i+3]];
            }
            sc /= (N - 3);

            if (sc > local_best) {
                local_best = sc;
                for (int i = 0; i < W; i++) local_perm[i] = order[i];
                for (int i = 0; i < N; i++) local_pt[i] = plain[i] + 'A';
                local_pt[N] = 0;
            }
        }

        #pragma omp critical
        {
            if (local_best > best_sc) {
                best_sc = local_best;
                for (int i = 0; i < W; i++) best_perm[i] = local_perm[i];
                strcpy(best_pt, local_pt);
            }
        }
    }

    double elapsed = omp_get_wtime() - t0;
    printf("Width %d finished in %.3f s. Best Score = %.4f\nOrder: [",
           W, elapsed, best_sc);
    for (int i = 0; i < W; i++) printf("%d%s", best_perm[i], i < W - 1 ? ", " : "]\n");
    printf("PT: %.100s...\n\n", best_pt);

    free(perms);
}

int main() {
    load_quads();
    test_width(7);
    test_width(8);
    test_width(9);
    return 0;
}
