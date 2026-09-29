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
const char *PK10_CT = "UBINFYJSFQXQVRLJJAJDGBXIWKDMAREZTGSHQWRXCHEPCLYSDNGYRRBTCVOZJYVLYWREJTCDOYVEYCJJVZKRMKTRPGVHRWMJSRCSHXZMJEVQKJYJJAYZKDFQBGRSWXATJMEXKFXAXKSIZXOERFESNVCGCNRHEOBCNCBUPXTJJRCIMDMRUVZWRDRRFXAPGPIGSPLILFIZSTDZYOVQGGDFUFZPUOJPJVWREUVRQIYPCEHGYUZUKWTFXELUNOKBANZFTFRMXZSXXQSBGPCWGXPFSCANSVUYLMTZIRCCCJJPBQAEPWVCDIMLOPOXQEGJKVQIVHEFAPQMVCYSQAFKCTYTPAOOJZCWIPGDPAFTINBFFHVXYEQXCEIDJJOUABBAHSWKHGMLJBXDSQEFBBDLTLJPLZPIPPTRGDRZIZPUPYJODOCSOYCZZWTKYWMBQTFMFEQZWVPQYLJTMEYKYBNOPEPUMHCFJSLFWOISWLKFFABTYFQDTEQBDELIEOZQ";

// Fixed binary parities for PK10
static const int q2_7[7] = {0, 1, 1, 1, 0, 0, 0};
static const int q2_8[8] = {0, 0, 0, 1, 0, 1, 0, 0};
static const int q2_9[9] = {0, 0, 1, 1, 1, 1, 0, 0, 0};

// CRT reconstruction: q = (13 * q2 + 14 * q13) % 26
static inline int crt(int q2, int q13) {
    return (13 * q2 + 14 * q13) % 26;
}

