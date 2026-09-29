#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>

#define N 504
#define W 14
#define H (N / W) // 36

static const char *ALPH = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
static const char *PK10_CT = "UBINFYJSFQXQVRLJJAJDGBXIWKDMAREZTGSHQWRXCHEPCLYSDNGYRRBTCVOZJYVLYWREJTCDOYVEYCJJVZKRMKTRPGVHRWMJSRCSHXZMJEVQKJYJJAYZKDFQBGRSWXATJMEXKFXAXKSIZXOERFESNVCGCNRHEOBCNCBUPXTJJRCIMDMRUVZWRDRRFXAPGPIGSPLILFIZSTDZYOVQGGDFUFZPUOJPJVWREUVRQIYPCEHGYUZUKWTFXELUNOKBANZFTFRMXZSXXQSBGPCWGXPFSCANSVUYLMTZIRCCCJJPBQAEPWVCDIMLOPOXQEGJKVQIVHEFAPQMVCYSQAFKCTYTPAOOJZCWIPGDPAFTINBFFHVXYEQXCEIDJJOUABBAHSWKHGMLJBXDSQEFBBDLTLJPLZPIPPTRGDRZIZPUPYJODOCSOYCZZWTKYWMBQTFMFEQZWVPQYLJTMEYKYBNOPEPUMHCFJSLFWOISWLKFFABTYFQDTEQBDELIEOZQ";

void word_to_order(const char *word, int len, int *order) {
    int used[32] = {0};
    int pos = 0;
    for (char c = 'A'; c <= 'Z'; c++) {
        for (int i = 0; i < len; i++) {
            if (word[i] == c && !used[i]) {
                order[pos++] = i;
                used[i] = 1;
            }
        }
    }
}

float calc_ioc_p9(const int *C, const int *order) {
    int cols[W][H];
    int idx = 0;
    for (int c = 0; c < W; c++) {
        int phys_col = order[c];
        for (int r = 0; r < H; r++) {
            cols[phys_col][r] = C[idx++];
        }
    }

    int out[N];
    int out_idx = 0;
    for (int r = 0; r < H; r++) {
        for (int c = 0; c < W; c++) {
            out[out_idx++] = cols[c][r];
        }
    }

    int total_num = 0;
    int total_den = 0;
    int p = 9;
    for (int rem = 0; rem < p; rem++) {
        int counts[13] = {0};
        int n_sub = 0;
        for (int i = rem; i < N; i += p) {
            counts[out[i]]++;
            n_sub++;
        }
        if (n_sub > 1) {
            int num = 0;
            for (int k = 0; k < 13; k++) num += counts[k] * (counts[k] - 1);
            total_num += num;
            total_den += n_sub * (n_sub - 1);
        }
    }
    return (total_den > 0) ? (float)total_num / (float)total_den : 0.0f;
}

typedef struct {
    float ioc;
    char word[32];
} Res;

int cmp_res(const void *a, const void *b) {
    float diff = ((const Res*)b)->ioc - ((const Res*)a)->ioc;
    return (diff > 0) ? 1 : ((diff < 0) ? -1 : 0);
}

int main() {
    int k2i[256];
    for (int i=0; i<256; i++) k2i[i] = -1;
    for (int i=0; i<26; i++) k2i[(int)ALPH[i]] = i;

    int C[N];
    for (int i=0; i<N; i++) C[i] = k2i[(int)PK10_CT[i]] % 13;

    FILE *f = fopen("words_14.txt", "r");
    char line[64];
    Res results[15000];
    int n_words = 0;

    while (fgets(line, sizeof(line), f)) {
        int len = strlen(line);
        while (len > 0 && (line[len-1] == '\n' || line[len-1] == '\r')) line[--len] = 0;
        if (len == W) {
            for (int i=0; i<W; i++) if (line[i]>='a' && line[i]<='z') line[i] -= 32;
            int order[W];
            word_to_order(line, W, order);
            results[n_words].ioc = calc_ioc_p9(C, order);
            strcpy(results[n_words].word, line);
            n_words++;
        }
    }
    fclose(f);

    qsort(results, n_words, sizeof(Res), cmp_res);

    printf("Top 25 Words of Width 14 for Period 9 IoC (mod 13):\n");
    for (int i = 0; i < 25 && i < n_words; i++) {
        printf("[%2d] %s: IoC = %.5f\n", i+1, results[i].word, results[i].ioc);
    }

    return 0;
}
