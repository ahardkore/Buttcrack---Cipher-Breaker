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
static const char *PK8_CT = "COPVEJJVSVURTVIPYOTPLHGBTMAUCCPESIWIGZBWSJPKTRPUEKQFIFCLHMXTHIMHWOYIGURBOMPARCVXVKBDDVBVHDRHGCVNWWVLBMYWMWHICFIXZWBVZYCQGNOGJGUMLNPUTHQCXNWPQZOIRJZGSWVPY";
static int c_base[N];
static int k_to_std[26];

void init_tables() {
    int hpos[256];
    for (int i=0; i<26; i++) {
        hpos[(unsigned char)KRYPTOS[i]] = i;
        k_to_std[i] = KRYPTOS[i] - 'A';
    }
    const int q4[4] = {4, 0, 0, 0};
    const int q7[7] = {0, 2, 9, 10, 10, 6, 7};
    for (int i=0; i<N; i++) {
        int raw = hpos[(unsigned char)PK8_CT[i]];
        c_base[i] = (raw - q4[i % 4] - q7[i % 7] + 52) % 26;
    }
}

int main(int argc, char **argv) {
    load_quads();
    init_tables();
    
    int max_q5_4 = (argc > 1) ? atoi(argv[1]) : 5;
    printf("Sweeping q5_4 in 0..%d (total %d * 26^5 = %d states)...\n", max_q5_4 - 1, max_q5_4, max_q5_4 * 11881376);
    double t0 = omp_get_wtime();
    
    float global_best_score = -999.0f;
    char global_best_pt[N+1];
    global_best_pt[N] = '\0';
    
    #pragma omp parallel
    {
        float local_best = -999.0f;
        char local_pt[N+1];
        int q5[5] = {0, 0, 0, 0, 0};
        int q6[6] = {0, 0, 0, 0, 0, 0};
        int pt[N];
        
        #pragma omp for schedule(dynamic)
        for (int q5_4 = 0; q5_4 < max_q5_4; q5_4++) {
            q5[4] = q5_4;
            q6[4] = (26 - q5_4) % 26;
            
            for (int q5_2 = 0; q5_2 < 26; q5_2++) {
                q5[2] = q5_2;
                for (int q5_3 = 0; q5_3 < 26; q5_3++) {
                    q5[3] = q5_3;
                    for (int q6_1 = 0; q6_1 < 26; q6_1++) {
                        q6[1] = q6_1;
                        for (int q6_2 = 0; q6_2 < 26; q6_2++) {
                            q6[2] = q6_2;
                            for (int q6_3 = 0; q6_3 < 26; q6_3++) {
                                q6[3] = q6_3;
                                
                                // Super fast screen on 12 characters
                                for (int i = 0; i < 12; i++) {
                                    int k = (q5[i % 5] + q6[i % 6]) % 26;
                                    pt[i] = k_to_std[(c_base[i] - k + 26) % 26];
                                }
                                float sc12 = 0.0f;
                                for (int i = 0; i < 9; i++) {
                                    sc12 += quad[pt[i]][pt[i+1]][pt[i+2]][pt[i+3]];
                                }
                                if (sc12 < -60.0f) continue; // avg < -6.0
                                
                                // Screen next 16 characters
                                for (int i = 12; i < 28; i++) {
                                    int k = (q5[i % 5] + q6[i % 6]) % 26;
                                    pt[i] = k_to_std[(c_base[i] - k + 26) % 26];
                                }
                                float sc28 = sc12;
                                for (int i = 9; i < 25; i++) {
                                    sc28 += quad[pt[i]][pt[i+1]][pt[i+2]][pt[i+3]];
                                }
                                if (sc28 < -160.0f) continue; // avg < -5.8
                                
                                // Full decrypt
                                for (int i = 28; i < N; i++) {
                                    int k = (q5[i % 5] + q6[i % 6]) % 26;
                                    pt[i] = k_to_std[(c_base[i] - k + 26) % 26];
                                }
                                float full_sc = sc28;
                                for (int i = 25; i < N - 3; i++) {
                                    full_sc += quad[pt[i]][pt[i+1]][pt[i+2]][pt[i+3]];
                                }
                                full_sc /= (N - 3);
                                
                                if (full_sc > -5.2f) {
                                    #pragma omp critical
                                    {
                                        char pt_str[N+1];
                                        for (int i=0; i<N; i++) pt_str[i] = 'A' + pt[i];
                                        pt_str[N] = '\0';
                                        printf("\n*** HIGH SCORE HIT! Score: %.4f ***\n", full_sc);
                                        printf("  Q5: %d %d %d %d %d | Q6: %d %d %d %d %d %d\n", q5[0], q5[1], q5[2], q5[3], q5[4], q6[0], q6[1], q6[2], q6[3], q6[4], q6[5]);
                                        printf("  PT: %s\n", pt_str);
                                    }
                                }
                                if (full_sc > local_best) {
                                    local_best = full_sc;
                                    for (int i=0; i<N; i++) local_pt[i] = 'A' + pt[i];
                                    local_pt[N] = '\0';
                                }
                            }
                        }
                    }
                }
            }
        }
        
        #pragma omp critical
        {
            if (local_best > global_best_score) {
                global_best_score = local_best;
                strcpy(global_best_pt, local_pt);
            }
        }
    }
    
    double elapsed = omp_get_wtime() - t0;
    printf("Finished in %.2f seconds (%.0f states/sec)\n", elapsed, (double)max_q5_4 * 11881376.0 / elapsed);
    printf("Global Best Quad: %.4f\n", global_best_score);
    if (global_best_score > -900.0f) {
        printf("Global Best PT: %s\n", global_best_pt);
    }
    return 0;
}
