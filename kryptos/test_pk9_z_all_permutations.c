#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>

#define N 144

static const char *Z_text = "KTNWGSTYKVOVNSENPXAVKTOSXMSKQSEMMJPWHLASMEYGYNOSIHRECTNSSNOEETLLCOLTIEAIORPEAXTABEMSNNSFXMSUHOILNSUTGTBEZCYWEDMASNCDDCOUMTJTDSUMTATTNEUWJWFAIHIK";

static float quadgrams[26][26][26][26];

static void init_tables(void) {
    for (int a = 0; a < 26; a++)
        for (int b = 0; b < 26; b++)
            for (int c = 0; c < 26; c++)
                for (int d = 0; d < 26; d++)
                    quadgrams[a][b][c][d] = -12.0f;

    FILE *f = fopen("english_quadgrams.txt", "r");
    if (!f) return;
    char line[64];
    long long total = 0;
    while (fgets(line, sizeof(line), f)) {
        char qg[5]; long long cnt;
        if (sscanf(line, "%4s %lld", qg, &cnt) == 2) total += cnt;
    }
    fseek(f, 0, SEEK_SET);
    while (fgets(line, sizeof(line), f)) {
        char qg[5]; long long cnt;
        if (sscanf(line, "%4s %lld", qg, &cnt) == 2) {
            int a = qg[0] - 'A', b = qg[1] - 'A', c = qg[2] - 'A', d = qg[3] - 'A';
            if (a >= 0 && a < 26 && b >= 0 && b < 26 && c >= 0 && c < 26 && d >= 0 && d < 26) {
                quadgrams[a][b][c][d] = log10f((float)cnt / total);
            }
        }
    }
    fclose(f);
}

void col_decrypt(const char *in, const int *order, char *out, int w, int h) {
    char grid[64][64];
    int idx = 0;
    for (int k = 0; k < w; k++) {
        int col = order[k];
        for (int r = 0; r < h; r++) grid[r][col] = in[idx++];
    }
    idx = 0;
    for (int r = 0; r < h; r++)
        for (int c = 0; c < w; c++) out[idx++] = grid[r][c];
    out[N] = '\0';
}

static inline float score_text(const char *pt) {
    float sc = 0;
    for (int t = 0; t < N - 3; t++) {
        sc += quadgrams[pt[t]-'A'][pt[t+1]-'A'][pt[t+2]-'A'][pt[t+3]-'A'];
    }
    return sc / (N - 3);
}

// Next permutation
int next_perm(int *arr, int n) {
    int i = n - 2;
    while (i >= 0 && arr[i] >= arr[i + 1]) i--;
    if (i < 0) return 0;
    int j = n - 1;
    while (arr[j] <= arr[i]) j--;
    int tmp = arr[i]; arr[i] = arr[j]; arr[j] = tmp;
    int l = i + 1, r = n - 1;
    while (l < r) { tmp = arr[l]; arr[l] = arr[r]; arr[r] = tmp; l++; r--; }
    return 1;
}

int main(void) {
    init_tables();

    int widths[] = {4, 6, 8, 9};
    int n_widths = 4;

    for (int wi = 0; wi < n_widths; wi++) {
        int w = widths[wi];
        int h = N / w;

        int perm[16];
        for (int i = 0; i < w; i++) perm[i] = i;

        float best_sc = -1e9f;
        char best_pt[N + 1];
        int best_perm[16];

        long long count = 0;
        double t0 = omp_get_wtime();

        do {
            char pt[N + 1];
            col_decrypt(Z_text, perm, pt, w, h);
            float sc = score_text(pt);
            if (sc > best_sc) {
                best_sc = sc;
                strcpy(best_pt, pt);
                memcpy(best_perm, perm, w * sizeof(int));
            }
            count++;
        } while (next_perm(perm, w));

        double t1 = omp_get_wtime();
        printf("Width %2d (%d rows, %lld perms, %.3fs): Best Score = %5.2f | Perm: [",
            w, h, count, t1 - t0, best_sc);
        for (int i = 0; i < w; i++) printf("%d%s", best_perm[i], i < w - 1 ? ", " : "]\n");
        printf("  PT: %s\n\n", best_pt);
    }

    return 0;
}
