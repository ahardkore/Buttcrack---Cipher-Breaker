#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>
#include <time.h>

#define N 144

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

    printf("Testing direct Dual-Clock (4, 7) Quagmire III and Vigenere on PK9...\n");

    // Mode 0: Quagmire III (KRYPTOS alphabet)
    // Mode 1: Standard Vigenere (A-Z alphabet)
    for (int mode = 0; mode < 2; mode++) {
        printf("\n--- Mode: %s ---\n", mode == 0 ? "Quagmire III (KRYPTOS)" : "Standard Vigenere (A-Z)");

        float best_sc = -999.0f;
        int best_q4[4], best_q7[7];
        char best_pt[150] = "";

        // q4[0] can be fixed to 0 as gauge
        // q4 has 26^3 = 17,576 possibilities
        // q7 has 26^7 possibilities
        // We can run coordinate descent / 2-opt from 5,000 random starts
        #pragma omp parallel
        {
            float loc_best_sc = -999.0f;
            int loc_q4[4], loc_q7[7];
            char loc_pt[150] = "";
            unsigned int seed = 12345 + omp_get_thread_num() * 777;

            #pragma omp for schedule(dynamic, 100)
            for (int r = 0; r < 5000; r++) {
                int q4[4], q7[7];
                q4[0] = 0;
                for (int i = 1; i < 4; i++) q4[i] = rand_r(&seed) % 26;
                for (int i = 0; i < 7; i++) q7[i] = rand_r(&seed) % 26;

                int pt[N];
                for (int t = 0; t < N; t++) {
                    int k = (q4[t % 4] + q7[t % 7]) % 26;
                    if (mode == 0) {
                        int p_kr = (ct_kr[t] - k + 26) % 26;
                        pt[t] = k2std[p_kr];
                    } else {
                        pt[t] = (ct_std[t] - k + 26) % 26;
                    }
                }
                float cur_sc = score_pt(pt);

                // Coordinate ascent
                int improved = 1;
                while (improved) {
                    improved = 0;
                    // optimize q4
                    for (int i = 1; i < 4; i++) {
                        int old_v = q4[i];
                        int best_v = old_v;
                        float best_s = cur_sc;
                        for (int v = 0; v < 26; v++) {
                            if (v == old_v) continue;
                            q4[i] = v;
                            for (int t = 0; t < N; t++) {
                                int k = (q4[t % 4] + q7[t % 7]) % 26;
                                if (mode == 0) pt[t] = k2std[(ct_kr[t] - k + 26) % 26];
                                else pt[t] = (ct_std[t] - k + 26) % 26;
                            }
                            float s = score_pt(pt);
                            if (s > best_s) { best_s = s; best_v = v; }
                        }
                        q4[i] = best_v;
                        if (best_v != old_v) { cur_sc = best_s; improved = 1; }
                    }

                    // optimize q7
                    for (int i = 0; i < 7; i++) {
                        int old_v = q7[i];
                        int best_v = old_v;
                        float best_s = cur_sc;
                        for (int v = 0; v < 26; v++) {
                            if (v == old_v) continue;
                            q7[i] = v;
                            for (int t = 0; t < N; t++) {
                                int k = (q4[t % 4] + q7[t % 7]) % 26;
                                if (mode == 0) pt[t] = k2std[(ct_kr[t] - k + 26) % 26];
                                else pt[t] = (ct_std[t] - k + 26) % 26;
                            }
                            float s = score_pt(pt);
                            if (s > best_s) { best_s = s; best_v = v; }
                        }
                        q7[i] = best_v;
                        if (best_v != old_v) { cur_sc = best_s; improved = 1; }
                    }
                }

                if (cur_sc > loc_best_sc) {
                    loc_best_sc = cur_sc;
                    memcpy(loc_q4, q4, 4 * sizeof(int));
                    memcpy(loc_q7, q7, 7 * sizeof(int));
                    for (int t = 0; t < N; t++) {
                        int k = (q4[t % 4] + q7[t % 7]) % 26;
                        if (mode == 0) loc_pt[t] = 'A' + k2std[(ct_kr[t] - k + 26) % 26];
                        else loc_pt[t] = 'A' + (ct_std[t] - k + 26) % 26;
                    }
                    loc_pt[N] = '\0';
                }
            }

            #pragma omp critical
            {
                if (loc_best_sc > best_sc) {
                    best_sc = loc_best_sc;
                    memcpy(best_q4, loc_q4, 4 * sizeof(int));
                    memcpy(best_q7, loc_q7, 7 * sizeof(int));
                    strcpy(best_pt, loc_pt);
                }
            }
        }

        printf("Best Score: %.4f\n", best_sc);
        printf("q4: [%d, %d, %d, %d]\n", best_q4[0], best_q4[1], best_q4[2], best_q4[3]);
        printf("q7: [%d, %d, %d, %d, %d, %d, %d]\n", best_q7[0], best_q7[1], best_q7[2], best_q7[3], best_q7[4], best_q7[5], best_q7[6]);
        printf("PT: %s\n", best_pt);
    }

    return 0;
}
