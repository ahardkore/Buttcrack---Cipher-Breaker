#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <time.h>
#include <omp.h>
#include "pk8_arrays.h"

#define BEAM_SIZE 200000

static float quad[26][26][26][26];
static float bg[26][26];

void load_models() {
    FILE *f_bg = fopen("english_bigrams.bin", "rb");
    if (!f_bg) { printf("Error opening english_bigrams.bin\n"); exit(1); }
    if (fread(bg, sizeof(float), 26 * 26, f_bg) != 26 * 26) {
        printf("Error reading english_bigrams.bin\n"); exit(1);
    }
    fclose(f_bg);

    FILE *f_q = fopen("quad.bin", "rb");
    if (!f_q) { printf("Error opening quad.bin\n"); exit(1); }
    if (fread(quad, sizeof(float), 26 * 26 * 26 * 26, f_q) != 26 * 26 * 26 * 26) {
        printf("Error reading quad.bin\n"); exit(1);
    }
    fclose(f_q);
}

typedef struct {
    unsigned char p[18]; // Plaintext in KR alphabet
    float score;
} Cand;

// Helper to compute P[t] in standard alphabet given P_kr[0..j]
static inline int get_pt_std(int t, const unsigned char *p_kr, int len) {
    int s = D_VEC[t];
    for (int k = 0; k < len; k++) {
        s += W_INT[t][k] * p_kr[k];
    }
    s = (s % 26 + 26) % 26;
    return KR2STD[s];
}

int compare_cands(const void *a, const void *b) {
    float diff = ((const Cand *)b)->score - ((const Cand *)a)->score;
    return (diff > 0) ? 1 : ((diff < 0) ? -1 : 0);
}

