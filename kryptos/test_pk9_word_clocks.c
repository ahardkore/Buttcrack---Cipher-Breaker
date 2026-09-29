#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <omp.h>

#define N 144
const char *KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
const char *UNDONE = "QGKVHPZGUKSYHEGBYFHJGQNHSVHAWFLHXAQBUQGZGSMLSEYYSJMQYYLHDUHUCTSOISUXGVDWKEWUDXUQXZGENUIJKLSKALEHHSUUFBVBXJXMMHIRHUMQQLYAGUJYIEJXDMALIFUTAIHZRPIF";

static int undone_kr[N];
static int k2std[26];
static int hpos[256];
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

void init_tables() {
    for (int i = 0; i < 26; i++) {
        hpos[(unsigned char)KRYPTOS[i]] = i;
        k2std[i] = KRYPTOS[i] - 'A';
    }
    for (int i = 0; i < N; i++) undone_kr[i] = hpos[(unsigned char)UNDONE[i]];
}

static inline float score_shifts(const int *shifts, int p) {
    int pt[N];
    for (int t = 0; t < N; t++) {
        int s = shifts[t % p];
        int p_kr = (undone_kr[t] - s + 26) % 26;
        pt[t] = k2std[p_kr];
    }
    float sc = 0.0f;
    for (int i = 0; i < N - 3; i++) {
        sc += quad[pt[i]][pt[i+1]][pt[i+2]][pt[i+3]];
    }
    return sc / (N - 3);
}

int main() {
    load_quads();
    init_tables();

    // Load words of length 7
    FILE *f7 = fopen("words_7.txt", "r");
    if (!f7) { printf("Cannot open words_7.txt\n"); exit(1); }
    char line[128];
    int cap7 = 50000;
    char (*w7)[8] = malloc(cap7 * 8);
    int n7 = 0;
    while (fgets(line, sizeof(line), f7)) {
        char w[64];
        if (sscanf(line, "%s", w) == 1 && strlen(w) == 7) {
            for (int i=0; i<7; i++) {
                if (w[i]>='a' && w[i]<='z') w[i] = w[i]-'a'+'A';
            }
            strcpy(w7[n7++], w);
            if (n7 >= cap7) break;
        }
    }
    fclose(f7);
    printf("Loaded %d 7-letter words.\n", n7);

    // Test 1: Every 7-letter word directly (period 7)
    float best_sc7 = -99.0f;
    char best_w7[8] = "";
    #pragma omp parallel for reduction(max:best_sc7)
    for (int i = 0; i < n7; i++) {
        int shifts[7];
        for (int j = 0; j < 7; j++) shifts[j] = hpos[(unsigned char)w7[i][j]];
        float sc = score_shifts(shifts, 7);
        if (sc > best_sc7) {
            best_sc7 = sc;
        }
    }
    printf("Best single 7-letter word (period 7) score: %.4f\n", best_sc7);

    // Test 2: Every 7-letter word with q2 clock (period 14)
    // shifts[t] = (q7[t % 7] + (t%2 == 1 ? d : 0)) % 26
    float best_sc_q2 = -99.0f;
    int best_w_q2 = -1, best_d_q2 = -1;
    #pragma omp parallel
    {
        float loc_best = -99.0f;
        int loc_w = -1, loc_d = -1;
        #pragma omp for
        for (int i = 0; i < n7; i++) {
            int q7[7];
            for (int j = 0; j < 7; j++) q7[j] = hpos[(unsigned char)w7[i][j]];
            for (int d = 0; d < 26; d++) {
                int s14[14];
                for (int t = 0; t < 14; t++) {
                    s14[t] = (q7[t % 7] + (t % 2 == 1 ? d : 0)) % 26;
                }
                float sc = score_shifts(s14, 14);
                if (sc > loc_best) {
                    loc_best = sc;
                    loc_w = i;
                    loc_d = d;
                }
            }
        }
        #pragma omp critical
        {
            if (loc_best > best_sc_q2) {
                best_sc_q2 = loc_best;
                best_w_q2 = loc_w;
                best_d_q2 = loc_d;
            }
        }
    }
    printf("Best (q7, q2) compound score: %.4f (word: %s, d: %d)\n",
           best_sc_q2, w7[best_w_q2], best_d_q2);

    // Test 3: Load words_14.txt
    FILE *f14 = fopen("words_14.txt", "r");
    if (f14) {
        int cap14 = 20000;
        char (*w14)[16] = malloc(cap14 * 16);
        int n14 = 0;
        while (fgets(line, sizeof(line), f14)) {
            char w[64];
            if (sscanf(line, "%s", w) == 1 && strlen(w) == 14) {
                for (int i=0; i<14; i++) {
                    if (w[i]>='a' && w[i]<='z') w[i] = w[i]-'a'+'A';
                }
                strcpy(w14[n14++], w);
                if (n14 >= cap14) break;
            }
        }
        fclose(f14);
        printf("Loaded %d 14-letter words.\n", n14);

        float best_sc14 = -99.0f;
        int best_idx14 = -1;
        #pragma omp parallel
        {
            float loc_best = -99.0f;
            int loc_idx = -1;
            #pragma omp for
            for (int i = 0; i < n14; i++) {
                int s14[14];
                for (int j = 0; j < 14; j++) s14[j] = hpos[(unsigned char)w14[i][j]];
                float sc = score_shifts(s14, 14);
                if (sc > loc_best) {
                    loc_best = sc;
                    loc_idx = i;
                }
            }
            #pragma omp critical
            {
                if (loc_best > best_sc14) {
                    best_sc14 = loc_best;
                    best_idx14 = loc_idx;
                }
            }
        }
        printf("Best single 14-letter word score: %.4f (word: %s)\n",
               best_sc14, w14[best_idx14]);
    }

    return 0;
}
