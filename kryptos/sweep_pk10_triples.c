#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>

#define N 504

const char *KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
const char *PK10_CT = "UBINFYJSFQXQVRLJJAJDGBXIWKDMAREZTGSHQWRXCHEPCLYSDNGYRRBTCVOZJYVLYWREJTCDOYVEYCJJVZKRMKTRPGVHRWMJSRCSHXZMJEVQKJYJJAYZKDFQBGRSWXATJMEXKFXAXKSIZXOERFESNVCGCNRHEOBCNCBUPXTJJRCIMDMRUVZWRDRRFXAPGPIGSPLILFIZSTDZYOVQGGDFUFZPUOJPJVWREUVRQIYPCEHGYUZUKWTFXELUNOKBANZFTFRMXZSXXQSBGPCWGXPFSCANSVUYLMTZIRCCCJJPBQAEPWVCDIMLOPOXQEGJKVQIVHEFAPQMVCYSQAFKCTYTPAOOJZCWIPGDPAFTINBFFHVXYEQXCEIDJJOUABBAHSWKHGMLJBXDSQEFBBDLTLJPLZPIPPTRGDRZIZPUPYJODOCSOYCZZWTKYWMBQTFMFEQZWVPQYLJTMEYKYBNOPEPUMHCFJSLFWOISWLKFFABTYFQDTEQBDELIEOZQ";

static const float eng_freq[26] = {
    0.08167, 0.01492, 0.02782, 0.04253, 0.12702, 0.02228, 0.02015,
    0.06094, 0.06966, 0.00153, 0.00772, 0.04025, 0.02406, 0.06749,
    0.07507, 0.01929, 0.00095, 0.05987, 0.06327, 0.09056, 0.02758,
    0.00978, 0.02360, 0.00150, 0.01974, 0.00074
};

static int c_idx[N];
static int alpha_to_std[26];
static int char_to_k[256];

void init_tables() {
    for (int i = 0; i < 256; i++) char_to_k[i] = -1;
    for (int i = 0; i < 26; i++) {
        alpha_to_std[i] = KRYPTOS[i] - 'A';
        char_to_k[(unsigned char)KRYPTOS[i]] = i;
    }
    for (int i = 0; i < N; i++) {
        c_idx[i] = char_to_k[(unsigned char)PK10_CT[i]];
    }
}

typedef struct {
    char word[16];
    int rot;
    int k_idx[16];
} WordItem;

int load_items(const char *path, int len, WordItem *items, int max_items) {
    FILE *f = fopen(path, "r");
    if (!f) return 0;
    char line[64];
    int count = 0;
    while (fgets(line, sizeof(line), f) && count < max_items) {
        char w[32];
        int r;
        if (sscanf(line, "%s %d", w, &r) == 2 && strlen(w) == len) {
            strcpy(items[count].word, w);
            items[count].rot = r;
            for (int i = 0; i < len; i++) {
                items[count].k_idx[i] = char_to_k[(unsigned char)w[i]];
            }
            count++;
        }
    }
    fclose(f);
    return count;
}

void run_sweep(const char *prefix, WordItem *w7, int n7, WordItem *w8, int n8, WordItem *w9, int n9) {
    long long total_triples = (long long)n7 * n8 * n9;
    printf("\n=== Running Sweep [%s]: %d w7 x %d w8 x %d w9 = %lld triples ===\n",
           prefix, n7, n8, n9, total_triples);

    float global_best_dot = 0.0f;
    char best_w7[16] = "", best_w8[16] = "", best_w9[16] = "";

    double t0 = omp_get_wtime();

    #pragma omp parallel
    {
        float local_best_dot = 0.0f;
        char local_w7[16] = "", local_w8[16] = "", local_w9[16] = "";

        #pragma omp for schedule(dynamic, 100)
        for (long long idx = 0; idx < total_triples; idx++) {
            int i7 = idx / ((long long)n8 * n9);
            long long rem = idx % ((long long)n8 * n9);
            int i8 = rem / n9;
            int i9 = rem % n9;

            const WordItem *pw7 = &w7[i7];
            const WordItem *pw8 = &w8[i8];
            const WordItem *pw9 = &w9[i9];

            int counts[26] = {0};
            for (int i = 0; i < N; i++) {
                int k7 = pw7->k_idx[(i + pw7->rot) % 7];
                int k8 = pw8->k_idx[(i + pw8->rot) % 8];
                int k9 = pw9->k_idx[(i + pw9->rot) % 9];
                int k = (k7 + k8 + k9) % 26;
                int p = (c_idx[i] - k + 26) % 26;
                counts[alpha_to_std[p]]++;
            }

            float dot = 0.0f;
            for (int c = 0; c < 26; c++) {
                dot += counts[c] * eng_freq[c];
            }

            if (dot > 27.5f) {
                #pragma omp critical
                {
                    printf(">>> CANDIDATE TRIPLE! Dot = %.4f | (%s, %s, %s)\n",
                           dot, pw7->word, pw8->word, pw9->word);
                    fflush(stdout);
                }
            }

            if (dot > local_best_dot) {
                local_best_dot = dot;
                strcpy(local_w7, pw7->word);
                strcpy(local_w8, pw8->word);
                strcpy(local_w9, pw9->word);
            }
        }

        #pragma omp critical
        {
            if (local_best_dot > global_best_dot) {
                global_best_dot = local_best_dot;
                strcpy(best_w7, local_w7);
                strcpy(best_w8, local_w8);
                strcpy(best_w9, local_w9);
            }
        }
    }

    double elapsed = omp_get_wtime() - t0;
    printf("Completed [%s] in %.2f s (%.1f million triples/sec)\n",
           prefix, elapsed, total_triples / (elapsed * 1e6));
    printf("Global Best Dot = %.4f | Words: (%s, %s, %s)\n",
           global_best_dot, best_w7, best_w8, best_w9);
}

static WordItem items7[2000], items8[5000], items9[2000];

int main() {
    init_tables();

    // 1. Sweep g000 (338k triples)
    int n7 = load_items("g000_w7.txt", 7, items7, 2000);
    int n8 = load_items("g000_w8.txt", 8, items8, 5000);
    int n9 = load_items("g000_w9.txt", 9, items9, 2000);
    run_sweep("g000", items7, n7, items8, n8, items9, n9);

    // 2. Sweep g101 (8.09M triples)
    n7 = load_items("g101_w7.txt", 7, items7, 2000);
    n8 = load_items("g101_w8.txt", 8, items8, 5000);
    n9 = load_items("g101_w9.txt", 9, items9, 2000);
    run_sweep("g101", items7, n7, items8, n8, items9, n9);

    return 0;
}