int main(int argc, char **argv) {
    load_quadgrams();
    int N = strlen(PK10_CT);

    int c_idx[600];
    int alpha_to_std[26];
    for (int i = 0; i < 26; i++) alpha_to_std[i] = KRYPTOS[i] - 'A';
    for (int i = 0; i < N; i++) c_idx[i] = strchr(KRYPTOS, PK10_CT[i]) - KRYPTOS;

    int num_restarts = 5000;
    if (argc > 1) num_restarts = atoi(argv[1]);

    printf("Starting OpenMP CRT Coordinate Descent on PK10 (%d restarts)...\n", num_restarts);

    float global_best_sc = -999.0f;
    char global_best_pt[600] = "";

    #pragma omp parallel
    {
        unsigned int seed = 1234 + omp_get_thread_num() * 7777;

        #pragma omp for schedule(dynamic, 50)
        for (int r = 0; r < num_restarts; r++) {
            // Random initialization in Z_13 (gauge fix q13_8[7] = 0, q13_9[8] = 0)
            int q13_7[7], q13_8[8], q13_9[9];
            for (int i = 0; i < 7; i++) q13_7[i] = rand_r(&seed) % 13;
            for (int i = 0; i < 7; i++) q13_8[i] = rand_r(&seed) % 13; q13_8[7] = 0;
            for (int i = 0; i < 8; i++) q13_9[i] = rand_r(&seed) % 13; q13_9[8] = 0;

            int q7[7], q8[8], q9[9];
            for (int i = 0; i < 7; i++) q7[i] = crt(q2_7[i], q13_7[i]);
            for (int i = 0; i < 8; i++) q8[i] = crt(q2_8[i], q13_8[i]);
            for (int i = 0; i < 9; i++) q9[i] = crt(q2_9[i], q13_9[i]);

            // Decrypt and score
            int pt[600];
            for (int i = 0; i < N; i++) {
                int k = (q7[i % 7] + q8[i % 8] + q9[i % 9]) % 26;
                pt[i] = alpha_to_std[(c_idx[i] - k + 26) % 26];
            }
            float sc = 0;
            for (int i = 0; i < N - 3; i++) sc += quad[pt[i]][pt[i+1]][pt[i+2]][pt[i+3]];
            sc /= (N - 3);

            // Coordinate descent over the 22 free Z_13 variables
            int improved = 1;
            int iter = 0;
            while (improved && iter < 10) {
                improved = 0;
                iter++;

                // Clock 7
                for (int idx = 0; idx < 7; idx++) {
                    int best_v = q13_7[idx];
                    float best_sub = sc;
                    for (int v = 0; v < 13; v++) {
                        if (v == q13_7[idx]) continue;
                        q7[idx] = crt(q2_7[idx], v);
                        float test_sc = 0;
                        for (int i = 0; i < N; i++) {
                            int k = (q7[i % 7] + q8[i % 8] + q9[i % 9]) % 26;
                            pt[i] = alpha_to_std[(c_idx[i] - k + 26) % 26];
                        }
                        for (int i = 0; i < N - 3; i++) test_sc += quad[pt[i]][pt[i+1]][pt[i+2]][pt[i+3]];
                        test_sc /= (N - 3);
                        if (test_sc > best_sub) {
                            best_sub = test_sc;
                            best_v = v;
                        }
                    }
                    if (best_v != q13_7[idx]) {
                        q13_7[idx] = best_v;
                        q7[idx] = crt(q2_7[idx], best_v);
                        sc = best_sub;
                        improved = 1;
                    }
                }

                // Clock 8
                for (int idx = 0; idx < 7; idx++) {
                    int best_v = q13_8[idx];
                    float best_sub = sc;
                    for (int v = 0; v < 13; v++) {
                        if (v == q13_8[idx]) continue;
                        q8[idx] = crt(q2_8[idx], v);
                        float test_sc = 0;
                        for (int i = 0; i < N; i++) {
                            int k = (q7[i % 7] + q8[i % 8] + q9[i % 9]) % 26;
                            pt[i] = alpha_to_std[(c_idx[i] - k + 26) % 26];
                        }
                        for (int i = 0; i < N - 3; i++) test_sc += quad[pt[i]][pt[i+1]][pt[i+2]][pt[i+3]];
                        test_sc /= (N - 3);
                        if (test_sc > best_sub) {
                            best_sub = test_sc;
                            best_v = v;
                        }
                    }
                    if (best_v != q13_8[idx]) {
                        q13_8[idx] = best_v;
                        q8[idx] = crt(q2_8[idx], best_v);
                        sc = best_sub;
                        improved = 1;
                    }
                }

                // Clock 9
                for (int idx = 0; idx < 8; idx++) {
                    int best_v = q13_9[idx];
                    float best_sub = sc;
                    for (int v = 0; v < 13; v++) {
                        if (v == q13_9[idx]) continue;
                        q9[idx] = crt(q2_9[idx], v);
                        float test_sc = 0;
                        for (int i = 0; i < N; i++) {
                            int k = (q7[i % 7] + q8[i % 8] + q9[i % 9]) % 26;
                            pt[i] = alpha_to_std[(c_idx[i] - k + 26) % 26];
                        }
                        for (int i = 0; i < N - 3; i++) test_sc += quad[pt[i]][pt[i+1]][pt[i+2]][pt[i+3]];
                        test_sc /= (N - 3);
                        if (test_sc > best_sub) {
                            best_sub = test_sc;
                            best_v = v;
                        }
                    }
                    if (best_v != q13_9[idx]) {
                        q13_9[idx] = best_v;
                        q9[idx] = crt(q2_9[idx], best_v);
                        sc = best_sub;
                        improved = 1;
                    }
                }
            }

            if (sc > global_best_sc) {
                #pragma omp critical
                {
                    if (sc > global_best_sc) {
                        global_best_sc = sc;
                        for (int i = 0; i < N; i++) {
                            int k = (q7[i % 7] + q8[i % 8] + q9[i % 9]) % 26;
                            global_best_pt[i] = 'A' + alpha_to_std[(c_idx[i] - k + 26) % 26];
                        }
                        global_best_pt[N] = '\0';
                        printf("Restart %5d: New Best sc = %6.4f\n", r, global_best_sc);
                        printf("  q7: [%d, %d, %d, %d, %d, %d, %d]\n", q7[0], q7[1], q7[2], q7[3], q7[4], q7[5], q7[6]);
                        printf("  q8: [%d, %d, %d, %d, %d, %d, %d, %d]\n", q8[0], q8[1], q8[2], q8[3], q8[4], q8[5], q8[6], q8[7]);
                        printf("  q9: [%d, %d, %d, %d, %d, %d, %d, %d, %d]\n", q9[0], q9[1], q9[2], q9[3], q9[4], q9[5], q9[6], q9[7], q9[8]);
                        printf("  PT (first 80): ");
                        for (int k = 0; k < 80; k++) printf("%c", global_best_pt[k]);
                        printf("\n\n");
                    }
                }
            }
        }
    }
    printf("Completed %d restarts. Global best sc = %6.4f\n", num_restarts, global_best_sc);
    return 0;
}
