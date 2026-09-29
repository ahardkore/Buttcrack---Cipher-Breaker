#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>
#include <time.h>

#define N 144
#define P 28

static float quad[26][26][26][26];

void load_quads() {
    for (int a=0; a<26; a++)
        for (int b=0; b<26; b++)
            for (int c=0; c<26; c++)
                for (int d=0; d<26; d++)
                    quad[a][b][c][d] = -9.5f;
    FILE *f = fopen("english_quads.tsv", "r");
    if (!f) { printf("Cannot open english_quads.tsv\n"); exit(1); }
    char q[16]; float sc;
    while (fscanf(f, "%s\t%f", q, &sc) == 2) {
        if (strlen(q) == 4) {
            int a = q[0]-'A', b = q[1]-'A', c = q[2]-'A', d = q[3]-'A';
            if (a>=0 && a<26 && b>=0 && b<26 && c>=0 && c<26 && d>=0 && d<26) {
                quad[a][b][c][d] = sc;
            }
        }
    }
    fclose(f);
}

const char *KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
const char *PK9_CT = "KSYAWFEYYOISZGEUFBLYATAIBYFAQBQYYVDWJKLJXMYIEPIFVHPQNHZGSUHUUDXLEHRHUMALHEGLHXSJMUXGNUIVBXGUJHZRZGUSVHMLSCTSUQXHSUMQQIFUQGKHJGUQGLHDKEWSKAMHIJXD";

static int ct_kr[N];
static int ct_std[N];
static int k2std[26];
static int hpos[256];

static inline float score_pt(const int *pt_std) {
    float s = 0.0f;
    for (int i = 0; i < N - 3; i++) {
        s += quad[pt_std[i]][pt_std[i+1]][pt_std[i+2]][pt_std[i+3]];
    }
    return s / (N - 3);
}

void compute_pt(const int *shifts, int *pt_std, int mode) {
    for (int t = 0; t < N; t++) {
        int sh = shifts[t % P];
        if (mode == 0) {
            int p_kr = (ct_kr[t] - sh + 26) % 26;
            pt_std[t] = k2std[p_kr];
        } else {
            pt_std[t] = (ct_std[t] - sh + 26) % 26;
        }
    }
}

float solve_restarts(int *shifts, int mode, unsigned int *seed) {
    int pt[N];
    compute_pt(shifts, pt, mode);
    float cur_sc = score_pt(pt);

    // Fast SA
    float T = 2.5f;
    float cooling = 0.999f;
    for (int step = 0; step < 4000; step++) {
        T *= cooling;
        int col = rand_r(seed) % P;
        int old_s = shifts[col];
        int new_s = (old_s + 1 + rand_r(seed) % 25) % 26;
        shifts[col] = new_s;

        compute_pt(shifts, pt, mode);
        float sc = score_pt(pt);
        float delta = sc - cur_sc;

        if (delta > 0 || (float)rand_r(seed) / RAND_MAX < expf(delta / T)) {
            cur_sc = sc;
        } else {
            shifts[col] = old_s;
        }
    }

    // 1-Opt Greedy Polish
    int improved = 1;
    int passes = 0;
    while (improved && passes < 15) {
        improved = 0;
        passes++;
        for (int col = 0; col < P; col++) {
            int old_s = shifts[col];
            int best_s = old_s;
            float best_sc = cur_sc;

            for (int s = 0; s < 26; s++) {
                if (s == old_s) continue;
                shifts[col] = s;
                compute_pt(shifts, pt, mode);
                float sc = score_pt(pt);
                if (sc > best_sc) {
                    best_sc = sc;
                    best_s = s;
                }
            }
            shifts[col] = best_s;
            if (best_s != old_s) {
                cur_sc = best_sc;
                improved = 1;
            }
        }
    }

    // 2-Opt Polish (coupled adjacent and near columns)
    improved = 1;
    passes = 0;
    while (improved && passes < 8) {
        improved = 0;
        passes++;
        for (int c1 = 0; c1 < P - 1; c1++) {
            for (int c2 = c1 + 1; c2 < P; c2++) {
                // Focus on adjacent or related columns
                if (c2 - c1 > 4 && c2 - c1 != 7 && c2 - c1 != 14 && c2 - c1 != 21) continue;

                int old1 = shifts[c1];
                int old2 = shifts[c2];
                int best_d = 0;
                float best_sc = cur_sc;

                for (int d = 1; d < 26; d++) {
                    shifts[c1] = (old1 + d) % 26;
                    shifts[c2] = (old2 - d + 26) % 26;
                    compute_pt(shifts, pt, mode);
                    float sc = score_pt(pt);
                    if (sc > best_sc) {
                        best_sc = sc;
                        best_d = d;
                    }
                }

                if (best_d != 0) {
                    shifts[c1] = (old1 + best_d) % 26;
                    shifts[c2] = (old2 - best_d + 26) % 26;
                    cur_sc = best_sc;
                    improved = 1;
                } else {
                    shifts[c1] = old1;
                    shifts[c2] = old2;
                }
            }
        }
    }

    return cur_sc;
}

