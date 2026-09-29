#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <omp.h>

#define N 144

static const char *PK9_CT = "KSYAWFEYYOISZGEUFBLYATAIBYFAQBQGZGSMMJHJQNHSVHAWFLHXLSKALEHHSUUFBVBXJXMMHIRHUMQQLYAGUJYIEJXDMALIFUTAIHZRPIFLSEYYSJMQYYLHDUHUCTSOISUXGVDWKEWUDXUQXZGENUIJK";

// Complete columnar inverse permutation:
// Encrypt: write rows (len/w x w), read columns in order o
// Decrypt: fill columns in order o, read rows
void get_col_map(int w, const int *o, int *map) {
    int h = N / w;
    // Decrypt writes into grid: col o[c] receives block c (size h)
    // grid[r][col] has index r * w + col
    // plaintext position r * w + col comes from ciphertext position c * h + r
    // So pt[r * w + o[c]] = ct[c * h + r]
    // That means pt_to_ct map: map[r * w + o[c]] = c * h + r
    for (int c = 0; c < w; c++) {
        int col = o[c];
        for (int r = 0; r < h; r++) {
            map[r * w + col] = c * h + r;
        }
    }
}

// Compute slice IoC at period p
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

float max_col_ioc(const char *txt, int *best_p) {
    float best = 0.0f;
    int bp = 0;
    for (int p = 5; p <= 15; p++) {
        float v = col_ioc(txt, p);
        if (v > best) {
            best = v;
            bp = p;
        }
    }
    *best_p = bp;
    return best;
}

// Structure for keyword orders
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
        // Check if alpha
        int ok = 1;
        for (int i = 0; i < w; i++) {
            if (word[i] < 'A' || word[i] > 'Z') { ok = 0; break; }
        }
        if (!ok) continue;
        
        // compute argsort order
        int ord[32];
        for (int i = 0; i < w; i++) ord[i] = i;
        for (int i = 0; i < w - 1; i++) {
            for (int j = i + 1; j < w; j++) {
                if (word[ord[i]] > word[ord[j]]) {
                    int tmp = ord[i]; ord[i] = ord[j]; ord[j] = tmp;
                }
            }
        }
        
        // Check if unique order
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

int main(int argc, char **argv) {
    int w = (argc > 1) ? atoi(argv[1]) : 9;
    char fn[64];
    sprintf(fn, "theophilus_w%d.txt", w);
    
    KeyOrder keys[500];
    int n_keys = load_orders(fn, w, keys, 500);
    printf("Loaded %d unique orders for width %d from %s\n", n_keys, w, fn);
    
    // Also try curated/standard words
    sprintf(fn, "words_%d.txt", w);
    int n_more = load_orders(fn, w, keys + n_keys, 500 - n_keys);
    printf("Added %d orders from %s (total %d)\n", n_more, fn, n_keys + n_more);
    n_keys += n_more;
    
    float global_best_rv = 0.0f;
    int best_p = 0;
    int best_i = -1, best_j = -1;
    
    #pragma omp parallel
    {
        float local_best = 0.0f;
        int local_bp = 0, local_bi = -1, local_bj = -1;
        int map1[N], map2[N], comp_map[N];
        char undone[N + 1];
        undone[N] = '\0';
        
        #pragma omp for schedule(dynamic)
        for (int i = 0; i < n_keys; i++) {
            get_col_map(w, keys[i].order, map1);
            for (int j = 0; j < n_keys; j++) {
                get_col_map(w, keys[j].order, map2);
                // Composite map: undo outer map1 then inner map2
                // pt[k] = ct[map1[map2[k]]]
                for (int k = 0; k < N; k++) {
                    undone[k] = PK9_CT[map1[map2[k]]];
                }
                int bp = 0;
                float rv = max_col_ioc(undone, &bp);
                if (rv > 0.065f) {
                    #pragma omp critical
                    printf("HIT! rv=%.5f p=%d | kw1=%s kw2=%s\n", rv, bp, keys[i].word, keys[j].word);
                }
                if (rv > local_best) {
                    local_best = rv;
                    local_bp = bp;
                    local_bi = i;
                    local_bj = j;
                }
            }
        }
        
        #pragma omp critical
        {
            if (local_best > global_best_rv) {
                global_best_rv = local_best;
                best_p = local_bp;
                best_i = local_bi;
                best_j = local_bj;
            }
        }
    }
    
    printf("\n=== GLOBAL BEST for width %d ===\n", w);
    printf("Best Reveal: %.5f at period %d\n", global_best_rv, best_p);
    if (best_i >= 0 && best_j >= 0) {
        printf("KW1: %s | KW2: %s\n", keys[best_i].word, keys[best_j].word);
    }
    return 0;
}
