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
        chi2 += (diff * diff) / (expected + 0.001f);
    }
    return chi2;
}

void test_file(const char *fn) {
    FILE *f = fopen(fn, "r");
    if (!f) return;
    char word[64];
    int txt_std[N];
    
    float best_chi2 = 1e9f;
    char best_word[64] = "";
    float best_ioc = 0.0f;
    int tested = 0;
    
    while (fscanf(f, "%63s", word) == 1) {
        int len = strlen(word);
        if (len < 3 || len > 24) continue;
        int ok = 1;
        for (int i=0; i<len; i++) {
            if (word[i] >= 'a' && word[i] <= 'z') word[i] -= 32;
            if (word[i] < 'A' || word[i] > 'Z') { ok = 0; break; }
        }
        if (!ok) continue;
        tested++;
        
        // Mode 1: QIII (KRYPTOS alphabet)
        int key_kr[64];
        for (int j=0; j<len; j++) key_kr[j] = std_to_k[word[j] - 'A'];
        for (int i=0; i<N; i++) {
            int p_kr = (ct_kr[i] - key_kr[i % len] + 26) % 26;
            txt_std[i] = k_to_std[p_kr];
        }
        float chi2 = eval_chi2(txt_std);
        float ioc = eval_ioc(txt_std);
        if (chi2 < best_chi2) {
            best_chi2 = chi2;
            best_ioc = ioc;
            strcpy(best_word, word);
            if (chi2 < 120.0f) {
                printf("[QIII HIT] File: %s | Word: %-15s (len %d) | Chi2: %.2f | IoC: %.5f\n",
                       fn, word, len, chi2, ioc);
            }
        }
        
        // Mode 2: Standard Vig
        int key_std[64];
        for (int j=0; j<len; j++) key_std[j] = word[j] - 'A';
        for (int i=0; i<N; i++) {
            txt_std[i] = (ct_std[i] - key_std[i % len] + 26) % 26;
        }
        chi2 = eval_chi2(txt_std);
        ioc = eval_ioc(txt_std);
        if (chi2 < 120.0f) {
            printf("[Std Vig HIT] File: %s | Word: %-15s (len %d) | Chi2: %.2f | IoC: %.5f\n",
                   fn, word, len, chi2, ioc);
        }
    }
    fclose(f);
    printf("File: %-25s | Tested: %6d | Best Word: %-12s | Chi2: %.2f | IoC: %.5f\n",
           fn, tested, best_word, best_chi2, best_ioc);
}

int main() {
    init();
    printf("Testing candidate substitution keywords on PK9...\n");
    test_file("theophilus_w4.txt");
    test_file("theophilus_w5.txt");
    test_file("theophilus_w6.txt");
    test_file("theophilus_w7.txt");
    test_file("theophilus_w8.txt");
    test_file("theophilus_w9.txt");
    test_file("theophilus_w12.txt");
    test_file("theophilus_w12_all.txt");
    test_file("words_4.txt");
    test_file("words_5.txt");
    test_file("words_6.txt");
    test_file("words_8.txt");
    test_file("words_9.txt");
    test_file("words_12.txt");
    test_file("words_14.txt");
    return 0;
}
