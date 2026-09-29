#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>
#include <time.h>

#define N 504

const char *KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
const char *PK10_CT = "UBINFYJSFQXQVRLJJAJDGBXIWKDMAREZTGSHQWRXCHEPCLYSDNGYRRBTCVOZJYVLYWREJTCDOYVEYCJJVZKRMKTRPGVHRWMJSRCSHXZMJEVQKJYJJAYZKDFQBGRSWXATJMEXKFXAXKSIZXOERFESNVCGCNRHEOBCNCBUPXTJJRCIMDMRUVZWRDRRFXAPGPIGSPLILFIZSTDZYOVQGGDFUFZPUOJPJVWREUVRQIYPCEHGYUZUKWTFXELUNOKBANZFTFRMXZSXXQSBGPCWGXPFSCANSVUYLMTZIRCCCJJPBQAEPWVCDIMLOPOXQEGJKVQIVHEFAPQMVCYSQAFKCTYTPAOOJZCWIPGDPAFTINBFFHVXYEQXCEIDJJOUABBAHSWKHGMLJBXDSQEFBBDLTLJPLZPIPPTRGDRZIZPUPYJODOCSOYCZZWTKYWMBQTFMFEQZWVPQYLJTMEYKYBNOPEPUMHCFJSLFWOISWLKFFABTYFQDTEQBDELIEOZQ";

static const int q2_7[7] = {0, 1, 1, 1, 0, 0, 0};
static const int q2_8[8] = {0, 0, 0, 1, 0, 1, 0, 0};
static const int q2_9[9] = {0, 0, 1, 1, 1, 1, 0, 0, 0};

static int c_idx[N];
static int alpha_to_std[26];
static float quad[26][26][26][26];

static inline int crt(int q2, int q13) {
    return (13 * q2 + 14 * q13) % 26;
}

void load_quadgrams() {
    for (int a = 0; a < 26; a++)
        for (int b = 0; b < 26; b++)
            for (int c = 0; c < 26; c++)
                for (int d = 0; d < 26; d++)
                    quad[a][b][c][d] = -9.5f;

    FILE *f = fopen("english_quads.tsv", "r");
    if (!f) exit(1);
    char q[16]; float sc;
    while (fscanf(f, "%s %f", q, &sc) == 2) {
        if (strlen(q) == 4) {
            int a = q[0]-'A', b = q[1]-'A', c = q[2]-'A', d = q[3]-'A';
            if (a>=0 && a<26 && b>=0 && b<26 && c>=0 && c<26 && d>=0 && d<26) {
                quad[a][b][c][d] = sc;
            }
        }
    }
    fclose(f);
}

void init_tables() {
    for (int i = 0; i < 26; i++) {
        alpha_to_std[i] = KRYPTOS[i] - 'A';
    }
    for (int i = 0; i < N; i++) {
        c_idx[i] = strchr(KRYPTOS, PK10_CT[i]) - KRYPTOS;
    }
}

static inline float full_score(const int *pt) {
    float s = 0.0f;
    for (int i = 0; i < N - 3; i++) {
        s += quad[pt[i]][pt[i+1]][pt[i+2]][pt[i+3]];
    }
    return s;
}

