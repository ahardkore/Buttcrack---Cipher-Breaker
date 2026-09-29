#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

#define N 144

static const char *KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
static const char *PK9_CT = "KSYAWFEYYOISZGEUFBLYATAIBYFAQBQGZGSMMJHJQNHSVHAWFLHXLSKALEHHSUUFBVBXJXMMHIRHUMQQLYAGUJYIEJXDMALIFUTAIHZRPIFLSEYYSJMQYYLHDUHUCTSOISUXGVDWKEWUDXUQXZGENUIJK";

static int ct_kr[N];
static int ct_std[N];
static int k_to_std[26];
static int std_to_k[26];

// Standard English monogram frequencies (scaled to sum to 1000)
static const float eng_freq[26] = {
    82, 15, 28, 43, 127, 22, 20, 61, 70, 2, 8, 40, 24, 67, 75, 19, 1, 60, 63, 91, 28, 10, 24, 2, 20, 1
};

void init() {
    for (int i=0; i<26; i++) {
        k_to_std[i] = KRYPTOS[i] - 'A';
        std_to_k[KRYPTOS[i] - 'A'] = i;
    }
    for (int i=0; i<N; i++) {
        ct_std[i] = PK9_CT[i] - 'A';
        ct_kr[i] = std_to_k[PK9_CT[i] - 'A'];
    }
}

float eval_ioc(const int *txt_std) {
    int cnt[26] = {0};
    for (int i=0; i<N; i++) cnt[txt_std[i]]++;
    int num = 0;
    for (int i=0; i<26; i++) num += cnt[i] * (cnt[i] - 1);
    return (float)num / (float)(N * (N - 1));
}

float eval_chi2(const int *txt_std) {
    int cnt[26] = {0};
    for (int i=0; i<N; i++) cnt[txt_std[i]]++;
    float chi2 = 0.0f;
    for (int i=0; i<26; i++) {
        float expected = (float)N * (eng_freq[i] / 1000.0f);
        float diff = (float)cnt[i] - expected;
        chi2 += (diff * diff) / expected;
    }
    return chi2;
}

int main() {
    init();
    FILE *f = fopen("words_7.txt", "r");
    if (!f) { printf("Cannot open words_7.txt\n"); return 1; }
    
    char word[32];
    int count = 0;
    float best_chi2_kr = 99999.0f;
    float best_chi2_std = 99999.0f;
    char best_word_kr[32] = "";
    char best_word_std[32] = "";
    
    int txt_std[N];
    
    while (fscanf(f, "%31s", word) == 1) {
        if (strlen(word) != 7) continue;
        count++;
        
        // Mode 1: Quagmire III (KRYPTOS alphabet, Vigenere)
        int key_kr[7];
        for (int j=0; j<7; j++) key_kr[j] = std_to_k[word[j] - 'A'];
        for (int i=0; i<N; i++) {
            int p_kr = (ct_kr[i] - key_kr[i % 7] + 26) % 26;
            txt_std[i] = k_to_std[p_kr];
        }
        float ioc_kr = eval_ioc(txt_std);
        if (ioc_kr > 0.055f) {
            float chi2 = eval_chi2(txt_std);
            if (chi2 < best_chi2_kr) {
                best_chi2_kr = chi2;
                strcpy(best_word_kr, word);
                printf("[QIII] Hit! Word: %-10s | IoC: %.5f | Chi2: %.2f\n", word, ioc_kr, chi2);
            }
        }
        
        // Mode 2: Standard Alphabet Vigenere
        int key_std[7];
        for (int j=0; j<7; j++) key_std[j] = word[j] - 'A';
        for (int i=0; i<N; i++) {
            txt_std[i] = (ct_std[i] - key_std[i % 7] + 26) % 26;
        }
        float ioc_std = eval_ioc(txt_std);
        if (ioc_std > 0.055f) {
            float chi2 = eval_chi2(txt_std);
            if (chi2 < best_chi2_std) {
                best_chi2_std = chi2;
                strcpy(best_word_std, word);
                printf("[Std Vig] Hit! Word: %-10s | IoC: %.5f | Chi2: %.2f\n", word, ioc_std, chi2);
            }
        }
    }
    fclose(f);
    printf("Tested %d 7-letter words.\n", count);
    printf("Best QIII: %s (Chi2: %.2f)\n", best_word_kr, best_chi2_kr);
    printf("Best Std Vig: %s (Chi2: %.2f)\n", best_word_std, best_chi2_std);
    return 0;
}
