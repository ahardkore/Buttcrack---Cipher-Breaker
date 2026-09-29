#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <time.h>
#include <omp.h>

static float quad[26][26][26][26];

void load_quadgrams() {
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
const char *STD = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";
const char *PK8_CT = "COPVEJJVSVURTVIPYOTPLHGBTMAUCCPESIWIGZBWSJPKTRPUEKQFIFCLHMXTHIMHWOYIGURBOMPARCVXVKBDDVBVHDRHGCVNWWVLBMYWMWHICFIXZWBVZYCQGNOGJGUMLNPUTHQCXNWPQZOIRJZGSWVPY";
const char *PK9_CT = "KSYAWFEYYOISZGEUFBLYATAIBYFAQBQYYVDWJKLJXMYIEPIFVHPQNHZGSUHUUDXLEHRHUMALHEGLHXSJMUXGNUIVBXGUJHZRZGUSVHMLSCTSUQXHSUMQQIFUQGKHJGUQGLHDKEWSKAMHIJXD";

static const int N = 144;

static inline float eval_full(const int *p8, const int *p9) {
    float sc = 0.0f;
    for (int i = 0; i < N - 3; i++) {
        sc += quad[p8[i]][p8[i+1]][p8[i+2]][p8[i+3]];
        sc += quad[p9[i]][p9[i+1]][p9[i+2]][p9[i+3]];
    }
    return sc / (2.0f * (N - 3));
}

int main(int argc, char **argv) {
    load_quadgrams();

    int d_std[144], d_k[144];
    int k_to_std[26], s_to_std[26];
    for (int i=0; i<26; i++) {
        k_to_std[i] = KRYPTOS[i] - 'A';
        s_to_std[i] = i;
    }
    for (int i = 0; i < N; i++) {
        d_std[i] = (PK9_CT[i] - PK8_CT[i] + 26) % 26;
        int idx8 = strchr(KRYPTOS, PK8_CT[i]) - KRYPTOS;
        int idx9 = strchr(KRYPTOS, PK9_CT[i]) - KRYPTOS;
        d_k[i] = (idx9 - idx8 + 26) % 26;
    }

    printf("Starting Fast Dual-Stream Depth-Two Annealing on (C9 - C8)...\n");

    // Test widths W dividing 144
    int widths[] = {6, 8, 9, 12, 16, 18, 24};
    int num_w = sizeof(widths) / sizeof(widths[0]);

    float global_best_sc = -999.0f;
    char global_p8[150] = "", global_p9[150] = "";

    for (int m = 0; m < 2; m++) {
        const char *mname = (m == 0) ? "STD" : "KRYPTOS";
        int *D = (m == 0) ? d_std : d_k;
        int *a_to_std = (m == 0) ? s_to_std : k_to_std;

        for (int wi = 0; wi < num_w; wi++) {
            int W = widths[wi];
            int H = N / W;

            // Simple columnar transposition: pi maps plaintext pos to I9 pos
            // Row-write, col-read: char at row r, col c has plaintext index r*W + c
            // Written into column c, so I9 index is c*H + r
            int pi[144], pi_inv[144];
            for (int r = 0; r < H; r++) {
                for (int c = 0; c < W; c++) {
                    int pt_idx = r * W + c;
                    int i9_idx = c * H + r;
                    pi[pt_idx] = i9_idx;
                    pi_inv[i9_idx] = pt_idx;
                }
            }

            #pragma omp parallel
            {
                unsigned int seed = 12345 + omp_get_thread_num() * 7777 + wi * 101 + m * 53;
                int p8[144], p9[144];
                int p8_std[144], p9_std[144];

                #pragma omp for schedule(dynamic, 10)
                for (int restart = 0; restart < 500; restart++) {
                    for (int i = 0; i < N; i++) p8[i] = rand_r(&seed) % 26;
                    for (int i = 0; i < N; i++) {
                        int i9 = (p8[pi[i]] + D[pi[i]]) % 26;
                        p9[i] = i9;
                        p8_std[i] = a_to_std[p8[i]];
                        p9_std[i] = a_to_std[p9[i]];
                    }

                    float cur_sc = eval_full(p8_std, p9_std);

                    float T = 5.0f;
                    float cooling = 0.999f;

                    for (int step = 0; step < 10000 && T > 0.05f; step++) {
                        T *= cooling;
                        int pos = rand_r(&seed) % N;
                        int old_val = p8[pos];
                        int new_val = (old_val + 1 + rand_r(&seed) % 25) % 26;

                        p8[pos] = new_val;
                        p8_std[pos] = a_to_std[new_val];

                        int p9_pos = pi_inv[pos];
                        int old_p9 = p9[p9_pos];
                        int new_p9 = (new_val + D[pos]) % 26;
                        p9[p9_pos] = new_p9;
                        p9_std[p9_pos] = a_to_std[new_p9];

                        float new_sc = eval_full(p8_std, p9_std);
                        float delta = new_sc - cur_sc;

                        if (delta > 0 || (float)rand_r(&seed) / RAND_MAX < expf(delta / T)) {
                            cur_sc = new_sc;
                        } else {
                            p8[pos] = old_val;
                            p8_std[pos] = a_to_std[old_val];
                            p9[p9_pos] = old_p9;
                            p9_std[p9_pos] = a_to_std[old_p9];
                        }
                    }

                    if (cur_sc > global_best_sc) {
                        #pragma omp critical
                        {
                            if (cur_sc > global_best_sc) {
                                global_best_sc = cur_sc;
                                for (int i = 0; i < N; i++) {
                                    global_p8[i] = 'A' + p8_std[i];
                                    global_p9[i] = 'A' + p9_std[i];
                                }
                                global_p8[N] = '\0';
                                global_p9[N] = '\0';
                                printf("[%s W=%2d] sc=%6.4f\n  P8: %s\n  P9: %s\n",
                                       mname, W, global_best_sc, global_p8, global_p9);
                            }
                        }
                    }
                }
            }
        }
    }
    printf("Completed dual-stream depth-two search. Best score = %6.4f\n", global_best_sc);
    return 0;
}
