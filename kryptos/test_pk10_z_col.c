#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>

#define N 504

static const char *Z_504 = "EFQEZMTSQTWLHMRRRPYBMAAREHIEYWLJVGENHSVAEMIDTWNIHTAUTENPYNATMWLNCSIPNFHKDGRYSOFOOGTAFRWEYSNXFRBHEDDOTULSACPVPRTFXAACRGSUXNHOLEHETMIHOAWFBLNVTKRQYFCRWRHVRJWYYLAFCTIKOHOEUMNLHMULDAUAETZCEEJHEHEEULANLOIEYIGAEWQGYRCALAUEOGFGUICONVEDAJDFRETVIHTHQLFPOETSAFPNZPDNASNNBRIHFWFBTCCVMIYPYAMEPKAFCDGCNKHUEMDEOMHCUYXIUUCISHASHFKNECVKGKFWBHPVFPKHAAMCUUZAYHDBWWLSYDSYIDTNBPLOLRDPFOIEMDPTJMDLAZGASSPGLTPRJERYWYUMUMDLFTAONFUYDLENIOVWNESOBNFYVUTEKPESGIVCUHODTEHOIETDENRISTAPUIHSGBKICSLMBSNOUPINAHMSTFFYXLDSIUCXJOVBNCTEIHTB";

static float quadgrams[26][26][26][26];

void load_quads(void) {
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

void get_order(const char *word, int *order, int len) {
    int used[128] = {0};
    int k = 0;
    for (char ch = 'A'; ch <= 'Z'; ch++) {
        for (int i = 0; i < len; i++) {
            if (word[i] == ch && !used[i]) {
                order[k++] = i;
                used[i] = 1;
            }
        }
    }
}

void col_decrypt(const char *in, const int *order, char *out, int w, int h) {
    char grid[100][100];
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

void test_file(const char *filename, int w) {
    FILE *f = fopen(filename, "r");
    if (!f) return;
    int h = N / w;

    char word[64];
    float best_sc = -1e9f;
    char best_w[64];
    char best_pt[N + 1];
    long tested = 0;

    #pragma omp parallel
    {
        float local_sc = -1e9f;
        char local_w[64];
        char local_pt[N + 1];

        #pragma omp for schedule(dynamic, 100)
        for (int line = 0; line < 100000; line++) {
            // Read sequentially or in memory
        }
    }
}

int main(void) {
    load_quads();

    int widths[] = {7, 8, 9, 12, 14, 18, 21, 24, 28, 36, 42};
    int n_w = sizeof(widths) / sizeof(widths[0]);

    for (int wi = 0; wi < n_w; wi++) {
        int w = widths[wi];
        int h = N / w;
        char fn[64];
        sprintf(fn, "words_%d.txt", w);

        FILE *f = fopen(fn, "r");
        if (!f) {
            sprintf(fn, "theophilus_w%d.txt", w);
            f = fopen(fn, "r");
            if (!f) continue;
        }

        char (*wlist)[64] = malloc(100000 * sizeof(*wlist));
        int n_words = 0;
        while (fscanf(f, "%63s", wlist[n_words]) == 1) {
            if ((int)strlen(wlist[n_words]) == w) n_words++;
        }
        fclose(f);

        if (n_words == 0) { free(wlist); continue; }

        float best_sc = -1e9f;
        char best_w[64];
        char best_pt[N + 1];

        #pragma omp parallel
        {
            float local_sc = -1e9f;
            char local_w[64];
            char local_pt[N + 1];

            #pragma omp for schedule(static, 100)
            for (int i = 0; i < n_words; i++) {
                int order[64];
                get_order(wlist[i], order, w);
                char pt[N + 1];
                col_decrypt(Z_504, order, pt, w, h);
                float sc = score_text(pt);
                if (sc > local_sc) {
                    local_sc = sc;
                    strcpy(local_w, wlist[i]);
                    strcpy(local_pt, pt);
                }
            }

            #pragma omp critical
            {
                if (local_sc > best_sc) {
                    best_sc = local_sc;
                    strcpy(best_w, local_w);
                    strcpy(best_pt, local_pt);
                }
            }
        }

        printf("Width %2d (%d words): Best Score = %5.2f | Word = %s\n",
            w, n_words, best_sc, best_w);
        printf("  PT: %.80s...\n\n", best_pt);
        free(wlist);
    }

    return 0;
}
