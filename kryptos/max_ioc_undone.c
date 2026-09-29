#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define N 144

static const char *KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
static const char *undone = "QGKVHPZGUKSYHEGBYFHJGQNHSVHAWFLHXAQBUQGZGSMLSEYYSJMQYYLHDUHUCTSOISUXGVDWKEWUDXUQXZGENUIJKLSKALEHHSUUFBVBXJXMMHIRHUMQQLYAGUJYIEJXDMALIFUTAIHZRPIF";

static int u_kr[N];
static int k_to_std[26];
static int std_to_k[26];

void init() {
    for (int i=0; i<26; i++) {
        k_to_std[i] = KRYPTOS[i] - 'A';
        std_to_k[KRYPTOS[i] - 'A'] = i;
    }
    for (int i=0; i<N; i++) {
        u_kr[i] = std_to_k[undone[i] - 'A'];
    }
}

float eval_ioc(const int *key) {
    int counts[26] = {0};
    for (int i=0; i<N; i++) {
        int p_kr = (u_kr[i] - key[i % 7] + 26) % 26;
        counts[k_to_std[p_kr]]++;
    }
    int sum = 0;
    for (int k=0; k<26; k++) sum += counts[k] * (counts[k] - 1);
    return (float)sum / (float)(N * (N - 1));
}

int main() {
    init();
    
    float best_ioc = 0.0f;
    int best_key[7] = {0};
    
    for (int restart=0; restart<1000; restart++) {
        int key[7];
        for (int j=0; j<7; j++) key[j] = rand() % 26;
        key[0] = 0;
        
        int improved = 1;
        while (improved) {
            improved = 0;
            for (int col=1; col<7; col++) {
                int old_s = key[col];
                float cur_best = eval_ioc(key);
                int b_s = old_s;
                for (int s=0; s<26; s++) {
                    if (s == old_s) continue;
                    key[col] = s;
                    float sc = eval_ioc(key);
                    if (sc > cur_best) {
                        cur_best = sc;
                        b_s = s;
                    }
                }
                key[col] = b_s;
                if (b_s != old_s) improved = 1;
            }
        }
        float final_sc = eval_ioc(key);
        if (final_sc > best_ioc) {
            best_ioc = final_sc;
            memcpy(best_key, key, 7 * sizeof(int));
        }
    }
    
    printf("Period 7 Max IoC on undone: %.5f | Key: [", best_ioc);
    for (int j=0; j<7; j++) printf("%d%s", best_key[j], j==6?"":", ");
    printf("]\n");
    
    char out[N+1];
    for (int i=0; i<N; i++) {
        int p_kr = (u_kr[i] - best_key[i % 7] + 26) % 26;
        out[i] = k_to_std[p_kr] + 'A';
    }
    out[N] = '\0';
    printf("Text Y:\n%s\n", out);
    
    return 0;
}