int main(int argc, char **argv) {
    load_models();
    printf("Models loaded successfully. Starting beam search (Beam size = %d)...\n", BEAM_SIZE);

    Cand *cur_beam = malloc(BEAM_SIZE * sizeof(Cand));
    Cand *next_beam = malloc(BEAM_SIZE * 26 * sizeof(Cand));
    if (!cur_beam || !next_beam) { printf("Alloc error\n"); return 1; }
    int cur_size = 0;

    // Step 0: initialize with 26 single-letter candidates
    for (int let_std = 0; let_std < 26; let_std++) {
        cur_beam[let_std].p[0] = STD2KR[let_std];
        cur_beam[let_std].score = 0.0f;
    }
    cur_size = 26;

    double t0 = omp_get_wtime();

    for (int j = 1; j < 18; j++) {
        int next_size = 0;

        #pragma omp parallel
        {
            Cand *local_cands = malloc(cur_size * 26 * sizeof(Cand));
            int local_n = 0;

            #pragma omp for schedule(dynamic, 128)
            for (int i = 0; i < cur_size; i++) {
                Cand parent = cur_beam[i];
                int prev_std = KR2STD[parent.p[j - 1]];

                for (int let_std = 0; let_std < 26; let_std++) {
                    float sc_delta = 0.0f;

                    // Bigram score from previous letter
                    float bg_sc = bg[prev_std][let_std];
                    if (bg_sc < -5.5f) continue; // Prune non-English bigrams
                    sc_delta += bg_sc;

                    // Quadgram score in prefix
                    if (j >= 3) {
                        int q0 = KR2STD[parent.p[j - 3]];
                        int q1 = KR2STD[parent.p[j - 2]];
                        int q2 = prev_std;
                        int q3 = let_std;
                        float qsc = quad[q0][q1][q2][q3];
                        if (qsc < -8.0f) continue; // Prune terrible prefix quadgrams
                        sc_delta += qsc * 2.0f;
                    }

                    Cand child = parent;
                    child.p[j] = STD2KR[let_std];

                    // Check forward constraints
                    int valid = 1;
                    if (j == 13) {
                        int p34 = get_pt_std(34, child.p, 14);
                        int p35 = get_pt_std(35, child.p, 14);
                        int p36 = get_pt_std(36, child.p, 14);
                        int p37 = get_pt_std(37, child.p, 14);
                        float fq = quad[p34][p35][p36][p37];
                        if (fq < -8.0f) valid = 0;
                        else sc_delta += fq * 3.0f;
                    } else if (j == 14) {
                        int p35 = get_pt_std(35, child.p, 15);
                        int p36 = get_pt_std(36, child.p, 15);
                        int p37 = get_pt_std(37, child.p, 15);
                        int p38 = get_pt_std(38, child.p, 15);
                        float fq = quad[p35][p36][p37][p38];
                        if (fq < -8.0f) valid = 0;
                        else sc_delta += fq * 3.0f;
                    } else if (j == 15) {
                        int p36 = get_pt_std(36, child.p, 16);
                        int p37 = get_pt_std(37, child.p, 16);
                        int p38 = get_pt_std(38, child.p, 16);
                        int p39 = get_pt_std(39, child.p, 16);
                        float fq1 = quad[p36][p37][p38][p39];

                        int p47 = get_pt_std(47, child.p, 16);
                        int p48 = get_pt_std(48, child.p, 16);
                        int p49 = get_pt_std(49, child.p, 16);
                        int p50 = get_pt_std(50, child.p, 16);
                        float fq2 = quad[p47][p48][p49][p50];

                        int p64 = get_pt_std(64, child.p, 16);
                        int p65 = get_pt_std(65, child.p, 16);
                        int p66 = get_pt_std(66, child.p, 16);
                        int p67 = get_pt_std(67, child.p, 16);
                        float fq3 = quad[p64][p65][p66][p67];

                        int p71 = get_pt_std(71, child.p, 16);
                        int p72 = get_pt_std(72, child.p, 16);
                        int p73 = get_pt_std(73, child.p, 16);
                        int p74 = get_pt_std(74, child.p, 16);
                        float fq4 = quad[p71][p72][p73][p74];

                        if (fq1 < -8.0f || fq2 < -8.0f || fq3 < -8.0f || fq4 < -8.0f) valid = 0;
                        else sc_delta += (fq1 + fq2 + fq3 + fq4) * 3.0f;
                    }

                    if (!valid) continue;

                    child.score = parent.score + sc_delta;
                    local_cands[local_n++] = child;
                }
            }

            #pragma omp critical
            {
                for (int k = 0; k < local_n; k++) {
                    if (next_size < BEAM_SIZE * 26) {
                        next_beam[next_size++] = local_cands[k];
                    }
                }
            }
            free(local_cands);
        }

        // Sort next_beam and keep top BEAM_SIZE
        qsort(next_beam, next_size, sizeof(Cand), compare_cands);
        cur_size = (next_size < BEAM_SIZE) ? next_size : BEAM_SIZE;
        memcpy(cur_beam, next_beam, cur_size * sizeof(Cand));

        char sample[19];
        for (int k = 0; k <= j; k++) sample[k] = 'A' + KR2STD[cur_beam[0].p[k]];
        sample[j + 1] = '\0';
        printf("Step j=%2d | Candidates: %7d | Top Score: %8.2f | Top Prefix: %s\n",
               j, cur_size, cur_beam[0].score, sample);
        fflush(stdout);

        if (cur_size == 0) {
            printf("Beam empty at step %d. Exiting.\n", j);
            break;
        }
    }

    double elapsed = omp_get_wtime() - t0;
    printf("\nSearch finished in %.3f s. Evaluating full 153-char plaintexts of top 20 candidates:\n\n", elapsed);

    for (int rank = 0; rank < (cur_size < 20 ? cur_size : 20); rank++) {
        char full_pt[154];
        for (int t = 0; t < 153; t++) {
            full_pt[t] = 'A' + get_pt_std(t, cur_beam[rank].p, 18);
        }
        full_pt[153] = '\0';

        // Score full plaintext with quadgrams
        float full_sc = 0.0f;
        for (int t = 0; t < 150; t++) {
            full_sc += quad[full_pt[t]-'A'][full_pt[t+1]-'A'][full_pt[t+2]-'A'][full_pt[t+3]-'A'];
        }
        full_sc /= 150.0f;

        printf("--- Rank %2d (Prefix Score: %8.2f | Full Text Score: %.4f) ---\n",
               rank + 1, cur_beam[rank].score, full_sc);
        printf("%.75s\n", full_pt);
        printf("%.78s\n\n", full_pt + 75);
    }

    free(cur_beam);
    free(next_beam);
    return 0;
}
