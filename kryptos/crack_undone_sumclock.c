#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>

#define N 144

static float quad[26][26][26][26];

void load_quads() {
    for (int a=0; a<26; a++)
        for (int b=0; b<26; b++)
            for (int c=0; c<26; c++)
                for (int d=0; d<26; d++)
                    quad[a][b][c][d] = -9.5f;
    FILE *f = fopen("english_quadgrams.txt", "r");
    if (!f) { printf("Cannot open english_quadgrams.txt\n"); exit(1); }
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
static const char *UNDONE = "QGKVHPZGUKSYHEGBYFHJGQNHSVHAWFLHXAQBUQGZGSMLSEYYSJMQYYLHDUHUCTSOISUXGVDWKEWUDXUQXZGENUIJKLSKALEHHSUUFBVBXJXMMHIRHUMQQLYAGUJYIEJXDMALIFUTAIHZRPIF";

static int u_kryptos[N];
static int u_standard[N];
static int k_to_std[26];

void init_tables() {
    int hpos_k[256];
    for (int i=0; i<26; i++) {
        hpos_k[(unsigned char)KRYPTOS[i]] = i;
        k_to_std[i] = KRYPTOS[i] - 'A';
    }
    for (int i=0; i<N; i++) {
        u_kryptos[i] = hpos_k[(unsigned char)UNDONE[i]];
        u_standard[i] = UNDONE[i] - 'A';
    }
}

int main() {
    load_quads();
    init_tables();
    printf("Models loaded. Length of undone: %d\n", N);
    
    // Halfabet mod 13 schedule for Q7
    const int s13[7] = {0, 2, 9, 10, 10, 6, 7};
    
    // Test both alphabets: KRYPTOS and STANDARD
    // Test both sign conventions: Vigenere (C - K) and Beaufort (K - C)
    for (int alph_type = 0; alph_type < 2; alph_type++) {
        const int *u_idx = (alph_type == 0) ? u_kryptos : u_standard;
        const char *alph_name = (alph_type == 0) ? "KRYPTOS" : "STANDARD";
        
        for (int sign = 1; sign >= -1; sign -= 2) {
            const char *sign_name = (sign == 1) ? "Vigenere (C - K)" : "Beaufort (K - C)";
            printf("\n=== Alphabet: %s | Mode: %s ===\n", alph_name, sign_name);
            
            float global_best = -999.0f;
            int best_mask = -1;
            int best_q4[4] = {0};
            int best_q7[7] = {0};
            char best_pt[N+1];
            best_pt[N] = '\0';
            
            double t0 = omp_get_wtime();
            
            #pragma omp parallel
            {
                float local_best = -999.0f;
                int local_mask = -1;
                int local_q4[4] = {0};
                int local_q7[7] = {0};
                char local_pt[N+1];
                int pt[N];
                
                #pragma omp for schedule(dynamic)
                for (int mask = 0; mask < 128; mask++) {
                    int q7[7];
                    for (int j = 0; j < 7; j++) {
                        q7[j] = (s13[j] + 13 * ((mask >> j) & 1)) % 26;
                    }
                    
                    int q4[4] = {0, 0, 0, 0};
                    
                    for (int q1 = 0; q1 < 26; q1++) {
                        q4[1] = q1;
                        for (int q2 = 0; q2 < 26; q2++) {
                            q4[2] = q2;
                            for (int q3 = 0; q3 < 26; q3++) {
                                q4[3] = q3;
                                
                                // Decrypt
                                if (sign == 1) { // C - K
                                    for (int i = 0; i < N; i++) {
                                        int k = (q4[i % 4] + q7[i % 7]) % 26;
                                        int p = (u_idx[i] - k + 26) % 26;
                                        pt[i] = (alph_type == 0) ? k_to_std[p] : p;
                                    }
                                } else { // K - C
                                    for (int i = 0; i < N; i++) {
                                        int k = (q4[i % 4] + q7[i % 7]) % 26;
                                        int p = (k - u_idx[i] + 26) % 26;
                                        pt[i] = (alph_type == 0) ? k_to_std[p] : p;
                                    }
                                }
                                
                                // Score with quadgrams
                                float sc = 0.0f;
                                for (int i = 0; i < N - 3; i++) {
                                    sc += quad[pt[i]][pt[i+1]][pt[i+2]][pt[i+3]];
                                }
                                sc /= (N - 3);
                                
                                if (sc > -5.2f) {
                                    #pragma omp critical
                                    {
                                        char pt_str[N+1];
                                        for (int i=0; i<N; i++) pt_str[i] = 'A' + pt[i];
                                        pt_str[N] = '\0';
                                        printf("\n*** HIGH SCORE HIT! Score: %.4f ***\n", sc);
                                        printf("  Mask: %d | Q7: %d %d %d %d %d %d %d\n", mask, q7[0], q7[1], q7[2], q7[3], q7[4], q7[5], q7[6]);
                                        printf("  Q4: %d %d %d %d\n", q4[0], q4[1], q4[2], q4[3]);
                                        printf("  PT: %s\n", pt_str);
                                    }
                                }
                                
                                if (sc > local_best) {
                                    local_best = sc;
                                    local_mask = mask;
                                    memcpy(local_q4, q4, sizeof(q4));
                                    memcpy(local_q7, q7, sizeof(q7));
                                    for (int i=0; i<N; i++) local_pt[i] = 'A' + pt[i];
                                    local_pt[N] = '\0';
                                }
                            }
                        }
                    }
                }
                
                #pragma omp critical
                {
                    if (local_best > global_best) {
                        global_best = local_best;
                        best_mask = local_mask;
                        memcpy(best_q4, local_q4, sizeof(best_q4));
                        memcpy(best_q7, local_q7, sizeof(best_q7));
                        strcpy(best_pt, local_pt);
                    }
                }
            }
            
            double elapsed = omp_get_wtime() - t0;
            printf("Finished in %.2f s (%.0f pairs/sec)\n", elapsed, 2249728.0 / elapsed);
            printf("Global Best Quad: %.4f\n", global_best);
            printf("Best Mask: %d | Q7: %d %d %d %d %d %d %d\n", best_mask, best_q7[0], best_q7[1], best_q7[2], best_q7[3], best_q7[4], best_q7[5], best_q7[6]);
            printf("Best Q4: %d %d %d %d\n", best_q4[0], best_q4[1], best_q4[2], best_q4[3]);
            printf("PT: %s\n", best_pt);
        }
    }
    
    return 0;
}
