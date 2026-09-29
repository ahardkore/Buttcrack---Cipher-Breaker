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

static const int init_shifts[28] = {
    5, 2, 9, 15, 17, 5, 6, 16, 5, 25, 20, 21, 10, 7, 14, 11, 7, 2, 8, 24, 21, 23, 18, 1, 7, 10, 7, 3
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
            int col_orig = perm[c];
            out[idx++] = z[col_orig * H + r];
        }
    }
    out[N] = '\0';
}

int main() {
    load_quads();
    init();
    printf("Models loaded. Starting multi-threaded hill climbing on Width 12...\n");
    
    srand(12345);
    
    float global_best_sc = -999.0f;
    char global_best_pt[N+1];
    int global_best_perm[W];
    int global_best_shifts[28];
    
    #pragma omp parallel
    {
        unsigned int seed = 42 + omp_get_thread_num() * 10007;
        
        float local_best_sc = -999.0f;
        char local_best_pt[N+1];
        int local_perm[W];
        int local_shifts[28];
        char cur_pt[N+1];
        
        #pragma omp for schedule(dynamic)
        for (int restart = 0; restart < 2000; restart++) {
            int cur_perm[W];
            for (int i=0; i<W; i++) cur_perm[i] = i;
            for (int i=W-1; i>0; i--) {
                int j = rand_r(&seed) % (i + 1);
                int tmp = cur_perm[i]; cur_perm[i] = cur_perm[j]; cur_perm[j] = tmp;
            }
            int cur_shifts[28];
            memcpy(cur_shifts, init_shifts, sizeof(cur_shifts));
            
            build_text(cur_shifts, cur_perm, cur_pt);
            float cur_sc = score_text(cur_pt);
            
            int improved = 1;
            int steps = 0;
            while (improved && steps < 500) {
                improved = 0;
                steps++;
                
                for (int a = 0; a < W - 1; a++) {
                    for (int b = a + 1; b < W; b++) {
                        int tmp = cur_perm[a]; cur_perm[a] = cur_perm[b]; cur_perm[b] = tmp;
                        build_text(cur_shifts, cur_perm, cur_pt);
                        float sc = score_text(cur_pt);
                        if (sc > cur_sc) {
                            cur_sc = sc;
                            improved = 1;
                        } else {
                            tmp = cur_perm[a]; cur_perm[a] = cur_perm[b]; cur_perm[b] = tmp;
                        }
                    }
                }
                
                if (steps % 3 == 0) {
                    for (int col = 0; col < 28; col++) {
                        int orig_s = cur_shifts[col];
                        for (int delta = -2; delta <= 2; delta++) {
                            if (delta == 0) continue;
                            cur_shifts[col] = (orig_s + delta + 26) % 26;
                            build_text(cur_shifts, cur_perm, cur_pt);
                            float sc = score_text(cur_pt);
                            if (sc > cur_sc) {
                                cur_sc = sc;
                                orig_s = cur_shifts[col];
                                improved = 1;
                            } else {
                                cur_shifts[col] = orig_s;
                            }
                        }
                    }
                }
            }
            
            if (cur_sc > local_best_sc) {
                local_best_sc = cur_sc;
                memcpy(local_best_pt, cur_pt, sizeof(local_best_pt));
                memcpy(local_perm, cur_perm, sizeof(local_perm));
                memcpy(local_shifts, cur_shifts, sizeof(local_shifts));
            }
        }
        
        #pragma omp critical
        {
            if (local_best_sc > global_best_sc) {
                global_best_sc = local_best_sc;
                memcpy(global_best_pt, local_best_pt, sizeof(global_best_pt));
                memcpy(global_best_perm, local_perm, sizeof(local_perm));
                memcpy(global_best_shifts, local_shifts, sizeof(local_shifts));
            }
        }
    }
    
    printf("\nGlobal Best Quad: %.3f\n", global_best_sc);
    printf("Perm: [");
    for (int i=0; i<W; i++) printf("%d%s", global_best_perm[i], i==W-1?"":", ");
    printf("]\n");
    printf("Shifts: [");
    for (int i=0; i<28; i++) printf("%d%s", global_best_shifts[i], i==27?"":", ");
    printf("]\n");
    printf("Best PT:\n%s\n", global_best_pt);
    
    return 0;
}
