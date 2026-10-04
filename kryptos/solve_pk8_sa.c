#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <time.h>
#include <omp.h>

static float qgram[26][26][26][26];

void load_qgrams() {
    FILE *f = fopen("english_quads.tsv", "r");
    if (!f) {
        fprintf(stderr, "Cannot open english_quads.tsv\n");
        exit(1);
    }
    for (int a = 0; a < 26; a++)
        for (int b = 0; b < 26; b++)
            for (int c = 0; c < 26; c++)
                for (int d = 0; d < 26; d++)
                    qgram[a][b][c][d] = -9.5f;

    char line[128];
    while (fgets(line, sizeof(line), f)) {
        char gram[5];
        float score;
        /* english_quads.tsv stores precomputed log scores, not raw counts. */
        if (sscanf(line, "%4s %f", gram, &score) == 2) {
            int a = gram[0] - 'A';
            int b = gram[1] - 'A';
            int c = gram[2] - 'A';
            int d = gram[3] - 'A';
            if (a >= 0 && a < 26 && b >= 0 && b < 26 && c >= 0 && c < 26 && d >= 0 && d < 26)
                qgram[a][b][c][d] = score;
        }
    }
    fclose(f);
}

const char *KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
const char *STD = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";
const char *PK8_CT = "COPVEJJVSVURTVIPYOTPLHGBTMAUCCPESIWIGZBWSJPKTRPUEKQFIFCLHMXTHIMHWOYIGURBOMPARCVXVKBDDVBVHDRHGCVNWWVLBMYWMWHICFIXZWBVZYCQGNOGJGUMLNPUTHQCXNWPQZOIRJZGSWVPY";

static inline float score_text(const int *pt, int len) {
    float sc = 0;
    for (int i = 0; i < len - 3; i++) {
        sc += qgram[pt[i]][pt[i+1]][pt[i+2]][pt[i+3]];
    }
    return sc;
}

