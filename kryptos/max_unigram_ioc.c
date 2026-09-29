#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define N 144

static const char *KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
static const char *PK9_CT = "KSYAWFEYYOISZGEUFBLYATAIBYFAQBQGZGSMMJHJQNHSVHAWFLHXLSKALEHHSUUFBVBXJXMMHIRHUMQQLYAGUJYIEJXDMALIFUTAIHZRPIFLSEYYSJMQYYLHDUHUCTSOISUXGVDWKEWUDXUQXZGENUIJK";
static int c_vals[N];

void init() {
    int hpos[256];
    for (int i=0; i<26; i++) hpos[(unsigned char)KRYPTOS[i]] = i;
    for (int i=0; i<N; i++) c_vals[i] = hpos[(unsigned char)PK9_CT[i]];
}

float eval_ioc(int p, const int *key) {
    int counts[26] = {0};
    for (int i=0; i<N; i++) {
        int v = (c_vals[i] - key[i % p] + 26) % 26;
        counts[v]++;
    }
    int sum = 0;
    for (int k=0; k<26; k++) sum += counts[k] * (counts[k] - 1);
    return (float)sum / (float)(N * (N - 1));
}

void solve_period(int p) {
    int col_counts[32][26] = {0};
    for (int j=0; j<p; j++) {
        for (int i=j; i<N; i+=p) {
            col_counts[j][c_vals[i]]++;
        }
    }
    
    float best_ioc = 0.0f;
    int best_key[32] = {0};
    
    for (int restart=0; restart<500; restart++) {
        int key[32];
        for (int j=0; j<p; j++) key[j] = rand() % 26;
        key[0] = 0;
        
        int improved = 1;
        while (improved) {
            improved = 0;
            for (int col=1; col<p; col++) {
                int total[26] = {0};
                for (int j=0; j<p; j++) {
                    if (j != col) {
                        for (int k=0; k<26; k++) {
                            total[(k - key[j] + 26) % 26] += col_counts[j][k];
                        }
                    }
                }
                int best_s = key[col];
                int best_ss = 0;
                for (int s=0; s<26; s++) {
                    int ss = 0;
                    for (int k=0; k<26; k++) {
                        int cnt = total[(k - s + 26) % 26] + col_counts[col][k];
                        // wait, counts are in shifted domain:
                    }
                }
            }
        }
    }
}

int main() {
    init();
    // Test known periods and measure exact unigram IoC of optimal key:
    int periods[] = {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 14, 16, 18, 20, 24, 28};
    int n_p = sizeof(periods)/sizeof(periods[0]);
    
    for (int idx=0; idx<n_p; idx++) {
        int p = periods[idx];
        float best_ioc = 0.0f;
        int best_key[32] = {0};
        
        for (int restart=0; restart<1000; restart++) {
            int key[32];
            for (int j=0; j<p; j++) key[j] = rand() % 26;
            key[0] = 0;
            
            int improved = 1;
            while (improved) {
                improved = 0;
                for (int col=1; col<p; col++) {
                    int old_s = key[col];
                    float cur_best = eval_ioc(p, key);
                    int b_s = old_s;
                    for (int s=0; s<26; s++) {
                        if (s == old_s) continue;
                        key[col] = s;
                        float sc = eval_ioc(p, key);
                        if (sc > cur_best) {
                            cur_best = sc;
                            b_s = s;
                        }
                    }
                    key[col] = b_s;
                    if (b_s != old_s) improved = 1;
                }
            }
            float final_sc = eval_ioc(p, key);
            if (final_sc > best_ioc) {
                best_ioc = final_sc;
                memcpy(best_key, key, p * sizeof(int));
            }
        }
        printf("Period %2d: Max Unigram IoC = %.5f | Key: [", p, best_ioc);
        for (int j=0; j<p; j++) printf("%d%s", best_key[j], j == p-1 ? "" : ", ");
        printf("]\n");
    }
    return 0;
}
