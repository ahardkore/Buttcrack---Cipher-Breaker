#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
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

static const int A_inv[18][18] = {
    {25, 24, 23, 22, 22, 21, 22, 23, 25, 1, 3, 4, 5, 5, 4, 3, 2, 1},
    {25, 24, 23, 22, 22, 22, 23, 24, 0, 2, 3, 4, 4, 4, 3, 2, 1, 1},
    {25, 25, 25, 25, 0, 0, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0},
    {24, 22, 20, 18, 17, 17, 19, 22, 0, 4, 7, 9, 9, 8, 6, 4, 2, 1},
    {1, 1, 2, 2, 2, 2, 1, 0, 25, 24, 24, 24, 24, 25, 25, 0, 0, 0},
    {1, 2, 3, 4, 4, 4, 3, 1, 25, 23, 22, 22, 22, 23, 24, 25, 0, 0},
    {1, 2, 4, 5, 6, 6, 5, 3, 0, 23, 21, 20, 20, 21, 22, 24, 25, 0},
    {1, 2, 4, 6, 7, 8, 7, 5, 2, 24, 21, 19, 18, 19, 20, 22, 24, 25},
    {0, 25, 24, 23, 22, 22, 23, 24, 0, 2, 3, 4, 4, 3, 2, 1, 0, 0},
    {0, 0, 25, 24, 23, 22, 22, 23, 24, 0, 2, 3, 4, 4, 3, 2, 1, 0},
    {0, 25, 24, 22, 20, 19, 19, 20, 23, 0, 3, 6, 7, 7, 6, 4, 2, 1},
    {1, 2, 3, 4, 4, 3, 2, 0, 24, 23, 22, 22, 23, 24, 25, 0, 0, 0},
    {1, 2, 3, 5, 6, 7, 6, 5, 2, 25, 22, 20, 19, 19, 21, 22, 24, 25},
    {0, 1, 1, 2, 3, 4, 4, 4, 3, 1, 25, 23, 22, 21, 22, 23, 24, 25},
    {0, 0, 0, 0, 0, 1, 1, 2, 2, 2, 1, 0, 25, 24, 24, 24, 25, 25},
    {0, 0, 25, 25, 24, 24, 24, 25, 0, 1, 2, 2, 2, 1, 1, 0, 0, 0},
    {1, 2, 3, 4, 5, 5, 4, 3, 1, 25, 23, 22, 21, 21, 22, 23, 24, 25},
    {0, 1, 1, 2, 2, 3, 2, 2, 1, 0, 25, 24, 24, 23, 24, 24, 25, 25}
};

static char cribs[500000][20];
static int num_cribs = 0;

void load_cribs(const char *fn) {
    FILE *f = fopen(fn, "r");
    if (!f) return;
    char line[64];
    while (fgets(line, sizeof(line), f) && num_cribs < 500000) {
        line[strcspn(line, "\r\n")] = 0;
        if ((int)strlen(line) == 18) {
            strcpy(cribs[num_cribs++], line);
        }
    }
    fclose(f);
}

void test_all_cribs() {
    int N = strlen(PK8_CT);
    printf("Evaluating %d cribs across KRYPTOS & STD, Vig & Beau...\n", num_cribs);

    for (int model = 0; model < 4; model++) {
        const char *alpha = (model < 2) ? KRYPTOS : STD;
        int is_beau = (model % 2 == 1);
        const char *mname = (model < 2) ? "KRYPTOS" : "STD";
        const char *mode = is_beau ? "Beaufort" : "Vigenere";

        int c_idx[160];
        int alpha_to_std[26];
        for (int i = 0; i < 26; i++) alpha_to_std[i] = alpha[i] - 'A';
        for (int i = 0; i < N; i++) c_idx[i] = strchr(alpha, PK8_CT[i]) - alpha;

        #pragma omp parallel for schedule(dynamic)
        for (int idx = 0; idx < num_cribs; idx++) {
            int p_idx[18];
            for (int i = 0; i < 18; i++) p_idx[i] = strchr(alpha, cribs[idx][i]) - alpha;

            int k_idx[18];
            for (int i = 0; i < 18; i++) {
                k_idx[i] = is_beau ? ((p_idx[i] + c_idx[i]) % 26) : ((c_idx[i] - p_idx[i] + 26) % 26);
            }

            int q_sub[18];
            for (int r = 0; r < 18; r++) {
                int sum = 0;
                for (int c = 0; c < 18; c++) sum += A_inv[r][c] * k_idx[c];
                q_sub[r] = sum % 26;
            }

            int q4[4] = {q_sub[0], q_sub[1], q_sub[2], q_sub[3]};
            int q5[5] = {q_sub[4], q_sub[5], q_sub[6], q_sub[7], 0};
            int q6[6] = {q_sub[8], q_sub[9], q_sub[10], q_sub[11], 0, 0};
            int q7[7] = {q_sub[12], q_sub[13], q_sub[14], q_sub[15], q_sub[16], q_sub[17], 0};

            // Early check: score next 12 characters (positions 18 to 29)
            int pt_check[16];
            for (int i = 18; i < 30; i++) {
                int k = (q4[i % 4] + q5[i % 5] + q6[i % 6] + q7[i % 7]) % 26;
                int p = is_beau ? ((k - c_idx[i] + 26) % 26) : ((c_idx[i] - k + 26) % 26);
                pt_check[i - 18] = alpha_to_std[p];
            }
            float sc_early = 0;
            for (int i = 0; i < 9; i++) {
                sc_early += quad[pt_check[i]][pt_check[i+1]][pt_check[i+2]][pt_check[i+3]];
            }
            if (sc_early < -50.0f) continue;

            // Full score
            int pt_full[160];
            for (int i = 0; i < N; i++) {
                int k = (q4[i % 4] + q5[i % 5] + q6[i % 6] + q7[i % 7]) % 26;
                int p = is_beau ? ((k - c_idx[i] + 26) % 26) : ((c_idx[i] - k + 26) % 26);
                pt_full[i] = alpha_to_std[p];
            }
            float sc_full = 0;
            for (int i = 0; i < N - 3; i++) {
                sc_full += quad[pt_full[i]][pt_full[i+1]][pt_full[i+2]][pt_full[i+3]];
            }
            sc_full /= (N - 3);

            if (sc_full > -5.2f) {
                #pragma omp critical
                {
                    printf("  HIT! [%s %s] sc=%6.4f | Crib: %s | ",
                           mname, mode, sc_full, cribs[idx]);
                    for (int i = 0; i < 60; i++) printf("%c", 'A' + pt_full[i]);
                    printf("\n");
                    fflush(stdout);
                }
            }
        }
    }
}

int main() {
    load_quadgrams();
    load_cribs("pk8_narrative_cribs.txt");
    test_all_cribs();
    return 0;
}
