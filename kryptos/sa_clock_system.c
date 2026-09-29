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

float eval_clocks(const int *a, const int *b, char *out) {
    char z[N];
    for (int i=0; i<N; i++) {
        int sh = (a[i % 4] + b[i % 7]) % 26;
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
    printf("Models loaded. Executing Simulated Annealing (100,000 restarts) on Q4 x Q7 clock model...\n");
    
    double t0 = omp_get_wtime();
    float global_best_sc = -999.0f;
    char global_best_pt[N+1];
    int global_best_a[4];
    int global_best_b[7];
    
    #pragma omp parallel
    {
        unsigned int seed = 42 + omp_get_thread_num() * 10007;
        
        float local_best_sc = -999.0f;
        char local_best_pt[N+1];
        int local_best_a[4];
        int local_best_b[7];
        
        char cur_pt[N+1];
        int cur_a[4];
        int cur_b[7];
        
        #pragma omp for schedule(dynamic)
        for (int restart = 0; restart < 100000; restart++) {
            cur_a[0] = 0; // gauge fix
            for (int i=1; i<4; i++) cur_a[i] = rand_r(&seed) % 26;
            for (int j=0; j<7; j++) cur_b[j] = rand_r(&seed) % 26;
            
            float cur_sc = eval_clocks(cur_a, cur_b, cur_pt);
            float temp = 0.4f;
            float cooling = 0.96f;
            
            for (int step = 0; step < 300; step++) {
                temp *= cooling;
                
                int next_a[4];
                int next_b[7];
                memcpy(next_a, cur_a, sizeof(next_a));
                memcpy(next_b, cur_b, sizeof(next_b));
                
                // Pick one coordinate to mutate
                int var = rand_r(&seed) % 10;
                if (var < 3) {
                    // mutate a[var + 1]
                    next_a[var + 1] = (next_a[var + 1] + (rand_r(&seed) % 5 - 2) + 26) % 26;
                } else {
                    // mutate b[var - 3]
                    next_b[var - 3] = (next_b[var - 3] + (rand_r(&seed) % 5 - 2) + 26) % 26;
                }
                
                char next_pt[N+1];
                float next_sc = eval_clocks(next_a, next_b, next_pt);
                float delta = next_sc - cur_sc;
                
                if (delta > 0 || (temp > 1e-4f && expf(delta / temp) > ((float)rand_r(&seed) / (float)RAND_MAX))) {
                    cur_sc = next_sc;
                    memcpy(cur_a, next_a, sizeof(cur_a));
                    memcpy(cur_b, next_b, sizeof(cur_b));
                    strcpy(cur_pt, next_pt);
                    
                    if (cur_sc > local_best_sc) {
                        local_best_sc = cur_sc;
                        strcpy(local_best_pt, cur_pt);
                        memcpy(local_best_a, cur_a, sizeof(cur_a));
                        memcpy(local_best_b, cur_b, sizeof(cur_b));
                    }
                }
            }
        }
        
        #pragma omp critical
        {
            if (local_best_sc > global_best_sc) {
                global_best_sc = local_best_sc;
                strcpy(global_best_pt, local_best_pt);
                memcpy(global_best_a, local_best_a, sizeof(global_best_a));
                memcpy(global_best_b, local_best_b, sizeof(global_best_b));
                printf("New Global Best: Quad = %.4f | a=[%d, %d, %d, %d] | b=[%d, %d, %d, %d, %d, %d, %d]\n",
                       global_best_sc,
                       global_best_a[0], global_best_a[1], global_best_a[2], global_best_a[3],
                       global_best_b[0], global_best_b[1], global_best_b[2], global_best_b[3],
                       global_best_b[4], global_best_b[5], global_best_b[6]);
            }
        }
    }
    
    double elapsed = omp_get_wtime() - t0;
    printf("\nCompleted 100,000 restarts in %.2f s\n", elapsed);
    printf("Global Best Quad: %.4f\n", global_best_sc);
    printf("Optimal a: [%d, %d, %d, %d]\n", global_best_a[0], global_best_a[1], global_best_a[2], global_best_a[3]);
    printf("Optimal b: [%d, %d, %d, %d, %d, %d, %d]\n",
           global_best_b[0], global_best_b[1], global_best_b[2], global_best_b[3],
           global_best_b[4], global_best_b[5], global_best_b[6]);
    printf("Plaintext:\n");
    for (int r=0; r<H; r++) {
        char row[W+1];
        strncpy(row, global_best_pt + r*W, W);
        row[W] = '\0';
        printf("Row %2d: %s\n", r, row);
    }
    
    return 0;
}
