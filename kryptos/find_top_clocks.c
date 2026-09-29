#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

#define N 144

static const char *ALPH = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
static const char *PK9_REAL = "KSYAWFEYYOISZGEUFBLYATAIBYFAQBQYYVDWJKLJXMYIEPIFVHPQNHZGSUHUUDXLEHRHUMALHEGLHXSJMUXGNUIVBXGUJHZRZGUSVHMLSCTSUQXHSUMQQIFUQGKHJGUQGLHDKEWSKAMHIJXD";

static double log_english_freq[26];
static const double english_freq[26] = {
    0.08167, 0.01492, 0.02782, 0.04253, 0.12702, 0.02228, 0.02015,
    0.06094, 0.06966, 0.00153, 0.00772, 0.04025, 0.02406, 0.06749,
    0.07507, 0.01929, 0.00095, 0.05987, 0.06327, 0.09056, 0.02758,
    0.00978, 0.02360, 0.00150, 0.01974, 0.00074
};

static int ct_kr[N];
static int ct_std[N];
static int kr_to_std[26];
static int std_to_kr[26];
static double slice_ll[4][28][26];

void init() {
    for (int a = 0; a < 26; a++) {
        log_english_freq[a] = log(english_freq[a]);
        kr_to_std[a] = ALPH[a] - 'A';
        std_to_kr[ALPH[a] - 'A'] = a;
    }
    for (int i = 0; i < N; i++) {
        ct_kr[i] = std_to_kr[PK9_REAL[i] - 'A'];
        ct_std[i] = PK9_REAL[i] - 'A';
    }
    for (int mode = 0; mode < 4; mode++) {
        for (int s = 0; s < 28; s++) {
            for (int sh = 0; sh < 26; sh++) {
                double ll = 0.0;
                for (int i = s; i < N; i += 28) {
                    int p_val;
                    if (mode == 0) p_val = (ct_std[i] - sh + 26) % 26;
                    else if (mode == 1) p_val = (sh - ct_std[i] + 26) % 26;
                    else if (mode == 2) {
                        int kr_p = (ct_kr[i] - sh + 26) % 26;
                        p_val = kr_to_std[kr_p];
                    } else {
                        int kr_p = (sh - ct_kr[i] + 26) % 26;
                        p_val = kr_to_std[kr_p];
                    }
                    ll += log_english_freq[p_val];
                }
                slice_ll[mode][s][sh] = ll;
            }
        }
    }
}

typedef struct {
    double ll;
    int mode;
    int q4[4];
    int q7[7];
} Candidate;

int comp_cand(const void *a, const void *b) {
    Candidate *ca = (Candidate *)a;
    Candidate *cb = (Candidate *)b;
    if (cb->ll > ca->ll) return 1;
    if (cb->ll < ca->ll) return -1;
    return 0;
}

int main() {
    init();
    FILE *out = fopen("top_clocks.csv", "w");
    fprintf(out, "mode,ll,q4_0,q4_1,q4_2,q4_3,q7_0,q7_1,q7_2,q7_3,q7_4,q7_5,q7_6,str_q4_std,str_q7_std,str_q4_kr,str_q7_kr\n");

    for (int mode = 0; mode < 4; mode++) {
        Candidate *cands = (Candidate *)malloc(17576 * sizeof(Candidate));
        int c_idx = 0;

        for (int q4_1 = 0; q4_1 < 26; q4_1++) {
            for (int q4_2 = 0; q4_2 < 26; q4_2++) {
                for (int q4_3 = 0; q4_3 < 26; q4_3++) {
                    Candidate *c = &cands[c_idx++];
                    c->mode = mode;
                    c->q4[0] = 0; c->q4[1] = q4_1; c->q4[2] = q4_2; c->q4[3] = q4_3;
                    c->ll = 0.0;
                    for (int j = 0; j < 7; j++) {
                        double best_j_ll = -1e9;
                        int best_v = 0;
                        for (int v = 0; v < 26; v++) {
                            double j_ll = 0.0;
                            for (int mult = 0; mult < 4; mult++) {
                                int s = j + mult * 7;
                                int sh = (c->q4[s % 4] + v) % 26;
                                j_ll += slice_ll[mode][s][sh];
                            }
                            if (j_ll > best_j_ll) {
                                best_j_ll = j_ll;
                                best_v = v;
                            }
                        }
                        c->q7[j] = best_v;
                        c->ll += best_j_ll;
                    }
                }
            }
        }

        qsort(cands, c_idx, sizeof(Candidate), comp_cand);

        // Write top 500
        for (int i = 0; i < 500 && i < c_idx; i++) {
            Candidate *c = &cands[i];
            char q4_std[5], q7_std[8], q4_kr[5], q7_kr[8];
            for (int k = 0; k < 4; k++) {
                q4_std[k] = 'A' + c->q4[k];
                q4_kr[k] = ALPH[c->q4[k]];
            }
            q4_std[4] = 0; q4_kr[4] = 0;
            for (int k = 0; k < 7; k++) {
                q7_std[k] = 'A' + c->q7[k];
                q7_kr[k] = ALPH[c->q7[k]];
            }
            q7_std[7] = 0; q7_kr[7] = 0;

            fprintf(out, "%d,%.4f,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%s,%s,%s,%s\n",
                    c->mode, c->ll,
                    c->q4[0], c->q4[1], c->q4[2], c->q4[3],
                    c->q7[0], c->q7[1], c->q7[2], c->q7[3], c->q7[4], c->q7[5], c->q7[6],
                    q4_std, q7_std, q4_kr, q7_kr);
        }
        free(cands);
    }
    fclose(out);
    printf("Saved top 500 clock configurations per mode to top_clocks.csv\n");
    return 0;
}
