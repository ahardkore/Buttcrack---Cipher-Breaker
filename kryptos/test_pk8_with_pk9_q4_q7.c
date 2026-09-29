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
const char *PK8_CT = "COPVEJJVSVURTVIPYOTPLHGBTMAUCCPESIWIGZBWSJPKTRPUEKQFIFCLHMXTHIMHWOYIGURBOMPARCVXVKBDDVBVHDRHGCVNWWVLBMYWMWHICFIXZWBVZYCQGNOGJGUMLNPUTHQCXNWPQZOIRJZGSWVPY";

static int ct_kr[N];
static int k2std[26];
static int hpos[256];

// Mod-13 base schedule for Clock 7
static const int s13[7] = {0, 2, 9, 10, 10, 6, 7};

static inline float score_pt(const int *pt_std) {
    float s = 0.0f;
    for (int i = 0; i < N - 3; i++) {
        s += quad[pt_std[i]][pt_std[i+1]][pt_std[i+2]][pt_std[i+3]];
    }
    return s / (N - 3);
}

// Fast coordinate descent to optimize q5 and q6 on stream Y
float optimize_q5_q6(const int *Y, int *best_q5, int *best_q6, int *best_pt_std) {
    int q5[5] = {0};
    int q6[6] = {0};

    int pt_kr[N], pt_std[N];
    for (int t = 0; t < N; t++) {
        pt_kr[t] = Y[t];
        pt_std[t] = k2std[pt_kr[t]];
    }
    float cur_sc = score_pt(pt_std);

    int improved = 1;
    int passes = 0;
    while (improved && passes < 12) {
        improved = 0;
        passes++;

        // Optimize q5[0..4]
        for (int j = 0; j < 5; j++) {
            int old_v = q5[j];
            int best_v = old_v;
            float best_s = cur_sc;

            for (int v = 0; v < 26; v++) {
                if (v == old_v) continue;
                for (int t = j; t < N; t += 5) {
                    int k = (v + q6[t % 6]) % 26;
                    int p = (Y[t] - k + 26) % 26;
                    pt_std[t] = k2std[p];
                }
                float s = score_pt(pt_std);
                if (s > best_s) {
                    best_s = s;
                    best_v = v;
                }
            }
            q5[j] = best_v;
            for (int t = j; t < N; t += 5) {
                int k = (q5[j] + q6[t % 6]) % 26;
                int p = (Y[t] - k + 26) % 26;
                pt_std[t] = k2std[p];
            }
            if (best_v != old_v) {
                cur_sc = best_s;
                improved = 1;
            }
        }

        // Optimize q6[0..5]
        for (int j = 0; j < 6; j++) {
            int old_v = q6[j];
            int best_v = old_v;
            float best_s = cur_sc;

            for (int v = 0; v < 26; v++) {
                if (v == old_v) continue;
                for (int t = j; t < N; t += 6) {
                    int k = (q5[t % 5] + v) % 26;
                    int p = (Y[t] - k + 26) % 26;
                    pt_std[t] = k2std[p];
                }
                float s = score_pt(pt_std);
                if (s > best_s) {
                    best_s = s;
                    best_v = v;
                }
            }
            q6[j] = best_v;
            for (int t = j; t < N; t += 6) {
                int k = (q5[t % 5] + q6[j]) % 26;
                int p = (Y[t] - k + 26) % 26;
                pt_std[t] = k2std[p];
            }
            if (best_v != old_v) {
                cur_sc = best_s;
                improved = 1;
            }
        }
    }

    for (int j = 0; j < 5; j++) best_q5[j] = q5[j];
    for (int j = 0; j < 6; j++) best_q6[j] = q6[j];
    for (int t = 0; t < N; t++) best_pt_std[t] = pt_std[t];

    return cur_sc;
}

