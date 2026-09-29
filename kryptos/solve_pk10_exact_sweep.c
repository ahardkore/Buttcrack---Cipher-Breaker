#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>

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

static inline float score_plain(const int *pt) {
    float s = 0.0f;
    for (int i = 0; i < N - 3; i++) {
        s += quad[pt[i]][pt[i+1]][pt[i+2]][pt[i+3]];
    }
    return s / (N - 3);
}

int main() {
    init_tables();
    load_quadgrams();

    printf("Full unpruned sweep of all 4,826,809 states for PK10 under 'STILL VEILED IN THE'...\n");

    float global_best_sc = -999.0f;
    char global_best_pt[N + 1] = "";
    int best_f[6] = {0};

    double t0 = omp_get_wtime();

    #pragma omp parallel
    {
        float local_best_sc = -999.0f;
        char local_best_pt[N + 1] = "";
        int local_best_f[6] = {0};
        int pt[N];
        int x[24];
        int q7[7], q8[8], q9[9];

        #pragma omp for schedule(dynamic, 1)
        for (int f0 = 0; f0 < 13; f0++) {
            for (int f1 = 0; f1 < 13; f1++) {
                for (int f2 = 0; f2 < 13; f2++) {
                    for (int f3 = 0; f3 < 13; f3++) {
                        for (int f4 = 0; f4 < 13; f4++) {
                            for (int f5 = 0; f5 < 13; f5++) {
                                x[15] = f0; x[16] = f1; x[17] = f2;
                                x[20] = f3; x[21] = f4; x[22] = f5;
                                x[14] = 0; x[23] = 0;

                                x[0] = (11 + 12 * f0 + 12 * f1 + 1 * f2) % 13;
                                x[1] = (3 + 12 * f0 + 12 * f1 + 1 * f3) % 13;
                                x[2] = (9 + 12 * f0 + 12 * f1 + 1 * f4) % 13;
                                x[3] = (8 + 12 * f0 + 12 * f1 + 1 * f5) % 13;
                                x[4] = (6 + 12 * f0 + 12 * f1) % 13;
                                x[5] = (6 + 12 * f1) % 13;
                                x[6] = (0 + 12 * f0) % 13;
                                x[7] = (4 + 1 * f0 + 12 * f2) % 13;
                                x[8] = (5 + 1 * f0 + 1 * f1 + 12 * f2 + 12 * f3) % 13;
                                x[9] = (4 + 1 * f0 + 1 * f1 + 12 * f3 + 12 * f4) % 13;
                                x[10] = (12 + 1 * f0 + 1 * f1 + 12 * f3 + 12 * f4) % 13;
                                x[11] = (0 + 1 * f0 + 1 * f1 + 12 * f4 + 12 * f5) % 13;
                                x[12] = (6 + 1 * f0 + 1 * f1 + 12 * f5) % 13;
                                x[13] = (12 + 1 * f1) % 13;
                                x[18] = (10 + 1 * f3) % 13;
                                x[19] = (7 + 1 * f4) % 13;

                                for (int i = 0; i < 7; i++) q7[i] = crt(q2_7[i], x[i]);
                                for (int i = 0; i < 8; i++) q8[i] = crt(q2_8[i], x[7 + i]);
                                for (int i = 0; i < 9; i++) q9[i] = crt(q2_9[i], x[15 + i]);

                                for (int i = 0; i < N; i++) {
                                    int k = (q7[i % 7] + q8[i % 8] + q9[i % 9]) % 26;
                                    pt[i] = alpha_to_std[(c_idx[i] - k + 26) % 26];
                                }

                                float sc = score_plain(pt);

                                if (sc > -7.2f) {
                                    #pragma omp critical
                                    {
                                        if (sc > global_best_sc) {
                                            global_best_sc = sc;
                                            for (int i = 0; i < 6; i++) best_f[i] = local_best_f[i];
                                            for (int i = 0; i < N; i++) global_best_pt[i] = 'A' + pt[i];
                                            global_best_pt[N] = '\0';
                                            printf("\n>>> CANDIDATE HIT! Score = %.4f | Free: [%d, %d, %d, %d, %d, %d]\n",
                                                   sc, f0, f1, f2, f3, f4, f5);
                                            printf("  PT: %.150s...\n\n", global_best_pt);
                                            fflush(stdout);
                                        }
                                    }
                                }

                                if (sc > local_best_sc) {
                                    local_best_sc = sc;
                                    local_best_f[0] = f0; local_best_f[1] = f1; local_best_f[2] = f2;
                                    local_best_f[3] = f3; local_best_f[4] = f4; local_best_f[5] = f5;
                                    for (int i = 0; i < N; i++) local_best_pt[i] = 'A' + pt[i];
                                    local_best_pt[N] = '\0';
                                }
                            }
                        }
                    }
                }
            }
        }

        #pragma omp critical
        {
            if (local_best_sc > global_best_sc) {
                global_best_sc = local_best_sc;
                for (int i = 0; i < 6; i++) best_f[i] = local_best_f[i];
                strcpy(global_best_pt, local_best_pt);
            }
        }
    }

    double elapsed = omp_get_wtime() - t0;
    printf("\nFinished 4,826,809 full evaluations in %.2f s (%.1f million evals/sec)\n",
           elapsed, 4.826809 / elapsed);
    printf("Global Best Score = %.4f | Free: [%d, %d, %d, %d, %d, %d]\n",
           global_best_sc, best_f[0], best_f[1], best_f[2], best_f[3], best_f[4], best_f[5]);
    printf("Plaintext:\n%s\n", global_best_pt);

    return 0;
}
