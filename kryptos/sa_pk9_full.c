#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <time.h>
#include <omp.h>

#define N 144
#define W 12
#define H (N / W)

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
static const char *PK9_REAL = "KSYAWFEYYOISZGEUFBLYATAIBYFAQBQYYVDWJKLJXMYIEPIFVHPQNHZGSUHUUDXLEHRHUMALHEGLHXSJMUXGNUIVBXGUJHZRZGUSVHMLSCTSUQXHSUMQQIFUQGKHJGUQGLHDKEWSKAMHIJXD";

static int ct_kr[N];
static int k_to_std[26];
static int std_to_k[26];

void init() {
    for (int i=0; i<26; i++) {
        k_to_std[i] = KRYPTOS[i] - 'A';
        std_to_k[KRYPTOS[i] - 'A'] = i;
    }
    for (int i=0; i<N; i++) {
        ct_kr[i] = std_to_k[PK9_REAL[i] - 'A'];
    }
}

static const int anchor_shifts[28] = {
    5, 4, 9, 15, 16, 5, 6, 14, 5, 25, 20, 21, 10, 7, 14, 11, 7, 25, 10, 24, 22, 23, 18, 1, 7, 10, 7, 3
};

static const int anchor_perm[W] = {
    3, 0, 6, 2, 11, 5, 4, 1, 9, 7, 8, 10
};

float score_text(const char *t) {
    float sc = 0.0f;
    for (int i=0; i<N-3; i++) {
        sc += quad[t[i]-'A'][t[i+1]-'A'][t[i+2]-'A'][t[i+3]-'A'];
    }
    return sc / (N - 3);
}

void build_text(const int *shifts, const int *perm, char *out) {
    char z[N];
    for (int i=0; i<N; i++) {
        int p_kr = (ct_kr[i] - shifts[i % 28] + 26) % 26;
        z[i] = k_to_std[p_kr] + 'A';
    }
    int idx = 0;
    for (int r=0; r<H; r++) {
        for (int c=0; c<W; c++) {
            out[idx++] = z[perm[c] * H + r];
        }
    }
    out[N] = '\0';
}

int main() {
    load_quads();
    init();
    printf("Models loaded. Executing Simulated Annealing (20,000 restarts) on PK9...\n");
    
    double t0 = omp_get_wtime();
    float global_best_sc = -999.0f;
    char global_best_pt[N+1];
    int global_best_perm[W];
    int global_best_shifts[28];
    
    #pragma omp parallel
    {
        unsigned int seed = 101 + omp_get_thread_num() * 31337;
        
        float local_best_sc = -999.0f;
        char local_best_pt[N+1];
        int local_perm[W];
        int local_shifts[28];
        
        char cur_pt[N+1];
        int cur_perm[W];
        int cur_shifts[28];
        
        #pragma omp for schedule(dynamic)
        for (int restart = 0; restart < 20000; restart++) {
            // Half restarts from anchor, half from random
            if (restart % 2 == 0) {
                memcpy(cur_perm, anchor_perm, sizeof(cur_perm));
                memcpy(cur_shifts, anchor_shifts, sizeof(cur_shifts));
                // Add minor jitter
                for (int j = 0; j < 3; j++) {
                    int a = rand_r(&seed) % W;
                    int b = rand_r(&seed) % W;
                    int t = cur_perm[a]; cur_perm[a] = cur_perm[b]; cur_perm[b] = t;
                }
            } else {
                for (int i=0; i<W; i++) cur_perm[i] = i;
                for (int i=W-1; i>0; i--) {
                    int j = rand_r(&seed) % (i + 1);
                    int t = cur_perm[i]; cur_perm[i] = cur_perm[j]; cur_perm[j] = t;
                }
                memcpy(cur_shifts, anchor_shifts, sizeof(cur_shifts));
                for (int j = 0; j < 5; j++) {
                    cur_shifts[rand_r(&seed) % 28] = rand_r(&seed) % 26;
                }
            }
            
            build_text(cur_shifts, cur_perm, cur_pt);
            float cur_sc = score_text(cur_pt);
            
            float temp = 0.5f;
            float cooling = 0.985f;
            
            for (int step = 0; step < 800; step++) {
                temp *= cooling;
                
                int next_perm[W];
                memcpy(next_perm, cur_perm, sizeof(next_perm));
                int next_shifts[28];
                memcpy(next_shifts, cur_shifts, sizeof(next_shifts));
                
                int move_type = rand_r(&seed) % 10;
                if (move_type < 5) {
                    // Swap two columns
                    int a = rand_r(&seed) % W;
                    int b = rand_r(&seed) % W;
                    int t = next_perm[a]; next_perm[a] = next_perm[b]; next_perm[b] = t;
                } else if (move_type < 7) {
                    // 3-cycle of columns
                    int a = rand_r(&seed) % W;
                    int b = rand_r(&seed) % W;
                    int c = rand_r(&seed) % W;
                    int t = next_perm[a]; next_perm[a] = next_perm[b]; next_perm[b] = next_perm[c]; next_perm[c] = t;
                } else {
                    // Mutate 1 or 2 shifts
                    int col = rand_r(&seed) % 28;
                    int delta = (rand_r(&seed) % 5) - 2;
                    next_shifts[col] = (next_shifts[col] + delta + 26) % 26;
                }
                
                char next_pt[N+1];
                build_text(next_shifts, next_perm, next_pt);
                float next_sc = score_text(next_pt);
                
                float delta_e = next_sc - cur_sc;
                if (delta_e > 0 || (temp > 1e-4f && expf(delta_e / temp) > ((float)rand_r(&seed) / (float)RAND_MAX))) {
                    cur_sc = next_sc;
                    memcpy(cur_perm, next_perm, sizeof(cur_perm));
                    memcpy(cur_shifts, next_shifts, sizeof(cur_shifts));
                    strcpy(cur_pt, next_pt);
                    
                    if (cur_sc > local_best_sc) {
                        local_best_sc = cur_sc;
                        strcpy(local_best_pt, cur_pt);
                        memcpy(local_perm, cur_perm, sizeof(local_perm));
                        memcpy(local_shifts, cur_shifts, sizeof(local_shifts));
                        
                        if (cur_sc > -5.3f) {
                            #pragma omp critical
                            {
                                printf("\n*** HIGH SCORE! Quad: %.3f ***\n", cur_sc);
                                printf("PT: %s\n", cur_pt);
                            }
                        }
                    }
                }
            }
        }
        
        #pragma omp critical
        {
            if (local_best_sc > global_best_sc) {
                global_best_sc = local_best_sc;
                strcpy(global_best_pt, local_best_pt);
                memcpy(global_best_perm, local_perm, sizeof(global_best_perm));
                memcpy(global_best_shifts, local_shifts, sizeof(global_best_shifts));
            }
        }
    }
    
    double elapsed = omp_get_wtime() - t0;
    printf("\nFinished in %.2f s (20,000 restarts)\n", elapsed);
    printf("Global Best Quad: %.3f\n", global_best_sc);
    printf("Perm: [");
    for (int i=0; i<W; i++) printf("%d%s", global_best_perm[i], i==W-1?"":", ");
    printf("]\n");
    printf("Shifts: [");
    for (int i=0; i<28; i++) printf("%d%s", global_best_shifts[i], i==27?"":", ");
    printf("]\n");
    printf("PT:\n%s\n", global_best_pt);
    
    return 0;
}
