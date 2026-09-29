#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>

#define N 144
#define W 12
#define H 12

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

static const int perm[W] = {
    3, 0, 6, 2, 11, 5, 4, 1, 9, 7, 8, 10
};

float eval_4clocks(const int *q4, const int *q5, const int *q6, const int *q7, char *out) {
    char z[N];
    for (int i=0; i<N; i++) {
        int sh = (q4[i % 4] + q5[i % 5] + q6[i % 6] + q7[i % 7]) % 26;
        int p_kr = (ct_kr[i] - sh + 26) % 26;
        z[i] = k_to_std[p_kr] + 'A';
    }
    int idx = 0;
    for (int r=0; r<H; r++) {
        for (int c=0; c<W; c++) {
            out[idx++] = z[perm[c] * H + r];
        }
    }
    out[N] = '\0';
    float sc = 0.0f;
    for (int i=0; i<N-3; i++) {
        sc += quad[out[i]-'A'][out[i+1]-'A'][out[i+2]-'A'][out[i+3]-'A'];
    }
    return sc / (N - 3);
}

int main() {
    load_quads();
    init();
    printf("Models loaded. Executing Simulated Annealing (100,000 restarts) on Q4 x Q5 x Q6 x Q7 on PK9...\n");
    
    double t0 = omp_get_wtime();
    float global_best_sc = -999.0f;
    char global_best_pt[N+1];
    int best_q4[4], best_q5[5], best_q6[6], best_q7[7];
    
    #pragma omp parallel
    {
        unsigned int seed = 777 + omp_get_thread_num() * 19999;
        
        float local_best_sc = -999.0f;
        char local_best_pt[N+1];
        int l_q4[4], l_q5[5], l_q6[6], l_q7[7];
        
        char cur_pt[N+1];
        int c_q4[4], c_q5[5], c_q6[6], c_q7[7];
        
        #pragma omp for schedule(dynamic)
        for (int restart = 0; restart < 100000; restart++) {
            c_q4[0] = 0; for (int i=1; i<4; i++) c_q4[i] = rand_r(&seed) % 26;
            c_q5[0] = 0; for (int i=1; i<5; i++) c_q5[i] = rand_r(&seed) % 26;
            c_q6[0] = 0; for (int i=1; i<6; i++) c_q6[i] = rand_r(&seed) % 26;
            for (int i=0; i<7; i++) c_q7[i] = rand_r(&seed) % 26;
            
            float cur_sc = eval_4clocks(c_q4, c_q5, c_q6, c_q7, cur_pt);
            float temp = 0.5f;
            float cooling = 0.97f;
            
            for (int step = 0; step < 250; step++) {
                temp *= cooling;
                
                int n_q4[4], n_q5[5], n_q6[6], n_q7[7];
                memcpy(n_q4, c_q4, sizeof(n_q4));
                memcpy(n_q5, c_q5, sizeof(n_q5));
                memcpy(n_q6, c_q6, sizeof(n_q6));
                memcpy(n_q7, c_q7, sizeof(n_q7));
                
                int clock_choice = rand_r(&seed) % 4;
                int delta = (rand_r(&seed) % 5) - 2;
                if (clock_choice == 0) {
                    int idx = 1 + rand_r(&seed) % 3;
                    n_q4[idx] = (n_q4[idx] + delta + 26) % 26;
                } else if (clock_choice == 1) {
                    int idx = 1 + rand_r(&seed) % 4;
                    n_q5[idx] = (n_q5[idx] + delta + 26) % 26;
                } else if (clock_choice == 2) {
                    int idx = 1 + rand_r(&seed) % 5;
                    n_q6[idx] = (n_q6[idx] + delta + 26) % 26;
                } else {
                    int idx = rand_r(&seed) % 7;
                    n_q7[idx] = (n_q7[idx] + delta + 26) % 26;
                }
                
                char next_pt[N+1];
                float next_sc = eval_4clocks(n_q4, n_q5, n_q6, n_q7, next_pt);
                float diff = next_sc - cur_sc;
                if (diff > 0 || (temp > 1e-4f && expf(diff / temp) > ((float)rand_r(&seed) / (float)RAND_MAX))) {
                    cur_sc = next_sc;
                    memcpy(c_q4, n_q4, sizeof(c_q4));
                    memcpy(c_q5, n_q5, sizeof(c_q5));
                    memcpy(c_q6, n_q6, sizeof(c_q6));
                    memcpy(c_q7, n_q7, sizeof(c_q7));
                    strcpy(cur_pt, next_pt);
                    
                    if (cur_sc > local_best_sc) {
                        local_best_sc = cur_sc;
                        strcpy(local_best_pt, cur_pt);
                        memcpy(l_q4, c_q4, sizeof(l_q4));
                        memcpy(l_q5, c_q5, sizeof(l_q5));
                        memcpy(l_q6, c_q6, sizeof(l_q6));
                        memcpy(l_q7, c_q7, sizeof(l_q7));
                    }
                }
            }
        }
        
        #pragma omp critical
        {
            if (local_best_sc > global_best_sc) {
                global_best_sc = local_best_sc;
                strcpy(global_best_pt, local_best_pt);
                memcpy(best_q4, l_q4, sizeof(best_q4));
                memcpy(best_q5, l_q5, sizeof(best_q5));
                memcpy(best_q6, l_q6, sizeof(best_q6));
                memcpy(best_q7, l_q7, sizeof(best_q7));
                printf("New Best Score: %.4f\n", global_best_sc);
            }
        }
    }
    
    double elapsed = omp_get_wtime() - t0;
    printf("\nFinished 100,000 restarts in %.2f s\n", elapsed);
    printf("Global Best Quad: %.4f\n", global_best_sc);
    printf("q4: [%d, %d, %d, %d]\n", best_q4[0], best_q4[1], best_q4[2], best_q4[3]);
    printf("q5: [%d, %d, %d, %d, %d]\n", best_q5[0], best_q5[1], best_q5[2], best_q5[3], best_q5[4]);
    printf("q6: [%d, %d, %d, %d, %d, %d]\n", best_q6[0], best_q6[1], best_q6[2], best_q6[3], best_q6[4], best_q6[5]);
    printf("q7: [%d, %d, %d, %d, %d, %d, %d]\n", best_q7[0], best_q7[1], best_q7[2], best_q7[3], best_q7[4], best_q7[5], best_q7[6]);
    printf("Plaintext:\n");
    for (int r=0; r<H; r++) {
        char row[W+1];
        strncpy(row, global_best_pt + r*W, W);
        row[W] = '\0';
        printf("Row %2d: %s\n", r, row);
    }
    
    return 0;
}