int main(int argc, char **argv) {
    init_tables();
    load_quadgrams();

    int restarts = 1000;
    if (argc > 1) restarts = atoi(argv[1]);

    printf("Starting Fast Multi-Restart SA on PK10 (%d restarts)...\n", restarts);

    float global_best_sc = -99999.0f;
    int best_q7[7], best_q8[8], best_q9[9];
    char best_pt[N + 1] = "";

    double t0 = omp_get_wtime();

    #pragma omp parallel
    {
        unsigned int seed = 12345 + omp_get_thread_num() * 7777;
        float local_best_sc = -99999.0f;
        int local_best_q7[7], local_best_q8[8], local_best_q9[9];
        char local_best_pt[N + 1] = "";

        int pt[N];
        int q13_7[7], q13_8[8], q13_9[9];
        int q7[7], q8[8], q9[9];

        #pragma omp for schedule(dynamic, 1)
        for (int r = 0; r < restarts; r++) {
            // Random initialization of 22 free variables
            for (int i = 0; i < 7; i++) q13_7[i] = rand_r(&seed) % 13;
            for (int i = 0; i < 7; i++) q13_8[i] = rand_r(&seed) % 13;
            q13_8[7] = 0; // Gauge
            for (int i = 0; i < 8; i++) q13_9[i] = rand_r(&seed) % 13;
            q13_9[8] = 0; // Gauge

            for (int i = 0; i < 7; i++) q7[i] = crt(q2_7[i], q13_7[i]);
            for (int i = 0; i < 8; i++) q8[i] = crt(q2_8[i], q13_8[i]);
            for (int i = 0; i < 9; i++) q9[i] = crt(q2_9[i], q13_9[i]);

            for (int i = 0; i < N; i++) {
                int k = (q7[i % 7] + q8[i % 8] + q9[i % 9]) % 26;
                pt[i] = alpha_to_std[(c_idx[i] - k + 26) % 26];
            }

            float cur_sc = full_score(pt);

            // SA schedule
            float T = 20.0f;
            float T_end = 0.05f;
            int steps = 15000;
            float decay = powf(T_end / T, 1.0f / steps);

            for (int step = 0; step < steps; step++) {
                // Pick a clock to mutate (0: q7 [7 vars], 1: q8 [7 vars], 2: q9 [8 vars])
                int clk = rand_r(&seed) % 22;
                int which_clk, pos;
                if (clk < 7) {
                    which_clk = 0; pos = clk;
                } else if (clk < 14) {
                    which_clk = 1; pos = clk - 7;
                } else {
                    which_clk = 2; pos = clk - 14;
                }

                int old_v, period;
                if (which_clk == 0) { old_v = q13_7[pos]; period = 7; }
                else if (which_clk == 1) { old_v = q13_8[pos]; period = 8; }
                else { old_v = q13_9[pos]; period = 9; }

                int new_v = (old_v + 1 + rand_r(&seed) % 12) % 13;
                int old_k_elem = (which_clk == 0) ? q7[pos] : ((which_clk == 1) ? q8[pos] : q9[pos]);
                int new_k_elem = crt((which_clk == 0) ? q2_7[pos] : ((which_clk == 1) ? q2_8[pos] : q2_9[pos]), new_v);
                int delta_k = (new_k_elem - old_k_elem + 26) % 26;

                // Compute delta score
                float delta_sc = 0.0f;
                int step_p = period;
                for (int i = pos; i < N; i += step_p) {
                    int old_p = pt[i];
                    // Find old cipher index
                    // pt[i] = alpha_to_std[c_alph]
                    // new p: shift in alphabet
                    // We know p was (c_idx[i] - k) % 26.
                    // With new_k, new p is (old p_kryptos - delta_k) % 26
                    // Let's compute directly:
                    int k_new = ((which_clk == 0 ? new_k_elem : q7[i % 7]) +
                                 (which_clk == 1 ? new_k_elem : q8[i % 8]) +
                                 (which_clk == 2 ? new_k_elem : q9[i % 9])) % 26;
                    int new_p = alpha_to_std[(c_idx[i] - k_new + 26) % 26];

                    // Subtract old quadgrams
                    int q_min = (i - 3 < 0) ? 0 : i - 3;
                    int q_max = (i > N - 4) ? N - 4 : i;
                    for (int q = q_min; q <= q_max; q++) {
                        delta_sc -= quad[pt[q]][pt[q+1]][pt[q+2]][pt[q+3]];
                    }

                    pt[i] = new_p;

                    // Add new quadgrams
                    for (int q = q_min; q <= q_max; q++) {
                        delta_sc += quad[pt[q]][pt[q+1]][pt[q+2]][pt[q+3]];
                    }

                    // Restore temporarily for accurate loop or keep tracked
                    // Note: if multiple positions overlap (e.g. period <= 3, but period >= 7 here!)
                    // Since period >= 7 and quadgrams span 4 characters, NO TWO CHANGED POSITIONS OVERLAP!
                    // Distance between changed positions is >= 7 > 3!
                    // This is an exact guarantee of no collision!
                }

                // Metropolis condition
                if (delta_sc > 0 || (rand_r(&seed) / (float)RAND_MAX) < expf(delta_sc / T)) {
                    // Accept move
                    cur_sc += delta_sc;
                    if (which_clk == 0) { q13_7[pos] = new_v; q7[pos] = new_k_elem; }
                    else if (which_clk == 1) { q13_8[pos] = new_v; q8[pos] = new_k_elem; }
                    else { q13_9[pos] = new_v; q9[pos] = new_k_elem; }
                } else {
                    // Reject: revert pt[i]
                    for (int i = pos; i < N; i += step_p) {
                        int k_old = (q7[i % 7] + q8[i % 8] + q9[i % 9]) % 26;
                        pt[i] = alpha_to_std[(c_idx[i] - k_old + 26) % 26];
                    }
                }

                T *= decay;
            }

            // Greedy polish
            int imp = 1;
            while (imp) {
                imp = 0;
                for (int var = 0; var < 22; var++) {
                    int which_clk = (var < 7) ? 0 : ((var < 14) ? 1 : 2);
                    int pos = (var < 7) ? var : ((var < 14) ? var - 7 : var - 14);
                    int cur_v = (which_clk == 0) ? q13_7[pos] : ((which_clk == 1) ? q13_8[pos] : q13_9[pos]);
                    int best_v = cur_v;
                    float best_delta = 0.0f;

                    for (int test_v = 0; test_v < 13; test_v++) {
                        if (test_v == cur_v) continue;
                        int old_elem = (which_clk == 0) ? q7[pos] : ((which_clk == 1) ? q8[pos] : q9[pos]);
                        int test_elem = crt((which_clk == 0) ? q2_7[pos] : ((which_clk == 1) ? q2_8[pos] : q2_9[pos]), test_v);

                        float d_sc = 0.0f;
                        int step_p = (which_clk == 0) ? 7 : ((which_clk == 1) ? 8 : 9);
                        for (int i = pos; i < N; i += step_p) {
                            int q_min = (i - 3 < 0) ? 0 : i - 3;
                            int q_max = (i > N - 4) ? N - 4 : i;
                            for (int q = q_min; q <= q_max; q++) d_sc -= quad[pt[q]][pt[q+1]][pt[q+2]][pt[q+3]];
                            int k_new = ((which_clk == 0 ? test_elem : q7[i % 7]) +
                                         (which_clk == 1 ? test_elem : q8[i % 8]) +
                                         (which_clk == 2 ? test_elem : q9[i % 9])) % 26;
                            int new_p = alpha_to_std[(c_idx[i] - k_new + 26) % 26];
                            pt[i] = new_p;
                            for (int q = q_min; q <= q_max; q++) d_sc += quad[pt[q]][pt[q+1]][pt[q+2]][pt[q+3]];
                            // Revert pt[i]
                            int k_old = (q7[i % 7] + q8[i % 8] + q9[i % 9]) % 26;
                            pt[i] = alpha_to_std[(c_idx[i] - k_old + 26) % 26];
                        }

                        if (d_sc > best_delta) {
                            best_delta = d_sc;
                            best_v = test_v;
                        }
                    }

                    if (best_v != cur_v) {
                        int new_elem = crt((which_clk == 0) ? q2_7[pos] : ((which_clk == 1) ? q2_8[pos] : q2_9[pos]), best_v);
                        if (which_clk == 0) { q13_7[pos] = best_v; q7[pos] = new_elem; }
                        else if (which_clk == 1) { q13_8[pos] = best_v; q8[pos] = new_elem; }
                        else { q13_9[pos] = best_v; q9[pos] = new_elem; }
                        int step_p = (which_clk == 0) ? 7 : ((which_clk == 1) ? 8 : 9);
                        for (int i = pos; i < N; i += step_p) {
                            int k_now = (q7[i % 7] + q8[i % 8] + q9[i % 9]) % 26;
                            pt[i] = alpha_to_std[(c_idx[i] - k_now + 26) % 26];
                        }
                        cur_sc += best_delta;
                        imp = 1;
                    }
                }
            }

            if (cur_sc > local_best_sc) {
                local_best_sc = cur_sc;
                for (int i = 0; i < 7; i++) local_best_q7[i] = q7[i];
                for (int i = 0; i < 8; i++) local_best_q8[i] = q8[i];
                for (int i = 0; i < 9; i++) local_best_q9[i] = q9[i];
                for (int i = 0; i < N; i++) local_best_pt[i] = 'A' + pt[i];
                local_best_pt[N] = '\0';
            }
        }

        #pragma omp critical
        {
            if (local_best_sc > global_best_sc) {
                global_best_sc = local_best_sc;
                for (int i = 0; i < 7; i++) best_q7[i] = local_best_q7[i];
                for (int i = 0; i < 8; i++) best_q8[i] = local_best_q8[i];
                for (int i = 0; i < 9; i++) best_q9[i] = local_best_q9[i];
                strcpy(best_pt, local_best_pt);

                float avg_sc = global_best_sc / (N - 3);
                printf("\n>>> CANDIDATE HIT! Score = %.4f (avg = %.4f)\n", global_best_sc, avg_sc);
                printf("  q7: ["); for (int i = 0; i < 7; i++) printf("%d%s", best_q7[i], i==6?"]\n":", ");
                printf("  q8: ["); for (int i = 0; i < 8; i++) printf("%d%s", best_q8[i], i==7?"]\n":", ");
                printf("  q9: ["); for (int i = 0; i < 9; i++) printf("%d%s", best_q9[i], i==8?"]\n":", ");
                printf("  Plaintext: %.120s...\n\n", best_pt);
                fflush(stdout);
            }
        }
    }

    double elapsed = omp_get_wtime() - t0;
    printf("\nFinished %d restarts in %.2f s (%.1f restarts/sec)\n", restarts, elapsed, restarts / elapsed);
    printf("Global Best Score = %.4f (avg = %.4f)\n", global_best_sc, global_best_sc / (N - 3));
    printf("Plaintext:\n%s\n", best_pt);

    return 0;
}
