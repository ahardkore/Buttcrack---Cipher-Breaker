#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>
#include <time.h>

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
static const char *PK8_CT = "COPVEJJVSVURTVIPYOTPLHGBTMAUCCFFGIZWSSGTYJOGUKVFXGTTUKUOXFLMRLJMSCGHCVRCRUKCWHUPRCLQGOGCRFFVTYJTTTVQSSQZZFCEHYNMTUSSUKMMQJGUVTMMPSSWVYCTMLVLSWPQZOIRJZGSWVPY";
static int c_idx[N];
static int k_to_std[26];

void init_tables() {
    int hpos[256];
    for (int i=0; i<26; i++) {
        hpos[(unsigned char)KRYPTOS[i]] = i;
        k_to_std[i] = KRYPTOS[i] - 'A';
    }
    for (int i=0; i<N; i++) {
        c_idx[i] = hpos[(unsigned char)PK8_CT[i]];
    }
}

static inline float eval_pt(const int *q4, const int *q5, const int *q6, const int *q7, int *out_pt) {
    int pt[N];
    for (int i=0; i<N; i++) {
        int k = (q4[i % 4] + q5[i % 5] + q6[i % 6] + q7[i % 7]) % 26;
        int p = (c_idx[i] - k + 26) % 26;
        pt[i] = k_to_std[p];
        if (out_pt) out_pt[i] = pt[i];
    }
    float sc = 0.0f;
    for (int i=0; i<N-3; i++) {
        sc += quad[pt[i]][pt[i+1]][pt[i+2]][pt[i+3]];
    }
    return sc / (N - 3);
}

// Xoroshiro128+ PRNG
static inline unsigned long long rotl(const unsigned long long x, int k) {
    return (x << k) | (x >> (64 - k));
}

unsigned long long next_rand(unsigned long long s[2]) {
    const unsigned long long s0 = s[0];
    unsigned long long s1 = s[1];
    const unsigned long long result = s0 + s1;
    s1 ^= s0;
    s[0] = rotl(s0, 55) ^ s1 ^ (s1 << 14);
    s[1] = rotl(s1, 36);
    return result;
}

int main(int argc, char **argv) {
    load_quads();
    init_tables();
    printf("Models loaded. PK8 length: %d\n", N);
    
    int n_restarts = (argc > 1) ? atoi(argv[1]) : 1000;
    int iters_per_restart = (argc > 2) ? atoi(argv[2]) : 50000;
    
    printf("Running %d simulated annealing restarts with %d iters each...\n", n_restarts, iters_per_restart);
    
    float global_best_score = -999.0f;
    char global_best_pt[N+1];
    global_best_pt[N] = '\0';
    
    double t0 = omp_get_wtime();
    
    #pragma omp parallel
    {
        int tid = omp_get_thread_num();
        unsigned long long rng[2] = {123456789ULL + tid * 99991ULL, 987654321ULL + tid * 10007ULL};
        
        #pragma omp for schedule(dynamic)
        for (int r = 0; r < n_restarts; r++) {
            int q4[4], q5[5], q6[6], q7[7];
            for (int i=0; i<4; i++) q4[i] = next_rand(rng) % 26;
            for (int i=0; i<5; i++) q5[i] = next_rand(rng) % 26;
            for (int i=0; i<6; i++) q6[i] = next_rand(rng) % 26;
            for (int i=0; i<7; i++) q7[i] = next_rand(rng) % 26;
            // Gauge choices:
            q5[0] = 0; q6[0] = 0; q7[0] = 0;
            
            float cur_score = eval_pt(q4, q5, q6, q7, NULL);
            float best_sc = cur_score;
            int b_q4[4], b_q5[5], b_q6[6], b_q7[7];
            memcpy(b_q4, q4, sizeof(q4));
            memcpy(b_q5, q5, sizeof(q5));
            memcpy(b_q6, q6, sizeof(q6));
            memcpy(b_q7, q7, sizeof(q7));
            
            float temp = 1.0f;
            float cooling = 0.9999f;
            
            for (int it = 0; it < iters_per_restart; it++) {
                // Pick a clock to mutate (excluding gauge variables)
                int choice = next_rand(rng) % 19;
                int old_val;
                int *target;
                
                if (choice < 4) {
                    target = &q4[choice];
                } else if (choice < 4 + 4) {
                    target = &q5[1 + (choice - 4)];
                } else if (choice < 4 + 4 + 5) {
                    target = &q6[1 + (choice - 8)];
                } else {
                    target = &q7[1 + (choice - 13)];
                }
                
                old_val = *target;
                *target = next_rand(rng) % 26;
                
                float new_score = eval_pt(q4, q5, q6, q7, NULL);
                float delta = new_score - cur_score;
                
                if (delta > 0 || (temp > 1e-4f && expf(delta / temp) > (float)(next_rand(rng) % 10000) / 10000.0f)) {
                    cur_score = new_score;
                    if (cur_score > best_sc) {
                        best_sc = cur_score;
                        memcpy(b_q4, q4, sizeof(q4));
                        memcpy(b_q5, q5, sizeof(q5));
                        memcpy(b_q6, q6, sizeof(q6));
                        memcpy(b_q7, q7, sizeof(q7));
                    }
                } else {
                    *target = old_val;
                }
                temp *= cooling;
            }
            
            if (best_sc > -5.2f) {
                int pt_arr[N];
                eval_pt(b_q4, b_q5, b_q6, b_q7, pt_arr);
                char pt_str[N+1];
                for (int i=0; i<N; i++) pt_str[i] = 'A' + pt_arr[i];
                pt_str[N] = '\0';
                
                #pragma omp critical
                {
                    printf("\n[Restart %d] Score: %.4f\n", r, best_sc);
                    printf("  PT: %s\n", pt_str);
                    if (best_sc > global_best_score) {
                        global_best_score = best_sc;
                        strcpy(global_best_pt, pt_str);
                    }
                }
            }
        }
    }
    
    double elapsed = omp_get_wtime() - t0;
    printf("\nFinished in %.2f seconds (%.0f evals/sec)\n", elapsed, (double)n_restarts * iters_per_restart / elapsed);
    printf("Global Best Quad: %.4f\n", global_best_score);
    if (global_best_score > -900.0f) {
        printf("Global Best PT: %s\n", global_best_pt);
    }
    return 0;
}
