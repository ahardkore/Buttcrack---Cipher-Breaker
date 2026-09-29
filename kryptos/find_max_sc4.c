#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>

#define N 144
#define P 7
#define N_ROWS 20

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

static int grid[N_ROWS][P];
static int k_to_std[26];

void init_tables(int use_kryptos) {
    int hpos[256];
    const char *alph = use_kryptos ? KRYPTOS : "ABCDEFGHIJKLMNOPQRSTUVWXYZ";
    for (int i=0; i<26; i++) {
        hpos[(unsigned char)alph[i]] = i;
        k_to_std[i] = alph[i] - 'A';
    }
    for (int r=0; r<N_ROWS; r++) {
        for (int c=0; c<P; c++) {
            grid[r][c] = hpos[(unsigned char)UNDONE[r * P + c]];
        }
    }
}

void search_shifts(int use_kryptos) {
    init_tables(use_kryptos);
    printf("\n=== Searching 7 shifts on %s alphabet ===\n", use_kryptos ? "KRYPTOS" : "STANDARD");
    
    float global_best = -999.0f;
    int best_shifts[7];
    char best_pt[N+1];
    best_pt[N] = '\0';
    
    double t0 = omp_get_wtime();
    long long total_tested = 0;
    
    #pragma omp parallel
    {
        float local_best = -999.0f;
        int local_shifts[7];
        char local_pt[N+1];
        int row_pt[7];
        
        #pragma omp for schedule(dynamic) reduction(+:total_tested)
        for (int s0 = 0; s0 < 26; s0++) {
            for (int s1 = 0; s1 < 26; s1++) {
                for (int s2 = 0; s2 < 26; s2++) {
                    for (int s3 = 0; s3 < 26; s3++) {
                        float sc4 = 0.0f;
                        for (int r = 0; r < N_ROWS; r++) {
                            int p0 = k_to_std[(grid[r][0] - s0 + 26) % 26];
                            int p1 = k_to_std[(grid[r][1] - s1 + 26) % 26];
                            int p2 = k_to_std[(grid[r][2] - s2 + 26) % 26];
                            int p3 = k_to_std[(grid[r][3] - s3 + 26) % 26];
                            sc4 += quad[p0][p1][p2][p3];
                        }
                        sc4 /= N_ROWS;
                        if (sc4 > local_best) {
                            local_best = sc4;
                            local_shifts[0] = s0; local_shifts[1] = s1; local_shifts[2] = s2; local_shifts[3] = s3;
                        }
                        continue;
                        
                        for (int s4 = 0; s4 < 26; s4++) {
                            // Stage 2: evaluate quadgram (s1, s2, s3, s4) across 20 rows
                            float sc5 = sc4;
                            for (int r = 0; r < N_ROWS; r++) {
                                int p1 = k_to_std[(grid[r][1] - s1 + 26) % 26];
                                int p2 = k_to_std[(grid[r][2] - s2 + 26) % 26];
                                int p3 = k_to_std[(grid[r][3] - s3 + 26) % 26];
                                int p4 = k_to_std[(grid[r][4] - s4 + 26) % 26];
                                sc5 += quad[p1][p2][p3][p4];
                            }
                            sc5 /= 2.0f; // avg of two quadgrams per row
                            if (sc5 < -7.8f) continue;
                            
                            for (int s5 = 0; s5 < 26; s5++) {
                                for (int s6 = 0; s6 < 26; s6++) {
                                    total_tested++;
                                    int s[7] = {s0, s1, s2, s3, s4, s5, s6};
                                    
                                    // Full evaluation across all 144 characters
                                    int full_pt[N];
                                    for (int i = 0; i < N; i++) {
                                        int c = i % 7;
                                        int raw = (UNDONE[i] >= 'A' && UNDONE[i] <= 'Z') ? (grid[i/7][c]) : 0;
                                        full_pt[i] = k_to_std[(raw - s[c] + 26) % 26];
                                    }
                                    
                                    float full_sc = 0.0f;
                                    for (int i = 0; i < N - 3; i++) {
                                        full_sc += quad[full_pt[i]][full_pt[i+1]][full_pt[i+2]][full_pt[i+3]];
                                    }
                                    full_sc /= (N - 3);
                                    
                                    if (full_sc > -5.2f) {
                                        #pragma omp critical
                                        {
                                            char pt_str[N+1];
                                            for (int i=0; i<N; i++) pt_str[i] = 'A' + full_pt[i];
                                            pt_str[N] = '\0';
                                            printf("\n*** HIGH SCORE HIT! Score: %.4f ***\n", full_sc);
                                            printf("  Shifts: %d %d %d %d %d %d %d\n", s0, s1, s2, s3, s4, s5, s6);
                                            printf("  PT: %s\n", pt_str);
                                        }
                                    }
                                    if (full_sc > local_best) {
                                        local_best = full_sc;
                                        memcpy(local_shifts, s, sizeof(s));
                                        for (int i=0; i<N; i++) local_pt[i] = 'A' + full_pt[i];
                                        local_pt[N] = '\0';
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
        #pragma omp critical
        {
            if (local_best > global_best) {
                global_best = local_best;
                memcpy(best_shifts, local_shifts, sizeof(best_shifts));
                strcpy(best_pt, local_pt);
            }
        }
    }
    
    double elapsed = omp_get_wtime() - t0;
    printf("Searched in %.2f s (survivors tested: %lld)\n", elapsed, total_tested);
    printf("Global Best Quad: %.4f\n", global_best);
    printf("Best Shifts: %d %d %d %d %d %d %d\n", best_shifts[0], best_shifts[1], best_shifts[2], best_shifts[3], best_shifts[4], best_shifts[5], best_shifts[6]);
    printf("PT: %s\n", best_pt);
}

int main() {
    load_quads();
    printf("Quadgram model loaded.\n");
    search_shifts(1); // KRYPTOS
    search_shifts(0); // STANDARD
    return 0;
}
