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

// Load unique thematic words of given length
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
    
    char w4[1000][16], w5[1000][16], w6[1000][16], w7[1000][16];
    int n4 = load_words_len("theophilus_hendrie.txt", 4, w4, 1000);
    int n5 = load_words_len("theophilus_hendrie.txt", 5, w5, 1000);
    int n6 = load_words_len("theophilus_hendrie.txt", 6, w6, 1000);
    int n7 = load_words_len("theophilus_hendrie.txt", 7, w7, 1000);
    
    printf("Theophilus thematic words loaded: w4=%d, w5=%d, w6=%d, w7=%d\n", n4, n5, n6, n7);
    
    // Add curated Kryptos lore keywords
    const char *extra4[] = {"FIRE", "IRON", "GOLD", "LEAD", "COAL", "HEAT", "MELT", "TOOL", "CAST", "WOOD"};
    for (int i=0; i<10; i++) strcpy(w4[n4++], extra4[i]);
    const char *extra5[] = {"FORGE", "ANVIL", "FLAME", "SMOKE", "STEEL", "BRASS", "ALLOY", "METAL", "TONGS"};
    for (int i=0; i<9; i++) strcpy(w5[n5++], extra5[i]);
    const char *extra6[] = {"HEARTH", "COPPER", "SILVER", "BELLOW", "HAMMER", "PORTAL", "NEEDLE", "SOLDER"};
    for (int i=0; i<8; i++) strcpy(w6[n6++], extra6[i]);
    const char *extra7[] = {"KRYPTOS", "SANBORN", "WEBSTER", "FURNACE", "BELLOWS", "CRUCIBL", "NEEDLES"};
    for (int i=0; i<7; i++) strcpy(w7[n7++], extra7[i]);
    
    printf("Total words: w4=%d, w5=%d, w6=%d, w7=%d\n", n4, n5, n6, n7);
    printf("Total 4-tuples to evaluate: %lld\n", (long long)n4 * n5 * n6 * n7);
    
    // Convert words to KRYPTOS shift arrays
    int s4[1100][4], s5[1100][5], s6[1100][6], s7[1100][7];
    for (int i=0; i<n4; i++) for (int k=0; k<4; k++) s4[i][k] = std_to_k[w4[i][k] - 'A'];
    for (int i=0; i<n5; i++) for (int k=0; k<5; k++) s5[i][k] = std_to_k[w5[i][k] - 'A'];
    for (int i=0; i<n6; i++) for (int k=0; k<6; k++) s6[i][k] = std_to_k[w6[i][k] - 'A'];
    for (int i=0; i<n7; i++) for (int k=0; k<7; k++) s7[i][k] = std_to_k[w7[i][k] - 'A'];
    
    float global_best_sc = -999.0f;
    char global_best_pt[N+1];
    char best_w4[16], best_w5[16], best_w6[16], best_w7[16];
    
    double t0 = omp_get_wtime();
    
    // Pruned search: evaluate first 30 characters
    #pragma omp parallel
    {
        float local_best = -999.0f;
        char local_pt[N+1];
        char l_w4[16], l_w5[16], l_w6[16], l_w7[16];
        
        #pragma omp for schedule(dynamic, 1)
        for (int i4 = 0; i4 < n4; i4++) {
            for (int i7 = 0; i7 < n7; i7++) {
                // Precompute base shift mod 28
                int base28[28];
                for (int k=0; k<28; k++) {
                    base28[k] = (s4[i4][k % 4] + s7[i7][k % 7]) % 26;
                }
                
                for (int i5 = 0; i5 < n5; i5++) {
                    for (int i6 = 0; i6 < n6; i6++) {
                        // Check first 30 chars
                        float quick_sc = 0.0f;
                        int prev_q[3];
                        int valid = 1;
                        
                        char pt[N+1];
                        for (int k=0; k<30; k++) {
                            int sh = (base28[k % 28] + s5[i5][k % 5] + s6[i6][k % 6]) % 26;
                            int p_kr = (ct_kr[k] - sh + 26) % 26;
                            pt[k] = k_to_std[p_kr] + 'A';
                            if (k >= 3) {
                                quick_sc += quad[pt[k-3]-'A'][pt[k-2]-'A'][pt[k-1]-'A'][pt[k]-'A'];
                            }
                        }
                        
                        // Prune if early quad score is terrible
                        if (quick_sc / 27.0f < -6.5f) continue;
                        
                        // Evaluate full text
                        for (int k=30; k<N; k++) {
                            int sh = (base28[k % 28] + s5[i5][k % 5] + s6[i6][k % 6]) % 26;
                            int p_kr = (ct_kr[k] - sh + 26) % 26;
                            pt[k] = k_to_std[p_kr] + 'A';
                        }
                        pt[N] = '\0';
                        float full_sc = score_text(pt);
                        
                        if (full_sc > local_best) {
                            local_best = full_sc;
                            strcpy(local_pt, pt);
                            strcpy(l_w4, w4[i4]);
                            strcpy(l_w5, w5[i5]);
                            strcpy(l_w6, w6[i6]);
                            strcpy(l_w7, w7[i7]);
                            if (full_sc > -5.5f) {
                                #pragma omp critical
                                {
                                    printf("\n*** HIGH SCORE: %.4f ***\n", full_sc);
                                    printf("Keys: %s + %s + %s + %s\n", w4[i4], w5[i5], w6[i6], w7[i7]);
                                    printf("PT: %s\n", pt);
                                }
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
                strcpy(best_w4, l_w4);
                strcpy(best_w5, l_w5);
                strcpy(best_w6, l_w6);
                strcpy(best_w7, l_w7);
            }
        }
    }
    
    double elapsed = omp_get_wtime() - t0;
    printf("\nCompleted in %.2f s\n", elapsed);
    printf("Global Best Quad: %.4f\n", global_best_sc);
    printf("Keys: %s + %s + %s + %s\n", best_w4, best_w5, best_w6, best_w7);
    printf("Plaintext:\n%s\n", global_best_pt);
    
    return 0;
}
