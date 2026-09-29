#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <omp.h>

#define N 504

static const char *PK10_CT = "UBINFYJSFQXQVRLJJAJDGBXIWKDMAREZTGSHQWRXCHEPCLYSDNGYRRBTCVOZJYVLYWREJTCDOYVEYCJJVZKRMKTRPGVHRWMJSRCSHXZMJEVQKJYJJAYZKDFQBGRSWXATJMEXKFXAXKSIZXOERFESNVCGCNRHEOBCNCBUPXTJJRCIMDMRUVZWRDRRFXAPGPIGSPLILFIZSTDZYOVQGGDFUFZPUOJPJVWREUVRQIYPCEHGYUZUKWTFXELUNOKBANZFTFRMXZSXXQSBGPCWGXPFSCANSVUYLMTZIRCCCJJPBQAEPWVCDIMLOPOXQEGJKVQIVHEFAPQMVCYSQAFKCTYTPAOOJZCWIPGDPAFTINBFFHVXYEQXCEIDJJOUABBAHSWKHGMLJBXDSQEFBBDLTLJPLZPIPPTRGDRZIZPUPYJODOCSOYCZZWTKYWMBQTFMFEQZWVPQYLJTMEYKYBNOPEPUMHCFJSLFWOISWLKFFABTYFQDTEQBDELIEOZQ";

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

float max_col_ioc(const char *txt, int *best_p) {
    float best = 0.0f;
    int bp = 0;
    for (int p = 5; p <= 30; p++) {
        float v = col_ioc(txt, p);
        if (v > best) {
            best = v;
            bp = p;
        }
    }
    *best_p = bp;
    return best;
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

void test_width(int w) {
    char fn[64];
    KeyOrder keys[2000];
    sprintf(fn, "theophilus_w%d.txt", w);
    int n_keys = load_orders(fn, w, keys, 2000);
    sprintf(fn, "curated_w%d.txt", w);
    int n2 = load_orders(fn, w, keys + n_keys, 2000 - n_keys);
    n_keys += n2;
    sprintf(fn, "words_%d.txt", w);
    int n3 = load_orders(fn, w, keys + n_keys, 2000 - n_keys);
    n_keys += n3;
    printf("Width %2d: %d unique keyword orders loaded\n", w, n_keys);
    
    float global_best_rv = 0.0f;
    int best_p = 0;
    int best_i = -1;
    
    #pragma omp parallel
    {
        float local_best = 0.0f;
        int local_bp = 0, local_bi = -1;
        int map[N];
        char undone[N + 1];
        undone[N] = '\0';
        
        #pragma omp for schedule(dynamic)
        for (int i = 0; i < n_keys; i++) {
            get_col_map(w, keys[i].order, map);
            for (int k = 0; k < N; k++) {
                undone[k] = PK10_CT[map[k]];
            }
            int bp = 0;
            float rv = max_col_ioc(undone, &bp);
            if (rv > local_best) {
                local_best = rv;
                local_bp = bp;
                local_bi = i;
            }
        }
        #pragma omp critical
        {
            if (local_best > global_best_rv) {
                global_best_rv = local_best;
                best_p = local_bp;
                best_i = local_bi;
            }
        }
    }
    
    if (best_i >= 0) {
        printf("  -> Best Reveal: %.5f at period %d with keyword: %s\n", global_best_rv, best_p, keys[best_i].word);
    }
}

int main() {
    int widths[] = {7, 8, 9, 12, 14, 18, 21, 24};
    for (int i = 0; i < 8; i++) {
        test_width(widths[i]);
    }
    return 0;
}
