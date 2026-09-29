#include <stdio.h>
#include <stdlib.h>
#include <string.h>

const char *ALPH = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
const char *CT = "KSYAWFEYYOISZGEUFBLYATAIBYFAQBQYYVDWJKLJXMYIEPIFVHPQNHZGSUHUUDXLEHRHUMALHEGLHXSJMUXGNUIVBXGUJHZRZGUSVHMLSCTSUQXHSUMQQIFUQGKHJGUQGLHDKEWSKAMHIJXD";

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
    for (int i = 0; i < N; i++) c_arr[i] = get_idx(CT[i]);

    FILE *f = fopen("/home/user/words_alpha.txt", "r");
    if (!f) return 1;

    char line[128];
    int tested = 0;
    float global_best_sc = -999.0f;
    char global_best_w6[16] = "";
    int global_best_w7_shifts[7] = {0};
    char global_best_pt[N+1];

    while (fgets(line, sizeof(line), f)) {
        int L = strlen(line);
        while (L > 0 && (line[L-1] == '\r' || line[L-1] == '\n')) line[--L] = '\0';
        if (L != 6) continue;

        int k6[6];
        int ok = 1;
        for (int i = 0; i < 6; i++) {
            char c = line[i];
            if (c >= 'a' && c <= 'z') c = c - 'a' + 'A';
            k6[i] = get_idx(c);
            if (k6[i] < 0) { ok = 0; break; }
        }
        if (!ok) continue;
        tested++;

        // Compute C'' = (C - k6) mod 26
        int c_pp[N];
        for (int i = 0; i < N; i++) {
            c_pp[i] = (c_arr[i] - k6[i % 6] + 26) % 26;
        }

        // For each of the 7 columns, find the best shift s in [0..25] by Chi-squared against English
        int best_w7_shift[7];
        for (int r = 0; r < 7; r++) {
            double best_chi = 1e9;
            int best_s = 0;
            int col_len = 0;
            int col_chars[32];
            for (int i = r; i < N; i += 7) {
                col_chars[col_len++] = c_pp[i];
            }

            for (int s = 0; s < 26; s++) {
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
                if (chi < best_chi) {
                    best_chi = chi;
                    best_s = s;
                }
            }
            best_w7_shift[r] = best_s;
        }

        // Decrypt full text
        int pt_std[N];
        char pt_alph[N+1];
        for (int i = 0; i < N; i++) {
            int p = (c_pp[i] - best_w7_shift[i % 7] + 26) % 26;
            pt_std[i] = alph_to_std[p];
            pt_alph[i] = ALPH[p];
        }
        pt_alph[N] = '\0';

        // Score with quadgrams
        float sc = 0.0f;
        for (int i = 0; i < N - 3; i++) {
            int code = ((pt_std[i] * 26 + pt_std[i+1]) * 26 + pt_std[i+2]) * 26 + pt_std[i+3];
            sc += quad_table[code];
        }
        sc /= (N - 3);

        if (sc > global_best_sc) {
            global_best_sc = sc;
            strcpy(global_best_w6, line);
            memcpy(global_best_w7_shifts, best_w7_shift, sizeof(best_w7_shift));
            strcpy(global_best_pt, pt_alph);
            if (sc > -5.5f) {
                printf("CANDIDATE HIT: W6=%s sc=%.3f | W7_shifts=[%d,%d,%d,%d,%d,%d,%d] | PT: %s\n",
                       line, sc, best_w7_shift[0], best_w7_shift[1], best_w7_shift[2],
                       best_w7_shift[3], best_w7_shift[4], best_w7_shift[5], best_w7_shift[6], pt_alph);
            }
        }
    }
    fclose(f);

    printf("Tested %d 6-letter words. Global best score: %.3f with W6='%s'\n", tested, global_best_sc, global_best_w6);
    printf("Best W7 shifts: [%d, %d, %d, %d, %d, %d, %d]\n",
           global_best_w7_shifts[0], global_best_w7_shifts[1], global_best_w7_shifts[2],
           global_best_w7_shifts[3], global_best_w7_shifts[4], global_best_w7_shifts[5], global_best_w7_shifts[6]);
    printf("PT: %s\n", global_best_pt);
    return 0;
}