void solve_sa(int use_kryptos, int is_beaufort, int num_restarts) {
    int N = strlen(PK8_CT);
    const char *alpha = use_kryptos ? KRYPTOS : STD;
    int c_idx[200];
    int alpha_to_std[26];
    for (int i = 0; i < 26; i++) alpha_to_std[i] = alpha[i] - 'A';
    for (int i = 0; i < N; i++) c_idx[i] = strchr(alpha, PK8_CT[i]) - alpha;

    float global_best_sc = -99999.0f;
    char global_best_pt[200];

    printf("Starting SA on PK8: %s %s, %d restarts...\n",
           use_kryptos ? "KRYPTOS" : "STD",
           is_beaufort ? "Beaufort" : "Vigenere",
           num_restarts);

    #pragma omp parallel
    {
        unsigned int seed = 12345 + omp_get_thread_num() * 9999 + use_kryptos * 37 + is_beaufort * 17;
        int q4[4], q5[5], q6[6], q7[7];
        int pt_alpha[200], pt_std[200];

        #pragma omp for
        for (int r = 0; r < num_restarts; r++) {
            for (int i = 0; i < 4; i++) q4[i] = rand_r(&seed) % 26;
            for (int i = 0; i < 5; i++) q5[i] = rand_r(&seed) % 26;
            for (int i = 0; i < 6; i++) q6[i] = rand_r(&seed) % 26;
            for (int i = 0; i < 7; i++) q7[i] = rand_r(&seed) % 26;

            for (int i = 0; i < N; i++) {
                int k = (q4[i % 4] + q5[i % 5] + q6[i % 6] + q7[i % 7]) % 26;
                int p = is_beaufort ? ((k - c_idx[i] + 26) % 26) : ((c_idx[i] - k + 26) % 26);
                pt_alpha[i] = p;
                pt_std[i] = alpha_to_std[p];
            }
            float cur_sc = score_text(pt_std, N);

            // Simulated Annealing
            float T = 15.0f;
            float T_min = 0.05f;
            float cooling = 0.999f;
            int steps = 5000;

            for (int step = 0; step < steps && T > T_min; step++) {
                T *= cooling;
                int clock_choice = rand_r(&seed) % 4;
                int idx, old_val, new_val;
                if (clock_choice == 0) {
                    idx = rand_r(&seed) % 4;
                    old_val = q4[idx];
                    new_val = (old_val + 1 + rand_r(&seed) % 25) % 26;
                    q4[idx] = new_val;
                } else if (clock_choice == 1) {
                    idx = rand_r(&seed) % 5;
                    old_val = q5[idx];
                    new_val = (old_val + 1 + rand_r(&seed) % 25) % 26;
                    q5[idx] = new_val;
                } else if (clock_choice == 2) {
                    idx = rand_r(&seed) % 6;
                    old_val = q6[idx];
                    new_val = (old_val + 1 + rand_r(&seed) % 25) % 26;
                    q6[idx] = new_val;
                } else {
                    idx = rand_r(&seed) % 7;
                    old_val = q7[idx];
                    new_val = (old_val + 1 + rand_r(&seed) % 25) % 26;
                    q7[idx] = new_val;
                }

                // recompute pt
                for (int i = 0; i < N; i++) {
                    int k = (q4[i % 4] + q5[i % 5] + q6[i % 6] + q7[i % 7]) % 26;
                    int p = is_beaufort ? ((k - c_idx[i] + 26) % 26) : ((c_idx[i] - k + 26) % 26);
                    pt_std[i] = alpha_to_std[p];
                }
                float new_sc = score_text(pt_std, N);
                float delta = new_sc - cur_sc;

                if (delta > 0 || (expf(delta / T) > ((float)rand_r(&seed) / RAND_MAX))) {
                    cur_sc = new_sc;
                } else {
                    // revert
                    if (clock_choice == 0) q4[idx] = old_val;
                    else if (clock_choice == 1) q5[idx] = old_val;
                    else if (clock_choice == 2) q6[idx] = old_val;
                    else q7[idx] = old_val;
                }
            }

            // Coordinate descent polish
            int improved = 1;
            int iter = 0;
            while (improved && iter < 15) {
                improved = 0;
                iter++;
                for (int clock_choice = 0; clock_choice < 4; clock_choice++) {
                    int mod = (clock_choice == 0) ? 4 : (clock_choice == 1 ? 5 : (clock_choice == 2 ? 6 : 7));
                    int *q = (clock_choice == 0) ? q4 : (clock_choice == 1 ? q5 : (clock_choice == 2 ? q6 : q7));
                    for (int j = 0; j < mod; j++) {
                        int best_val = q[j];
                        float best_val_sc = cur_sc;
                        int orig_val = q[j];

                        for (int cand = 0; cand < 26; cand++) {
                            if (cand == orig_val) continue;
                            q[j] = cand;
                            for (int i = j; i < N; i += mod) {
                                int k = (q4[i % 4] + q5[i % 5] + q6[i % 6] + q7[i % 7]) % 26;
                                int p = is_beaufort ? ((k - c_idx[i] + 26) % 26) : ((c_idx[i] - k + 26) % 26);
                                pt_std[i] = alpha_to_std[p];
                            }
                            float sc = score_text(pt_std, N);
                            if (sc > best_val_sc) {
                                best_val_sc = sc;
                                best_val = cand;
                            }
                        }
                        if (best_val != orig_val) {
                            q[j] = best_val;
                            cur_sc = best_val_sc;
                            improved = 1;
                        }
                        q[j] = best_val;
                        for (int i = j; i < N; i += mod) {
                            int k = (q4[i % 4] + q5[i % 5] + q6[i % 6] + q7[i % 7]) % 26;
                            int p = is_beaufort ? ((k - c_idx[i] + 26) % 26) : ((c_idx[i] - k + 26) % 26);
                            pt_std[i] = alpha_to_std[p];
                        }
                    }
                }
            }

            #pragma omp critical
            {
                if (cur_sc > global_best_sc) {
                    global_best_sc = cur_sc;
                    for (int i = 0; i < N; i++) {
                        int k = (q4[i % 4] + q5[i % 5] + q6[i % 6] + q7[i % 7]) % 26;
                        int p = is_beaufort ? ((k - c_idx[i] + 26) % 26) : ((c_idx[i] - k + 26) % 26);
                        global_best_pt[i] = 'A' + alpha_to_std[p];
                    }
                    global_best_pt[N] = '\0';
                    printf("Restart %5d: Score = %7.2f (avg %6.4f) | %s\n",
                           r, cur_sc, cur_sc / (N - 3), global_best_pt);
                    printf("  q4: "); for (int i=0; i<4; i++) printf("%c", alpha[q4[i]]);
                    printf(" | q5: "); for (int i=0; i<5; i++) printf("%c", alpha[q5[i]]);
                    printf(" | q6: "); for (int i=0; i<6; i++) printf("%c", alpha[q6[i]]);
                    printf(" | q7: "); for (int i=0; i<7; i++) printf("%c", alpha[q7[i]]);
                    printf("\n");
                    fflush(stdout);
                }
            }
        }
    }
}

int main() {
    load_qgrams();
    solve_sa(1, 0, 1000); // KRYPTOS Vig
    solve_sa(0, 0, 1000); // STD Vig
    return 0;
}
