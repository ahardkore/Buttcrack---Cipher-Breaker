#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>
#include <time.h>

#define N 153
#define WIN 18

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

// Precomputed unimodular weights W[win][N][18] and D[win][N]
static int W_all[N - WIN + 1][N][WIN];
static int D_all[N - WIN + 1][N];
static int valid_win[N - WIN + 1];

// Evaluate quadgram score of standard alphabet plaintext
static inline float score_pt(const int *pt) {
    float s = 0.0f;
    for (int i = 0; i < N - 3; i++) {
        s += quad[pt[i]][pt[i+1]][pt[i+2]][pt[i+3]];
    }
    return s / (N - 3);
}

int main() {
    load_quads();

    for (int i = 0; i < 26; i++) {
        hpos[(unsigned char)KRYPTOS[i]] = i;
        k2std[i] = KRYPTOS[i] - 'A';
    }
    for (int i = 0; i < N; i++) ct_kr[i] = hpos[(unsigned char)PK8_CT[i]];

    // Load precomputed W and D from Python precomputation or compute directly
    // Let's read from pk8_weights_all.bin if it exists, or generate it
    FILE *f_w = fopen("pk8_weights_all.bin", "rb");
    if (!f_w) {
        printf("pk8_weights_all.bin not found! Please run precompute_pk8_weights.py first.\n");
        return 1;
    }
    fread(W_all, sizeof(int), (N - WIN + 1) * N * WIN, f_w);
    fread(D_all, sizeof(int), (N - WIN + 1) * N, f_w);
    fread(valid_win, sizeof(int), N - WIN + 1, f_w);
    fclose(f_w);

    printf("Loaded precomputed unimodular weights for all 136 windows!\n");

    // Load candidate phrases
    FILE *f_cribs = fopen("apprentice_phrases_18.txt", "r");
    if (!f_cribs) { printf("Cannot open apprentice_phrases_18.txt\n"); return 1; }
    char (*phrases)[20] = malloc(150000 * sizeof(*phrases));
    int n_phrases = 0;
    char line[64];
    while (fgets(line, sizeof(line), f_cribs) && n_phrases < 150000) {
        if (line[strlen(line)-1] == '\n') line[strlen(line)-1] = 0;
        if (line[strlen(line)-1] == '\r') line[strlen(line)-1] = 0;
        if (strlen(line) == 18) {
            strcpy(phrases[n_phrases++], line);
        }
    }
    fclose(f_cribs);

    printf("Loaded %d unique 18-character craft phrases.\n", n_phrases);
    printf("Scanning %d phrases x 136 windows = %lld placements...\n",
           n_phrases, (long long)n_phrases * 136);

    double t0 = omp_get_wtime();
    float global_best_sc = -999.0f;
    char global_best_pt[160] = "";
    char global_best_phrase[20] = "";
    int global_best_win = -1;

    #pragma omp parallel
    {
        float local_best_sc = -999.0f;
        char local_best_pt[160] = "";
        char local_best_phrase[20] = "";
        int local_best_win = -1;

        #pragma omp for schedule(dynamic, 50)
        for (int pi = 0; pi < n_phrases; pi++) {
            int p_kr[WIN];
            for (int j = 0; j < WIN; j++) p_kr[j] = hpos[(unsigned char)phrases[pi][j]];

            for (int w = 0; w <= N - WIN; w++) {
                if (!valid_win[w]) continue;

                int pt_std[N];
                for (int t = 0; t < N; t++) {
                    int s = D_all[w][t];
                    const int *W_row = W_all[w][t];
                    for (int j = 0; j < WIN; j++) {
                        s += W_row[j] * p_kr[j];
                    }
                    int pt_kr = (s % 26 + 26) % 26;
                    pt_std[t] = k2std[pt_kr];
                }

                float sc = score_pt(pt_std);

                if (sc > -6.0f) {
                    #pragma omp critical
                    {
                        char pt_str[N + 1];
                        for (int t = 0; t < N; t++) pt_str[t] = 'A' + pt_std[t];
                        pt_str[N] = '\0';
                        printf(">>> HIT! Score: %.4f | Win: %2d | Phrase: %s <<<\n", sc, w, phrases[pi]);
                        printf("  PT: %s\n\n", pt_str);
                    }
                }

                if (sc > local_best_sc) {
                    local_best_sc = sc;
                    local_best_win = w;
                    strcpy(local_best_phrase, phrases[pi]);
                    for (int t = 0; t < N; t++) local_best_pt[t] = 'A' + pt_std[t];
                    local_best_pt[N] = '\0';
                }
            }
        }

        #pragma omp critical
        {
            if (local_best_sc > global_best_sc) {
                global_best_sc = local_best_sc;
                global_best_win = local_best_win;
                strcpy(global_best_phrase, local_best_phrase);
                strcpy(global_best_pt, local_best_pt);
            }
        }
    }

    double elapsed = omp_get_wtime() - t0;
    printf("Sweep completed in %.3f seconds!\n", elapsed);
    printf("Best Score: %.4f at Win %d with phrase %s\n", global_best_sc, global_best_win, global_best_phrase);
    printf("PT: %s\n", global_best_pt);

    free(phrases);
    return 0;
}