int main() {
    load_quads();

    for (int i = 0; i < 26; i++) {
        hpos[(unsigned char)KRYPTOS[i]] = i;
        k2std[i] = KRYPTOS[i] - 'A';
    }
    for (int i = 0; i < N; i++) ct_kr[i] = hpos[(unsigned char)PK8_CT[i]];

    printf("Starting Joint (q4, q7) -> (q5, q6) Solver on PK8...\n");
    double t0 = omp_get_wtime();

    float global_best_sc = -999.0f;
    char global_best_pt[160] = "";
    int best_q4[4], best_q5[5], best_q6[6], best_q7[7];

    // For candidate masks of q7:
    // Focus on masks that gave high IoC in PK9: masks 97, 116, 11, 43, 84, 14, 113, 30
    int test_masks[] = {97, 116, 11, 43, 84, 14, 113, 30, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10};
    int n_masks = sizeof(test_masks) / sizeof(test_masks[0]);

    #pragma omp parallel
    {
        float local_best_sc = -999.0f;
        char local_best_pt[160] = "";
        int loc_q4[4], loc_q5[5], loc_q6[6], loc_q7[7];
        unsigned int seed = 12345 + omp_get_thread_num() * 1007;

        #pragma omp for schedule(dynamic, 1)
        for (int mi = 0; mi < n_masks; mi++) {
            int mask = test_masks[mi];
            int q7_base[7];
            for (int j = 0; j < 7; j++) {
                int b = (mask >> j) & 1;
                q7_base[j] = (s13[j] + 13 * b) % 26;
            }

            // Test 7 phase shifts of q7
            for (int phase = 0; phase < 7; phase++) {
                int q7[7];
                for (int j = 0; j < 7; j++) q7[j] = q7_base[(j + phase) % 7];

                // Random sampling or systematic grid over q4[0..3]
                // 10,000 random q4 vectors per mask & phase
                for (int sample = 0; sample < 1000; sample++) {
                    int q4[4];
                    q4[0] = 0; // gauge
                    q4[1] = rand_r(&seed) % 26;
                    q4[2] = rand_r(&seed) % 26;
                    q4[3] = rand_r(&seed) % 26;

                    // Compute Y[t]
                    int Y[N];
                    for (int t = 0; t < N; t++) {
                        int k = (q4[t % 4] + q7[t % 7]) % 26;
                        Y[t] = (ct_kr[t] - k + 26) % 26;
                    }

                    int cur_q5[5], cur_q6[6], cur_pt_std[N];
                    float sc = optimize_q5_q6(Y, cur_q5, cur_q6, cur_pt_std);

                    if (sc > -5.8f) {
                        #pragma omp critical
                        {
                            char pt_str[N + 1];
                            for (int t = 0; t < N; t++) pt_str[t] = 'A' + cur_pt_std[t];
                            pt_str[N] = '\0';
                            printf(">>> HIGH SCORE! Score: %.4f | Mask: %d | Phase: %d <<<\n", sc, mask, phase);
                            printf("  PT: %s\n\n", pt_str);
                        }
                    }

                    if (sc > local_best_sc) {
                        local_best_sc = sc;
                        memcpy(loc_q4, q4, 4 * sizeof(int));
                        memcpy(loc_q5, cur_q5, 5 * sizeof(int));
                        memcpy(loc_q6, cur_q6, 6 * sizeof(int));
                        memcpy(loc_q7, q7, 7 * sizeof(int));
                        for (int t = 0; t < N; t++) local_best_pt[t] = 'A' + cur_pt_std[t];
                        local_best_pt[N] = '\0';
                    }
                }
            }
        }

        #pragma omp critical
        {
            if (local_best_sc > global_best_sc) {
                global_best_sc = local_best_sc;
                memcpy(best_q4, loc_q4, 4 * sizeof(int));
                memcpy(best_q5, loc_q5, 5 * sizeof(int));
                memcpy(best_q6, loc_q6, 6 * sizeof(int));
                memcpy(best_q7, loc_q7, 7 * sizeof(int));
                strcpy(global_best_pt, local_best_pt);
            }
        }
    }

    double elapsed = omp_get_wtime() - t0;
    printf("Evaluated in %.3f seconds!\n", elapsed);
    printf("Global Best Score: %.4f\n", global_best_sc);
    printf("q4: [%d, %d, %d, %d]\n", best_q4[0], best_q4[1], best_q4[2], best_q4[3]);
    printf("q5: [%d, %d, %d, %d, %d]\n", best_q5[0], best_q5[1], best_q5[2], best_q5[3], best_q5[4]);
    printf("q6: [%d, %d, %d, %d, %d, %d]\n", best_q6[0], best_q6[1], best_q6[2], best_q6[3], best_q6[4], best_q6[5]);
    printf("q7: [%d, %d, %d, %d, %d, %d, %d]\n", best_q7[0], best_q7[1], best_q7[2], best_q7[3], best_q7[4], best_q7[5], best_q7[6]);
    printf("PT: %s\n", global_best_pt);

    return 0;
}
