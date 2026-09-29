#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>

#define N 153

static float quad[26][26][26][26];

void load_quads() {
    for (int a=0; a<26; a++)
        for (int b=0; b<26; b++)
            for (int c=0; c<26; c++)
                for (int d=0; d<26; d++)
                    quad[a][b][c][d] = -9.5f;
    FILE *f = fopen("english_quadgrams.txt", "r");
    if (!f) return;
    char q[16]; float cnt;
    double total = 0;
    while (fscanf(f, "%s %f", q, &cnt) == 2) {
        if (strlen(q) == 4) total += cnt;
    }
    rewind(f);
    while (fscanf(f, "%s %f", q, &cnt) == 2) {
        if (strlen(q) == 4) {
            int a = q[0]-'A', b = q[1]-'A', c = q[2]-'A', d = q[3]-'A';
            if (a>=0 && a<26 && b>=0 && b<26 && c>=0 && c<26 && d>=0 && d<26) {
                quad[a][b][c][d] = (float)log10((cnt + 0.01) / total);
            }
        }
    }
    fclose(f);
}

static const char *KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
static const char *PK8_CT = "COPVEJJVSVURTVIPYOTPLHGBTMAUCCPESIWIGZBWSJPKTRPUEKQFIFCLHMXTHIMHWOYIGURBOMPARCVXVKBDDVBVHDRHGCVNWWVLBMYWMWHICFIXZWBVZYCQGNOGJGUMLNPUTHQCXNWPQZOIRJZGSWVPY";

static int ct_kr[N];
static int k_to_std[26];
static int std_to_k[26];

void init() {
    for (int i=0; i<26; i++) {
        k_to_std[i] = KRYPTOS[i] - 'A';
        std_to_k[KRYPTOS[i] - 'A'] = i;
    }
    for (int i=0; i<N; i++) {
        ct_kr[i] = std_to_k[PK8_CT[i] - 'A'];
    }
}

int load_words_len(const char *fn, int target_len, char out[][16], int max_words) {
    FILE *f = fopen(fn, "r");
    if (!f) return 0;
    char buf[64];
    int count = 0;
    while (fscanf(f, "%63s", buf) == 1 && count < max_words) {
        char clean[16]; int clen = 0;
        for (int i=0; buf[i]; i++) {
            char c = buf[i];
            if (c >= 'a' && c <= 'z') c -= 32;
            if (c >= 'A' && c <= 'Z') clean[clen++] = c;
        }
        clean[clen] = '\0';
        if (clen == target_len) {
            int exists = 0;
            for (int j=0; j<count; j++) {
                if (strcmp(out[j], clean) == 0) { exists = 1; break; }
            }
            if (!exists) {
                strcpy(out[count++], clean);
            }
        }
    }
    fclose(f);
    return count;
}

float score_text(const char *t) {
    float sc = 0.0f;
    for (int i=0; i<N-3; i++) {
        sc += quad[t[i]-'A'][t[i+1]-'A'][t[i+2]-'A'][t[i+3]-'A'];
    }
    return sc / (N - 3);
}

int main() {
    load_quads();
    init();
    
    char w5[2000][16], w6[2000][16];
    int n5 = load_words_len("theophilus_hendrie.txt", 5, w5, 1500);
    int n6 = load_words_len("theophilus_hendrie.txt", 6, w6, 1500);
    
    // Add curated words
    const char *extra5[] = {"FORGE", "ANVIL", "FLAME", "SMOKE", "STEEL", "BRASS", "ALLOY", "METAL", "TONGS", "HEATH"};
    for (int i=0; i<10; i++) strcpy(w5[n5++], extra5[i]);
    const char *extra6[] = {"HEARTH", "COPPER", "SILVER", "BELLOW", "HAMMER", "PORTAL", "NEEDLE", "SOLDER", "MOLTEN"};
    for (int i=0; i<9; i++) strcpy(w6[n6++], extra6[i]);
    
    printf("Loaded w5=%d, w6=%d. Testing %lld pairs on PK8 with fixed (Q4, Q7)...\n",
           n5, n6, (long long)n5 * n6);
    
    int s5[2000][5], s6[2000][6];
    for (int i=0; i<n5; i++) for (int k=0; k<5; k++) s5[i][k] = std_to_k[w5[i][k] - 'A'];
    for (int i=0; i<n6; i++) for (int k=0; k<6; k++) s6[i][k] = std_to_k[w6[i][k] - 'A'];
    
    // Fixed Q4 and Q7 from PK9
    const int q4[4] = {0, 18, 13, 9};
    const int q7[7] = {5, 5, 8, 7, 16, 10, 22};
    
    int base28[28];
    for (int k=0; k<28; k++) {
        base28[k] = (q4[k % 4] + q7[k % 7]) % 26;
    }
    
    float global_best_sc = -999.0f;
    char global_best_pt[N+1];
    char best_w5[16], best_w6[16];
    
    double t0 = omp_get_wtime();
    
    #pragma omp parallel
    {
        float local_best = -999.0f;
        char local_pt[N+1];
        char l_w5[16], l_w6[16];
        char pt[N+1];
        
        #pragma omp for schedule(dynamic, 10)
        for (int i5 = 0; i5 < n5; i5++) {
            for (int i6 = 0; i6 < n6; i6++) {
                // Check all 26 constant shift offsets c (0..25)
                for (int c = 0; c < 26; c++) {
                    for (int k = 0; k < N; k++) {
                        int sh = (base28[k % 28] + s5[i5][k % 5] + s6[i6][k % 6] + c) % 26;
                        int p_kr = (ct_kr[k] - sh + 26) % 26;
                        pt[k] = k_to_std[p_kr] + 'A';
                    }
                    pt[N] = '\0';
                    float sc = score_text(pt);
                    if (sc > local_best) {
                        local_best = sc;
                        strcpy(local_pt, pt);
                        strcpy(l_w5, w5[i5]);
                        strcpy(l_w6, w6[i6]);
                        if (sc > -5.8f) {
                            #pragma omp critical
                            {
                                printf("\n*** CANDIDATE: %.4f ***\n", sc);
                                printf("Keys: Q5=%s, Q6=%s (c=%d)\n", w5[i5], w6[i6], c);
                                printf("PT: %s\n", pt);
                            }
                        }
                    }
                }
            }
        }
        
        #pragma omp critical
        {
            if (local_best > global_best_sc) {
                global_best_sc = local_best;
                strcpy(global_best_pt, local_pt);
                strcpy(best_w5, l_w5);
                strcpy(best_w6, l_w6);
            }
        }
    }
    
    double elapsed = omp_get_wtime() - t0;
    printf("\nCompleted in %.2f s\n", elapsed);
    printf("Global Best Quad: %.4f\n", global_best_sc);
    printf("Keys: Q5=%s, Q6=%s\n", best_w5, best_w6);
    printf("Plaintext:\n%s\n", global_best_pt);
    
    return 0;
}
