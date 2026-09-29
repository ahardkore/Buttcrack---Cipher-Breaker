#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>
#include <time.h>

#define N 504

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
const char *PK10_CT = "UBINFYJSFQXQVRLJJAJDGBXIWKDMAREZTGSHQWRXCHEPCLYSDNGYRRBTCVOZJYVLYWREJTCDOYVEYCJJVZKRMKTRPGVHRWMJSRCSHXZMJEVQKJYJJAYZKDFQBGRSWXATJMEXKFXAXKSIZXOERFESNVCGCNRHEOBCNCBUPXTJJRCIMDMRUVZWRDRRFXAPGPIGSPLILFIZSTDZYOVQGGDFUFZPUOJPJVWREUVRQIYPCEHGYUZUKWTFXELUNOKBANZFTFRMXZSXXQSBGPCWGXPFSCANSVUYLMTZIRCCCJJPBQAEPWVCDIMLOPOXQEGJKVQIVHEFAPQMVCYSQAFKCTYTPAOOJZCWIPGDPAFTINBFFHVXYEQXCEIDJJOUABBAHSWKHGMLJBXDSQEFBBDLTLJPLZPIPPTRGDRZIZPUPYJODOCSOYCZZWTKYWMBQTFMFEQZWVPQYLJTMEYKYBNOPEPUMHCFJSLFWOISWLKFFABTYFQDTEQBDELIEOZQ";

static int ct_kr[N];
static int ct_std[N];
static int k2std[26];
static int hpos[256];

static inline float eval_3clocks_kr(const int *q7, const int *q8, const int *q9, int *out_pt) {
    int pt[N];
    for (int t = 0; t < N; t++) {
        int ks = (q7[t % 7] + q8[t % 8] + q9[t % 9]) % 26;
        int p_kr = (ct_kr[t] - ks + 26) % 26;
        pt[t] = k2std[p_kr];
    }
    if (out_pt) memcpy(out_pt, pt, N * sizeof(int));

    float s = 0.0f;
    for (int i = 0; i < N - 3; i++) {
        s += quad[pt[i]][pt[i+1]][pt[i+2]][pt[i+3]];
    }
    return s / (N - 3);
}

static inline float eval_3clocks_std(const int *q7, const int *q8, const int *q9, int *out_pt) {
    int pt[N];
    for (int t = 0; t < N; t++) {
        int ks = (q7[t % 7] + q8[t % 8] + q9[t % 9]) % 26;
        pt[t] = (ct_std[t] - ks + 26) % 26;
    }
    if (out_pt) memcpy(out_pt, pt, N * sizeof(int));

    float s = 0.0f;
    for (int i = 0; i < N - 3; i++) {
        s += quad[pt[i]][pt[i+1]][pt[i+2]][pt[i+3]];
    }
    return s / (N - 3);
}