int main() {
    load_quads();

    for (int i = 0; i < 26; i++) {
        hpos[(unsigned char)KRYPTOS[i]] = i;
        k2std[i] = KRYPTOS[i] - 'A';
    }
    for (int i = 0; i < N; i++) {
        ct_kr[i] = hpos[(unsigned char)PK9_CT[i]];
        ct_std[i] = PK9_CT[i] - 'A';
    }

    printf("Starting Period-28 Quagmire III / Vigenere SA + 1-Opt + 2-Opt Solver on PK9...\n");

    for (int mode = 0; mode < 2; mode++) {
        printf("\n=========================================\n");
        printf("Mode: %s\n", mode == 0 ? "Quagmire III (KRYPTOS)" : "Standard Vigenere (A-Z)");
        printf("=========================================\n");

        double t0 = omp_get_wtime();
        float global_best_sc = -999.0f;
        char global_best_pt[160] = "";
        int best_shifts[P];

        #define RESTARTS 2000

        #pragma omp parallel
        {
            float loc_best = -999.0f;
            char loc_pt[160] = "";
            int loc_shifts[P];
            unsigned int seed = 45678 + omp_get_thread_num() * 3333;

            #pragma omp for schedule(dynamic, 10)
            for (int r = 0; r < RESTARTS; r++) {
                int cur_shifts[P];
                for (int i = 0; i < P; i++) cur_shifts[i] = rand_r(&seed) % 26;

                float sc = solve_restarts(cur_shifts, mode, &seed);

                if (sc > -5.3f) {
                    #pragma omp critical
                    {
                        int pt[N];
                        compute_pt(cur_shifts, pt, mode);
                        char pt_str[N + 1];
                        for (int t = 0; t < N; t++) pt_str[t] = 'A' + pt[t];
                        pt_str[N] = '\0';
                        printf(">>> BREAKTHROUGH CANDIDATE! Score: %.4f <<<\n", sc);
                        printf("  PT: %s\n", pt_str);
                        printf("  Shifts: ");
                        for (int i = 0; i < P; i++) printf("%d ", cur_shifts[i]);
                        printf("\n\n");
                    }
                }

                if (sc > loc_best) {
                    loc_best = sc;
                    memcpy(loc_shifts, cur_shifts, P * sizeof(int));
                    int pt[N];
                    compute_pt(cur_shifts, pt, mode);
                    for (int t = 0; t < N; t++) loc_pt[t] = 'A' + pt[t];
                    loc_pt[N] = '\0';
                }
            }

            #pragma omp critical
            {
                if (loc_best > global_best_sc) {
                    global_best_sc = loc_best;
                    memcpy(best_shifts, loc_shifts, P * sizeof(int));
                    strcpy(global_best_pt, loc_pt);
                }
            }
        }

        double elapsed = omp_get_wtime() - t0;
        printf("Completed %d restarts in %.3f s\n", RESTARTS, elapsed);
        printf("Global Best Score: %.4f\n", global_best_sc);
        printf("Shifts: ");
        for (int i = 0; i < P; i++) printf("%d ", best_shifts[i]);
        printf("\nPT: %s\n", global_best_pt);
    }

    return 0;
}
