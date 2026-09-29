#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <omp.h>

#define N 144

static const char *PK9_CT = "KSYAWFEYYOISZGEUFBLYATAIBYFAQBQGZGSMMJHJQNHSVHAWFLHXLSKALEHHSUUFBVBXJXMMHIRHUMQQLYAGUJYIEJXDMALIFUTAIHZRPIFLSEYYSJMQYYLHDUHUCTSOISUXGVDWKEWUDXUQXZGENUIJK";

void get_col_map(int w, const int *o, int *map) {
    int h = N / w;
    for (int c = 0; c < w; c++) {
        int col = o[c];
        for (int r = 0; r < h; r++) {
            map[r * w + col] = c * h + r;
        }
    }
}

float col_ioc(const char *txt, int p) {
    int counts[26];
    float total_ioc = 0.0f;
    for (int rem = 0; rem < p; rem++) {
        memset(counts, 0, sizeof(counts));
        int n_letters = 0;
        for (int i = rem; i < N; i += p) {
            counts[txt[i] - 'A']++;
            n_letters++;
        }
        if (n_letters > 1) {
            int num = 0;
            for (int k = 0; k < 26; k++) num += counts[k] * (counts[k] - 1);
            total_ioc += (float)num / (float)(n_letters * (n_letters - 1));
        }
    }
    return total_ioc / (float)p;
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

void run_width(int w) {
    char fn[64];
    KeyOrder keys[1000];
    sprintf(fn, "theophilus_w%d.txt", w);
    int n_keys = load_orders(fn, w, keys, 1000);
    sprintf(fn, "curated_w%d.txt", w);
    int n2 = load_orders(fn, w, keys + n_keys, 1000 - n_keys);
    n_keys += n2;
    sprintf(fn, "words_%d.txt", w);
    int n3 = load_orders(fn, w, keys + n_keys, 1000 - n_keys);
    n_keys += n3;
    printf("\n=== Width %d: loaded %d unique keyword orders ===\n", w, n_keys);
    
    float global_best_rv7 = 0.0f;
    int best_i = -1, best_j = -1;
    
    #pragma omp parallel
    {
        float local_best = 0.0f;
        int local_bi = -1, local_bj = -1;
        int map1[N], map2[N];
        char undone[N + 1];
        undone[N] = '\0';
        
        #pragma omp for schedule(dynamic)
        for (int i = 0; i < n_keys; i++) {
            get_col_map(w, keys[i].order, map1);
            for (int j = 0; j < n_keys; j++) {
                get_col_map(w, keys[j].order, map2);
                for (int k = 0; k < N; k++) {
                    undone[k] = PK9_CT[map1[map2[k]]];
                }
                float rv7 = col_ioc(undone, 7);
                if (rv7 > 0.068f) {
                    #pragma omp critical
                    printf("  Period 7 HIT! rv7=%.5f | kw1=%s kw2=%s\n", rv7, keys[i].word, keys[j].word);
                }
                if (rv7 > local_best) {
                    local_best = rv7;
                    local_bi = i;
                    local_bj = j;
                }
            }
        }
        
        #pragma omp critical
        {
            if (local_best > global_best_rv7) {
                global_best_rv7 = local_best;
                best_i = local_bi;
                best_j = local_bj;
            }
        }
    }
    
    printf("Best Period-7 Reveal for width %d: %.5f\n", w, global_best_rv7);
    if (best_i >= 0 && best_j >= 0) {
        printf("  KW1: %s | KW2: %s\n", keys[best_i].word, keys[best_j].word);
    }
}

int main() {
    run_width(8);
    run_width(9);
    run_width(12);
    return 0;
}