int main(int argc, char **argv) {
    int total_restarts = (argc > 1) ? atoi(argv[1]) : 5000;
    int mode = (argc > 2) ? atoi(argv[2]) : 0; // 0 = Kryptos, 1 = Standard

    load_quads();
    for (int i = 0; i < 26; i++) {
        hpos[(unsigned char)KRYPTOS[i]] = i;
        k2std[i] = KRYPTOS[i] - 'A';
    }
    for (int i = 0; i < N; i++) {
        ct_kr[i] = hpos[(unsigned char)PK10_CT[i]];
        ct_std[i] = PK10_CT[i] - 'A';
    }

    printf("======================================================================\n");
    printf("Simulated Annealing on REAL PK10 (3-Clocks 7, 8, 9) [%d restarts, Mode: %s]\n",
           total_restarts, mode == 0 ? "Quagmire III (Kryptos)" : "Standard Alphabet");
    printf("======================================================================\n");

    float global_best_sc = -999.0f;
    int g_q7[7], g_q8[8], g_q9[9];
    char g_pt[N + 1];

    double t0 = omp_get_wtime();

    #pragma omp parallel
    {
        unsigned int seed = 888 + omp_get_thread_num() * 3119;
        float loc_best_sc = -999.0f;
        int l_q7[7], l_q8[8], l_q9[9];
        char l_pt[N + 1];

        #pragma omp for schedule(dynamic, 25)
        for (int rep = 0; rep < total_restarts; rep++) {
            int q7[7], q8[8], q9[9];
            for (int i = 0; i < 7; i++) q7[i] = rand_r(&seed) % 26;
            for (int i = 0; i < 8; i++) q8[i] = rand_r(&seed) % 26;
            for (int i = 0; i < 9; i++) q9[i] = rand_r(&seed) % 26;

            float cur_sc = (mode == 0) ? eval_3clocks_kr(q7, q8, q9, NULL)
                                       : eval_3clocks_std(q7, q8, q9, NULL);
            float temp = 2.0f;
            float cooling = 0.9992f;

            for (int step = 0; step < 5000; step++) {
                int clk = rand_r(&seed) % 3;
                int pos, old_v, new_v;

                if (clk == 0) {
                    pos = rand_r(&seed) % 7; old_v = q7[pos];
                    new_v = (old_v + 1 + (rand_r(&seed) % 25)) % 26;
                    q7[pos] = new_v;
                } else if (clk == 1) {
                    pos = rand_r(&seed) % 8; old_v = q8[pos];
                    new_v = (old_v + 1 + (rand_r(&seed) % 25)) % 26;
                    q8[pos] = new_v;
                } else {
                    pos = rand_r(&seed) % 9; old_v = q9[pos];
                    new_v = (old_v + 1 + (rand_r(&seed) % 25)) % 26;
                    q9[pos] = new_v;
                }

                float sc = (mode == 0) ? eval_3clocks_kr(q7, q8, q9, NULL)
                                       : eval_3clocks_std(q7, q8, q9, NULL);
                float delta = sc - cur_sc;

                if (delta > 0.0f || expf(delta / temp) > ((float)rand_r(&seed) / RAND_MAX)) {
                    cur_sc = sc;
                } else {
                    if (clk == 0) q7[pos] = old_v;
                    else if (clk == 1) q8[pos] = old_v;
                    else q9[pos] = old_v;
                }

                temp *= cooling;
            }

            // Greedy Polish on all 24 positions
            int improved = 1;
            while (improved) {
                improved = 0;
                for (int p = 0; p < 7; p++) {
                    int best_v = q7[p], old_v = q7[p]; float best_d = 0.0f;
                    for (int diff = 1; diff < 26; diff++) {
                        q7[p] = (old_v + diff) % 26;
                        float sc = (mode == 0) ? eval_3clocks_kr(q7, q8, q9, NULL)
                                               : eval_3clocks_std(q7, q8, q9, NULL);
                        if (sc - cur_sc > best_d) { best_d = sc - cur_sc; best_v = q7[p]; }
                    }
                    if (best_d > 1e-4f) { q7[p] = best_v; cur_sc += best_d; improved = 1; }
                    else q7[p] = old_v;
                }
                for (int p = 0; p < 8; p++) {
                    int best_v = q8[p], old_v = q8[p]; float best_d = 0.0f;
                    for (int diff = 1; diff < 26; diff++) {
                        q8[p] = (old_v + diff) % 26;
                        float sc = (mode == 0) ? eval_3clocks_kr(q7, q8, q9, NULL)
                                               : eval_3clocks_std(q7, q8, q9, NULL);
                        if (sc - cur_sc > best_d) { best_d = sc - cur_sc; best_v = q8[p]; }
                    }
                    if (best_d > 1e-4f) { q8[p] = best_v; cur_sc += best_d; improved = 1; }
                    else q8[p] = old_v;
                }
                for (int p = 0; p < 9; p++) {
                    int best_v = q9[p], old_v = q9[p]; float best_d = 0.0f;
                    for (int diff = 1; diff < 26; diff++) {
                        q9[p] = (old_v + diff) % 26;
                        float sc = (mode == 0) ? eval_3clocks_kr(q7, q8, q9, NULL)
                                               : eval_3clocks_std(q7, q8, q9, NULL);
                        if (sc - cur_sc > best_d) { best_d = sc - cur_sc; best_v = q9[p]; }
                    }
                    if (best_d > 1e-4f) { q9[p] = best_v; cur_sc += best_d; improved = 1; }
                    else q9[p] = old_v;
                }
            }

            if (cur_sc > loc_best_sc) {
                loc_best_sc = cur_sc;
                memcpy(l_q7, q7, 7 * sizeof(int));
                memcpy(l_q8, q8, 8 * sizeof(int));
                memcpy(l_q9, q9, 9 * sizeof(int));

                int pt_arr[N];
                if (mode == 0) eval_3clocks_kr(q7, q8, q9, pt_arr);
                else eval_3clocks_std(q7, q8, q9, pt_arr);
                for (int i = 0; i < N; i++) l_pt[i] = 'A' + pt_arr[i];
                l_pt[N] = '\0';
            }
        }

        #pragma omp critical
        {
            if (loc_best_sc > global_best_sc) {
                global_best_sc = loc_best_sc;
                memcpy(g_q7, l_q7, 7 * sizeof(int));
                memcpy(g_q8, l_q8, 8 * sizeof(int));
                memcpy(g_q9, l_q9, 9 * sizeof(int));
                strcpy(g_pt, l_pt);
                printf("[Thread %d] Global Best: %.4f\n", omp_get_thread_num(), global_best_sc);
                printf("  PT: %.80s...\n\n", g_pt);
            }
        }
    }

    double elapsed = omp_get_wtime() - t0;
    printf("%d restarts completed in %.3f s (%.1f restarts/sec)!\n\n",
           total_restarts, elapsed, total_restarts / elapsed);

    printf("======================================================================\n");
    printf("FINAL BEST REAL PK10 RESULT (Mode: %s)\n", mode == 0 ? "Quagmire III" : "Standard");
    printf("======================================================================\n");
    printf("Score: %.4f\n", global_best_sc);
    printf("q7: ["); for (int i=0; i<7; i++) printf("%d%s", g_q7[i], i==6?"":", "); printf("]\n");
    printf("q8: ["); for (int i=0; i<8; i++) printf("%d%s", g_q8[i], i==7?"":", "); printf("]\n");
    printf("q9: ["); for (int i=0; i<9; i++) printf("%d%s", g_q9[i], i==8?"":", "); printf("]\n");
    printf("\nFull Plaintext:\n%s\n", g_pt);

    return 0;
}
