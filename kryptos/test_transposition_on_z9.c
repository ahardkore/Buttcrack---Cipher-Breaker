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
    if (!f) { printf("Cannot open english_quadgrams.txt\n"); exit(1); }
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

static const char *Z9 = "KTNWGSTYKVOVNSENPXAVKTOSXMSKQSEMMJPWHLASMEYGYNOSIHRECTNSSNOEETLLCOLTIEAIORPEAXTABEMSNNSFXMSUHOILNSUTGTBEZCYWEDMASNCDDCOUMTJTDSUMTATTNEUWJWFAIHIK";

float score_text(const char *t) {
    float sc = 0.0f;
    for (int i=0; i<N-3; i++) {
        sc += quad[t[i]-'A'][t[i+1]-'A'][t[i+2]-'A'][t[i+3]-'A'];
    }
    return sc / (N - 3);
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

typedef struct {
    char word[32];
    int order[32];
} KeyOrder;

int load_orders(const char *fn, int w, KeyOrder *out, int max_n) {
    FILE *f = fopen(fn, "r");
    if (!f) return 0;
    char line[128];
    int count = 0;
    while (fgets(line, sizeof(line), f) && count < max_n) {
        char word[32];
        if (sscanf(line, "%s", word) != 1) continue;
        if (strlen(word) != w) continue;
        int ok = 1;
        for (int i = 0; i < w; i++) {
            if (word[i] < 'A' || word[i] > 'Z') { ok = 0; break; }
        }
        if (!ok) continue;
        
        int ord[32];
        for (int i = 0; i < w; i++) ord[i] = i;
        for (int i = 0; i < w - 1; i++) {
            for (int j = i + 1; j < w; j++) {
                if (word[ord[i]] > word[ord[j]]) {
                    int tmp = ord[i]; ord[i] = ord[j]; ord[j] = tmp;
                }
            }
        }
        
        int duplicate = 0;
        for (int i = 0; i < count; i++) {
            int same = 1;
            for (int k = 0; k < w; k++) {
                if (out[i].order[k] != ord[k]) { same = 0; break; }
            }
            if (same) { duplicate = 1; break; }
        }
        if (!duplicate) {
            strcpy(out[count].word, word);
            for (int k = 0; k < w; k++) out[count].order[k] = ord[k];
            count++;
        }
    }
    fclose(f);
    return count;
}

void test_double_on_z9(int w) {
    char fn[64];
    KeyOrder keys[1200];
    sprintf(fn, "theophilus_w%d.txt", w);
    int n_keys = load_orders(fn, w, keys, 1200);
    sprintf(fn, "curated_w%d.txt", w);
    int n2 = load_orders(fn, w, keys + n_keys, 1200 - n_keys);
    n_keys += n2;
    sprintf(fn, "words_%d.txt", w);
    int n3 = load_orders(fn, w, keys + n_keys, 1200 - n_keys);
    n_keys += n3;
    printf("\n=== Testing Double Columnar on Z9 at Width %d (%d orders) ===\n", w, n_keys);
    
    float global_best = -999.0f;
    int best_i = -1, best_j = -1;
    char best_pt[N+1];
    
    #pragma omp parallel
    {
        float local_best = -999.0f;
        int local_bi = -1, local_bj = -1;
        char local_pt[N+1];
        int map1[N], map2[N];
        char pt[N + 1];
        pt[N] = '\0';
        
        #pragma omp for schedule(dynamic)
        for (int i = 0; i < n_keys; i++) {
            get_col_map(w, keys[i].order, map1);
            for (int j = 0; j < n_keys; j++) {
                get_col_map(w, keys[j].order, map2);
                for (int k = 0; k < N; k++) {
                    pt[k] = Z9[map1[map2[k]]];
                }
                float sc = score_text(pt);
                if (sc > -5.2f) {
                    #pragma omp critical
                    {
                        printf("\n*** HIGH SCORE HIT! Quad=%.3f | w=%d ***\n", sc, w);
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
    
    printf("Width %d Double Columnar Best Quad: %.3f\n", w, global_best);
    if (best_i >= 0 && best_j >= 0) {
        printf("  KW1: %s | KW2: %s\n", keys[best_i].word, keys[best_j].word);
        printf("  PT: %s\n", best_pt);
    }
}

int main() {
    load_quads();
    printf("Quadgram model loaded.\n");
    test_double_on_z9(8);
    test_double_on_z9(9);
    test_double_on_z9(12);
    return 0;
}
