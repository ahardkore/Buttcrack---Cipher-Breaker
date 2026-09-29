#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>
#include "pos0_solver.h"

#define N 153
#define L 16

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
static int c_idx[N];
static int hpos[256];
static int k_to_std[26];

void init_tables() {
    for (int i=0; i<26; i++) {
        hpos[(unsigned char)KRYPTOS[i]] = i;
        k_to_std[i] = KRYPTOS[i] - 'A';
    }
    for (int i=0; i<N; i++) {
        c_idx[i] = hpos[(unsigned char)PK8_CT[i]];
    }
}

int main() {
    load_quads();
    init_tables();
    printf("Models loaded.\n");
    
    // Read cribs
    FILE *f = fopen("cribs_len16.txt", "r");
    if (!f) { printf("Cannot open cribs_len16.txt\n"); return 1; }
    
    // Count cribs
    int max_cribs = 700000;
    char (*cribs)[17] = malloc(max_cribs * 17);
    int n_cribs = 0;
    while (fgets(cribs[n_cribs], 17, f) && n_cribs < max_cribs) {
        // remove newline if present
        int len = strlen(cribs[n_cribs]);
        while (len > 0 && (cribs[n_cribs][len-1] == '\n' || cribs[n_cribs][len-1] == '\r')) {
            cribs[n_cribs][--len] = '\0';
        }
        if (len == 16) n_cribs++;
    }
    fclose(f);
    printf("Loaded %d 16-character cribs.\n", n_cribs);
    
    // First pass: test with q7[5] = 6 and q7[6] = 7 (from PK9)
    printf("Testing with Q7[5]=6, Q7[6]=7 from PK9...\n");
    double t0 = omp_get_wtime();
    
    float best_sc = -999.0f;
    char best_crib[17];
    char best_pt[N+1];
    best_pt[N] = '\0';
    
    #pragma omp parallel
    {
        float local_best = -999.0f;
        char local_crib[17];
        char local_pt[N+1];
        
        int diff[16];
        int rhs[16];
        int vars[18];
        int q4[4], q5[5], q6[6], q7[7];
        int pt[N];
        
        int y0 = 6, y1 = 7;
        vars[16] = y0;
        vars[17] = y1;
        
        #pragma omp for schedule(dynamic, 1000)
        for (int i = 0; i < n_cribs; i++) {
            const char *cr = cribs[i];
            for (int k = 0; k < 16; k++) {
                int p_idx = hpos[(unsigned char)cr[k]];
                diff[k] = (c_idx[k] - p_idx + 26) % 26;
                int r = diff[k] - (M_free[k][0] * y0 + M_free[k][1] * y1);
                rhs[k] = (r % 26 + 26) % 26;
            }
            
            // vars[0..15] = sub_inv * rhs mod 26
            for (int r = 0; r < 16; r++) {
                int sum = 0;
                for (int c = 0; c < 16; c++) {
                    sum += sub_inv[r][c] * rhs[c];
                }
                vars[r] = sum % 26;
            }
            
            // Map vars to clocks:
            // 0..3: q4[0..3]
            // 4..7: q5[1..4]
            // 8..11: q6[1..4]
            // 12..17: q7[1..6]
            q4[0] = vars[0]; q4[1] = vars[1]; q4[2] = vars[2]; q4[3] = vars[3];
            q5[0] = 0; q5[1] = vars[4]; q5[2] = vars[5]; q5[3] = vars[6]; q5[4] = vars[7];
            q6[0] = 0; q6[1] = vars[8]; q6[2] = vars[9]; q6[3] = vars[10]; q6[4] = vars[11]; q6[5] = 0;
            q7[0] = 0; q7[1] = vars[12]; q7[2] = vars[13]; q7[3] = vars[14]; q7[4] = vars[15]; q7[5] = vars[16]; q7[6] = vars[17];
            
            // Score characters 16..32
            for (int k = 16; k < 32; k++) {
                int shift = (q4[k % 4] + q5[k % 5] + q6[k % 6] + q7[k % 7]) % 26;
                int p = (c_idx[k] - shift + 26) % 26;
                pt[k] = k_to_std[p];
            }
            float sc16 = 0.0f;
            for (int k = 16; k < 29; k++) {
                sc16 += quad[pt[k]][pt[k+1]][pt[k+2]][pt[k+3]];
            }
            if (sc16 / 13.0f < -6.5f) continue;
            
            // Full decrypt
            for (int k = 0; k < 16; k++) {
                int shift = (q4[k % 4] + q5[k % 5] + q6[k % 6] + q7[k % 7]) % 26;
                int p = (c_idx[k] - shift + 26) % 26;
                pt[k] = k_to_std[p];
            }
            for (int k = 32; k < N; k++) {
                int shift = (q4[k % 4] + q5[k % 5] + q6[k % 6] + q7[k % 7]) % 26;
                int p = (c_idx[k] - shift + 26) % 26;
                pt[k] = k_to_std[p];
            }
            
            float full_sc = 0.0f;
            for (int k = 0; k < N - 3; k++) {
                full_sc += quad[pt[k]][pt[k+1]][pt[k+2]][pt[k+3]];
            }
            full_sc /= (N - 3);
            
            if (full_sc > -5.2f) {
                #pragma omp critical
                {
                    char pt_str[N+1];
                    for (int k=0; k<N; k++) pt_str[k] = 'A' + pt[k];
                    pt_str[N] = '\0';
                    printf("\n*** SOLVE CANDIDATE HIT! Score: %.4f ***\n", full_sc);
                    printf("  Crib: %s\n", cr);
                    printf("  PT: %s\n", pt_str);
                }
            }
            if (full_sc > local_best) {
                local_best = full_sc;
                strcpy(local_crib, cr);
                for (int k=0; k<N; k++) local_pt[k] = 'A' + pt[k];
                local_pt[N] = '\0';
            }
        }
        
        #pragma omp critical
        {
            if (local_best > best_sc) {
                best_sc = local_best;
                strcpy(best_crib, local_crib);
                strcpy(best_pt, local_pt);
            }
        }
    }
    
    double elapsed = omp_get_wtime() - t0;
    printf("Evaluated %d cribs in %.2f s (%.0f cribs/sec)\n", n_cribs, elapsed, (double)n_cribs / elapsed);
    printf("Best Score: %.4f | Crib: %s\n", best_sc, best_crib);
    printf("PT: %s\n", best_pt);
    
    free(cribs);
    return 0;
}
