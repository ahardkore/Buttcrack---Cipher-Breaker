#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>

#define N 144

static float quad[26][26][26][26];

void load_quads() {
    for (int a=0; a<26; a++)
        for (int b=0; b<26; b++)
            for (int c=0; c<26; c++)
                for (int d=0; d<26; d++)
                    quad[a][b][c][d] = -9.5f;
    FILE *f = fopen("english_quadgrams.txt", "r");
    if (!f) return;
    char q[16]; float cnt;
    double total = 0;
    while (fscanf(f, "%s %f", q, &cnt) == 2) {
        if (strlen(q) == 4) total += cnt;
    }
    rewind(f);
    while (fscanf(f, "%s %f", q, &cnt) == 2) {
        if (strlen(q) == 4) {
            int a = q[0]-'A', b = q[1]-'A', c = q[2]-'A', d = q[3]-'A';
            if (a>=0 && a<26 && b>=0 && b<26 && c>=0 && c<26 && d>=0 && d<26) {
                quad[a][b][c][d] = (float)log10((cnt + 0.01) / total);
            }
        }
    }
    fclose(f);
}

static const char *KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
static const char *PK9_REAL = "KSYAWFEYYOISZGEUFBLYATAIBYFAQBQYYVDWJKLJXMYIEPIFVHPQNHZGSUHUUDXLEHRHUMALHEGLHXSJMUXGNUIVBXGUJHZRZGUSVHMLSCTSUQXHSUMQQIFUQGKHJGUQGLHDKEWSKAMHIJXD";

static const int shifts28[28] = {
    5, 4, 9, 15, 16, 5, 6, 14, 5, 25, 20, 21, 10, 7, 14, 11, 7, 25, 10, 24, 22, 23, 18, 1, 7, 10, 7, 3
};

static char z_str[N + 1];

void init() {
    int hpos[256];
    for (int i=0; i<26; i++) hpos[(unsigned char)KRYPTOS[i]] = i;
    for (int i=0; i<N; i++) {
        int c_idx = hpos[(unsigned char)PK9_REAL[i]];
        int p_kr = (c_idx - shifts28[i % 28] + 26) % 26;
        z_str[i] = KRYPTOS[p_kr];
    }
    z_str[N] = '\0';
}

float score_text(const char *t) {
    float sc = 0.0f;
    for (int i=0; i<N-3; i++) {
        sc += quad[t[i]-'A'][t[i+1]-'A'][t[i+2]-'A'][t[i+3]-'A'];
    }
    return sc / (N - 3);
}

typedef struct {
    char word[32];
    int order[32];
} KeyOrder;

void get_word_order(const char *w, int len, int *order) {
    for (int i=0; i<len; i++) order[i] = i;
    for (int i=0; i<len-1; i++) {
        for (int j=i+1; j<len; j++) {
            if (w[order[i]] > w[order[j]]) {
                int tmp = order[i]; order[i] = order[j]; order[j] = tmp;
            }
        }
    }
}

int load_words(const char *fn, int w, KeyOrder *out, int max_n) {
    FILE *f = fopen(fn, "r");
    if (!f) return 0;
    char line[64];
    int count = 0;
    while (fscanf(f, "%63s", line) == 1 && count < max_n) {
        if (strlen(line) != w) continue;
        int ok = 1;
        for (int i=0; i<w; i++) {
            if (line[i] < 'A' || line[i] > 'Z') { ok = 0; break; }
        }
        if (!ok) continue;
        strcpy(out[count].word, line);
        get_word_order(line, w, out[count].order);
        count++;
    }
    fclose(f);
    return count;
}

void get_col_map(int w, const int *o, int *map) {
    int h = N / w;
    for (int c = 0; c < w; c++) {
        int col = o[c];
        for (int r = 0; r < h; r++) {
            map[r * w + col] = c * h + r;
        }
    }
}

void test_double(const char *fn, int w) {
    KeyOrder *keys = malloc(50000 * sizeof(KeyOrder));
    int n_keys = load_words(fn, w, keys, 50000);
    printf("Loaded %d keys from %s (width %d). Pairs: %lld\n",
           n_keys, fn, w, (long long)n_keys * n_keys);
    
    double t0 = omp_get_wtime();
    float global_best = -999.0f;
    int best_i = -1, best_j = -1;
    char best_pt[N+1];
    
    #pragma omp parallel
    {
        float local_best = -999.0f;
        int local_bi = -1, local_bj = -1;
        char local_pt[N+1];
        char pt[N+1];
        pt[N] = '\0';
        int map1[N], map2[N];
        
        #pragma omp for schedule(dynamic, 10)
        for (int i = 0; i < n_keys; i++) {
            get_col_map(w, keys[i].order, map1);
            for (int j = 0; j < n_keys; j++) {
                get_col_map(w, keys[j].order, map2);
                
                for (int k = 0; k < N; k++) {
                    pt[k] = z_str[map1[map2[k]]];
                }
                
                float sc = score_text(pt);
                if (sc > -5.2f) {
                    #pragma omp critical
                    {
                        printf("\n*** HIGH SCORE DOUBLE COL HIT! Width %d | Quad: %.3f ***\n", w, sc);
                        printf("  KW1: %s | KW2: %s\n", keys[i].word, keys[j].word);
                        printf("  PT: %s\n", pt);
                    }
                }
                if (sc > local_best) {
                    local_best = sc;
                    local_bi = i;
                    local_bj = j;
                    strcpy(local_pt, pt);
                }
            }
        }
        
        #pragma omp critical
        {
            if (local_best > global_best) {
                global_best = local_best;
                best_i = local_bi;
                best_j = local_bj;
                strcpy(best_pt, local_pt);
            }
        }
    }
    
    double elapsed = omp_get_wtime() - t0;
    printf("Width %d Double Col: %.2f s | Best Quad: %.3f\n", w, elapsed, global_best);
    if (best_i >= 0 && best_j >= 0) {
        printf("  KW1: %s | KW2: %s\n", keys[best_i].word, keys[best_j].word);
        printf("  PT: %s\n", best_pt);
    }
    free(keys);
}

int main() {
    load_quads();
    init();
    printf("z_str initialized: %s\n\n", z_str);
    test_double("theophilus_w8.txt", 8);
    test_double("theophilus_w9.txt", 9);
    test_double("theophilus_w12_all.txt", 12);
    return 0;
}
