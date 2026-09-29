#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

#define N 144

static const char *KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
static const char *undone = "QGKVHPZGUKSYHEGBYFHJGQNHSVHAWFLHXAQBUQGZGSMLSEYYSJMQYYLHDUHUCTSOISUXGVDWKEWUDXUQXZGENUIJKLSKALEHHSUUFBVBXJXMMHIRHUMQQLYAGUJYIEJXDMALIFUTAIHZRPIF";

static int u_kr[N];
static int u_std[N];
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
        u_std[i] = undone[i] - 'A';
        u_kr[i] = std_to_k[undone[i] - 'A'];
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
    printf("Evaluating optimal shift alignments on undone...\n");
    
    // For each column 0..6, find shift that maximizes correlation with English monograms
    // Under Quagmire III: p_kr = (u_kr - shift + 26) % 26
    // txt_std = k_to_std[p_kr]
    
    int best_shifts_kr[7];
    for (int c=0; c<7; c++) {
        float best_col_chi2 = 1e9f;
        int best_s = 0;
        int col_len = 0;
        for (int i=c; i<N; i+=7) col_len++;
        
        for (int s=0; s<26; s++) {
            int cnt[26] = {0};
            for (int i=c; i<N; i+=7) {
                int p_kr = (u_kr[i] - s + 26) % 26;
                cnt[k_to_std[p_kr]]++;
            }
            float chi2 = 0.0f;
            for (int k=0; k<26; k++) {
                float expected = (float)col_len * (eng_freq[k] / 1000.0f);
                float diff = (float)cnt[k] - expected;
                chi2 += (diff * diff) / (expected + 0.01f);
            }
            if (chi2 < best_col_chi2) {
                best_col_chi2 = chi2;
                best_s = s;
            }
        }
        best_shifts_kr[c] = best_s;
    }
    
    printf("Best QIII Shifts per column (0..6): [");
    for (int c=0; c<7; c++) printf("%d%s", best_shifts_kr[c], c==6?"":", ");
    printf("]\n");
    
    int txt_std[N];
    for (int i=0; i<N; i++) {
        int p_kr = (u_kr[i] - best_shifts_kr[i % 7] + 26) % 26;
        txt_std[i] = k_to_std[p_kr];
    }
    float ioc = eval_ioc(txt_std);
    float chi2 = eval_chi2(txt_std);
    printf("Combined IoC: %.5f | Total Chi2: %.2f\n", ioc, chi2);
    char out_txt[N+1];
    for (int i=0; i<N; i++) out_txt[i] = txt_std[i] + 'A';
    out_txt[N] = '\0';
    printf("Resulting Text Y:\n%s\n", out_txt);
    
    return 0;
}
