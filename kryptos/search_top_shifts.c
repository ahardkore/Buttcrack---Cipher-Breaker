#include <stdio.h>
#include <stdlib.h>
#include <string.h>

const char *ALPH = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
const char *UNDONE = "QGKVHPZGUKSYHEGBYFHJGQNHSVHAWFLHXAQBUQGZGSMLSEYYSJMQYYLHDUHUCTSOISUXGVDWKEWUDXUQXZGENUIJKLSKALEHHSUUFBVBXJXMMHIRHUMQQLYAGUJYIEJXDMALIFUTAIHZRPIF";

#define N 144
float quad_table[26*26*26*26];
int alph_to_std[26];

// English letter frequencies in percent
double ENG_FREQ[26] = {
    8.2, 1.5, 2.8, 4.3, 12.7, 2.2, 2.0, 6.1, 7.0, 0.15,
    0.8, 4.0, 2.4, 6.7, 7.5, 1.9, 0.1, 6.0, 6.3, 9.1,
    2.8, 1.0, 2.4, 0.15, 2.0, 0.07
};

int get_idx(char c) {
    for (int i = 0; i < 26; i++) {
        if (ALPH[i] == c) return i;
    }
    return -1;
}

void load_quads() {
    for (int i = 0; i < 26*26*26*26; i++) quad_table[i] = -8.0f;
    for (int i = 0; i < 26; i++) alph_to_std[i] = ALPH[i] - 'A';

    FILE *f = fopen("/home/user/english_quads.tsv", "r");
    if (!f) exit(1);
    char line[128];
    while (fgets(line, sizeof(line), f)) {
        char q[5];
        float sc;
        if (sscanf(line, "%4s\t%f", q, &sc) == 2) {
            int c0 = q[0] - 'A', c1 = q[1] - 'A', c2 = q[2] - 'A', c3 = q[3] - 'A';
            if (c0>=0 && c0<26 && c1>=0 && c1<26 && c2>=0 && c2<26 && c3>=0 && c3<26) {
                int code = ((c0 * 26 + c1) * 26 + c2) * 26 + c3;
                quad_table[code] = sc;
            }
        }
    }
    fclose(f);
}

int main() {
    load_quads();
    int c_arr[N];
    for (int i = 0; i < N; i++) c_arr[i] = get_idx(UNDONE[i]);

    // Rank shifts for each column
    int top_shifts[7][8];
    for (int r = 0; r < 7; r++) {
        int col_len = 0;
        int col_chars[32];
        for (int i = r; i < N; i += 7) col_chars[col_len++] = c_arr[i];

        double chi_arr[26];
        int s_order[26];
        for (int s = 0; s < 26; s++) {
            s_order[s] = s;
            int counts[26] = {0};
            for (int j = 0; j < col_len; j++) {
                int p_alph = (col_chars[j] - s + 26) % 26;
                int p_std = alph_to_std[p_alph];
                counts[p_std]++;
            }
            double chi = 0.0;
            for (int c = 0; c < 26; c++) {
                double exp = col_len * ENG_FREQ[c] / 100.0;
                double diff = counts[c] - exp;
                chi += (diff * diff) / exp;
            }
            chi_arr[s] = chi;
        }

        // Sort shifts by chi
        for (int i = 0; i < 25; i++) {
            for (int j = i + 1; j < 26; j++) {
                if (chi_arr[s_order[j]] < chi_arr[s_order[i]]) {
                    int tmp = s_order[i]; s_order[i] = s_order[j]; s_order[j] = tmp;
                }
            }
        }

        printf("Col %d top shifts: ", r);
        for (int k = 0; k < 7; k++) {
            top_shifts[r][k] = s_order[k];
            printf("%c(s=%d) ", ALPH[s_order[k]], s_order[k]);
        }
        printf("\n");
    }

    printf("Searching 7^7 = 823,543 shift combinations...\n");
    float global_best_sc = -999.0f;
    int best_s[7] = {0};
    char best_pt[N+1];

    int s[7];
    for (int i0 = 0; i0 < 7; i0++) { s[0] = top_shifts[0][i0];
    for (int i1 = 0; i1 < 7; i1++) { s[1] = top_shifts[1][i1];
    for (int i2 = 0; i2 < 7; i2++) { s[2] = top_shifts[2][i2];
    for (int i3 = 0; i3 < 7; i3++) { s[3] = top_shifts[3][i3];
    for (int i4 = 0; i4 < 7; i4++) { s[4] = top_shifts[4][i4];
    for (int i5 = 0; i5 < 7; i5++) { s[5] = top_shifts[5][i5];
    for (int i6 = 0; i6 < 7; i6++) { s[6] = top_shifts[6][i6];

        int pt_std[N];
        for (int k = 0; k < N; k++) {
            int p = (c_arr[k] - s[k % 7] + 26) % 26;
            pt_std[k] = alph_to_std[p];
        }

        float sc = 0.0f;
        for (int k = 0; k < N - 3; k++) {
            int code = ((pt_std[k] * 26 + pt_std[k+1]) * 26 + pt_std[k+2]) * 26 + pt_std[k+3];
            sc += quad_table[code];
        }
        sc /= (N - 3);

        if (sc > global_best_sc) {
            global_best_sc = sc;
            memcpy(best_s, s, sizeof(s));
            for (int k = 0; k < N; k++) {
                int p = (c_arr[k] - s[k % 7] + 26) % 26;
                best_pt[k] = ALPH[p];
            }
            best_pt[N] = '\0';
            if (sc > -5.5f) {
                printf("HIT: sc=%.3f | key=%c%c%c%c%c%c%c | PT: %s\n",
                       sc, ALPH[s[0]], ALPH[s[1]], ALPH[s[2]], ALPH[s[3]], ALPH[s[4]], ALPH[s[5]], ALPH[s[6]], best_pt);
            }
        }
    }}}}}}}

    printf("Best score: %.3f with key=%c%c%c%c%c%c%c\n",
           global_best_sc, ALPH[best_s[0]], ALPH[best_s[1]], ALPH[best_s[2]], ALPH[best_s[3]], ALPH[best_s[4]], ALPH[best_s[5]], ALPH[best_s[6]]);
    printf("PT: %s\n", best_pt);
    return 0;
}
