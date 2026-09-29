#include <stdio.h>
#include <stdlib.h>
#include <string.h>

const char *UNDONE = "QGKVHPZGUKSYHEGBYFHJGQNHSVHAWFLHXAQBUQGZGSMLSEYYSJMQYYLHDUHUCTSOISUXGVDWKEWUDXUQXZGENUIJKLSKALEHHSUUFBVBXJXMMHIRHUMQQLYAGUJYIEJXDMALIFUTAIHZRPIF";

#define N 144
float quad_table[26*26*26*26];

void load_quads() {
    for (int i = 0; i < 26*26*26*26; i++) quad_table[i] = -8.0f;
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

void make_keyed_alphabet(const char *kw, char *alph) {
    int used[26] = {0};
    int len = 0;
    for (int i = 0; kw[i]; i++) {
        char c = kw[i];
        if (c >= 'a' && c <= 'z') c = c - 'a' + 'A';
        if (c >= 'A' && c <= 'Z' && !used[c - 'A']) {
            used[c - 'A'] = 1;
            alph[len++] = c;
        }
    }
    for (int c = 0; c < 26; c++) {
        if (!used[c]) {
            alph[len++] = 'A' + c;
        }
    }
    alph[26] = '\0';
}

float eval_shifts(const int *c_arr, const int *shifts, const int *alph_to_std, int *pt_std) {
    for (int i = 0; i < N; i++) {
        int p = (c_arr[i] - shifts[i % 7] + 26) % 26;
        pt_std[i] = alph_to_std[p];
    }
    float sc = 0.0f;
    for (int i = 0; i < N - 3; i++) {
        int code = ((pt_std[i] * 26 + pt_std[i+1]) * 26 + pt_std[i+2]) * 26 + pt_std[i+3];
        sc += quad_table[code];
    }
    return sc / (N - 3);
}

int main() {
    load_quads();

    const char *keywords[] = {
        "KRYPTOS", "PALIMPSEST", "ABSCISSA", "PROVENANCE", "MARGINS",
        "PENTIMENTO", "ORDINATE", "PORTAL", "HEARTH", "NEEDLE",
        "WHITESMITH", "WORKSHOP", "WEBSTER", "WOMACKA", "LANGLEY",
        "BERLIN", "SANBORN", "SCHEIDT", "SHADOW", "COMPASS",
        "NIMBLE", "DEFENSE", "INTELLIGENCE", "CENTRAL", "AGENCY",
        "STANDARD", "", NULL
    };

    float global_best = -999.0f;
    char global_kw[32] = "";
    int global_shifts[7];

    srand(12345);

    for (int k_idx = 0; keywords[k_idx]; k_idx++) {
        char alph[27];
        if (strlen(keywords[k_idx]) == 0 || strcmp(keywords[k_idx], "STANDARD") == 0) {
            strcpy(alph, "ABCDEFGHIJKLMNOPQRSTUVWXYZ");
        } else {
            make_keyed_alphabet(keywords[k_idx], alph);
        }

        int get_idx[26];
        int alph_to_std[26];
        for (int i = 0; i < 26; i++) {
            alph_to_std[i] = alph[i] - 'A';
            get_idx[alph[i] - 'A'] = i;
        }

        int c_arr[N];
        for (int i = 0; i < N; i++) c_arr[i] = get_idx[UNDONE[i] - 'A'];

        float best_kw_sc = -999.0f;
        int best_kw_shifts[7];

        for (int restart = 0; restart < 200; restart++) {
            int shifts[7];
            for (int i = 0; i < 7; i++) shifts[i] = rand() % 26;
            int pt_std[N];
            float cur_sc = eval_shifts(c_arr, shifts, alph_to_std, pt_std);

            int improved = 1;
            while (improved) {
                improved = 0;
                for (int j = 0; j < 7; j++) {
                    int best_s = shifts[j];
                    float best_sc_j = cur_sc;
                    for (int s = 0; s < 26; s++) {
                        if (s == shifts[j]) continue;
                        shifts[j] = s;
                        float sc = eval_shifts(c_arr, shifts, alph_to_std, pt_std);
                        if (sc > best_sc_j) {
                            best_sc_j = sc;
                            best_s = s;
                        }
                    }
                    shifts[j] = best_s;
                    if (best_sc_j > cur_sc + 1e-4f) {
                        cur_sc = best_sc_j;
                        improved = 1;
                    }
                }
            }

            if (cur_sc > best_kw_sc) {
                best_kw_sc = cur_sc;
                memcpy(best_kw_shifts, shifts, sizeof(shifts));
            }
        }

        printf("Keyword: %-15s | Alph: %.12s... | Best score: %.3f\n",
               keywords[k_idx], alph, best_kw_sc);

        if (best_kw_sc > global_best) {
            global_best = best_kw_sc;
            strcpy(global_kw, keywords[k_idx]);
            memcpy(global_shifts, best_kw_shifts, sizeof(best_kw_shifts));
        }
    }

    printf("\nGLOBAL BEST KEYWORD: %s with score=%.3f\n", global_kw, global_best);
    return 0;
}
