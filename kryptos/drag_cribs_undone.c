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

const char *thematic_cribs[] = {
    "WHITESMITH", "WORKSHOP", "DRAWPLATE", "BELLOWS", "HAMMER",
    "NEEDLE", "NEEDLES", "HEARTH", "SILVER", "ANVIL",
    "STEEL", "POINT", "DRAWING", "STUDY", "YEARS",
    "RESIDUE", "PRACTICE", "MAKING", "STREWN", "GUTTER",
    "EXQUISITE", "PIERCE", "SPLIT", "FLAME", "TEMPER",
    "QUENCH", "TONGS", "CHISEL", "FURNACE", "CHARCOAL",
    "MASTER", "APPRENTICE", "FINER", "THINNER", "SMALLER",
    "SECOND", "FIRST", "THIRD", "THREAD", "STRINGS",
    "HAIR", "GLASS", "BERN", "VIENNESE", "ANATOMIST",
    "TENYEARS", "MYOWNMAKING", "ONEBYONE", "DRAWTHEWIRE",
    "THROUGHTHE", "THEWIRE", "THEEYE", "THEFIRE", "THECOALS",
    "THEANVIL", "THEHAMMER", "THEWORKSHOP", "THEWHITESMITH",
    NULL
};

const char *alph_keywords[] = {
    "KRYPTOS", "NIMBLE", "WIMBLE", "WORKSHOP", "WHITESMITH",
    "NEEDLE", "HEARTH", "BERLIN", "WEBSTER", "STANDARD",
    NULL
};

int main() {
    load_quads();

    float global_best_sc = -999.0f;
    char global_best_crib[32] = "";
    int global_best_pos = 0;
    char global_best_alph[32] = "";
    char global_best_pt[N+1];

    for (int a_idx = 0; alph_keywords[a_idx]; a_idx++) {
        char alph[27];
        if (strcmp(alph_keywords[a_idx], "STANDARD") == 0) {
            strcpy(alph, "ABCDEFGHIJKLMNOPQRSTUVWXYZ");
        } else {
            make_keyed_alphabet(alph_keywords[a_idx], alph);
        }

        int get_idx[26];
        int alph_to_std[26];
        for (int i = 0; i < 26; i++) {
            alph_to_std[i] = alph[i] - 'A';
            get_idx[alph[i] - 'A'] = i;
        }

        int c_arr[N];
        for (int i = 0; i < N; i++) c_arr[i] = get_idx[UNDONE[i] - 'A'];

        for (int c_idx = 0; thematic_cribs[c_idx]; c_idx++) {
            const char *crib = thematic_cribs[c_idx];
            int c_len = strlen(crib);
            int crib_arr[32];
            for (int i = 0; i < c_len; i++) crib_arr[i] = get_idx[crib[i] - 'A'];

            for (int pos = 0; pos <= N - c_len; pos++) {
                // Check consistency of crib at pos:
                // S[ (pos + i) % 7 ] = (C[pos + i] - crib[i]) mod 26
                int shifts[7];
                int set[7] = {0};
                int consistent = 1;

                for (int i = 0; i < c_len; i++) {
                    int r = (pos + i) % 7;
                    int s = (c_arr[pos + i] - crib_arr[i] + 26) % 26;
                    if (set[r] && shifts[r] != s) {
                        consistent = 0;
                        break;
                    }
                    shifts[r] = s;
                    set[r] = 1;
                }
                if (!consistent) continue;

                // Find unset columns
                int unset_cols[7];
                int n_unset = 0;
                for (int r = 0; r < 7; r++) {
                    if (!set[r]) unset_cols[n_unset++] = r;
                }

                // If n_unset == 0: exact key determined!
                if (n_unset == 0) {
                    int pt_std[N];
                    char pt_alph[N+1];
                    for (int k = 0; k < N; k++) {
                        int p = (c_arr[k] - shifts[k % 7] + 26) % 26;
                        pt_std[k] = alph_to_std[p];
                        pt_alph[k] = alph[p];
                    }
                    pt_alph[N] = '\0';
                    float sc = 0.0f;
                    for (int k = 0; k < N - 3; k++) {
                        int code = ((pt_std[k] * 26 + pt_std[k+1]) * 26 + pt_std[k+2]) * 26 + pt_std[k+3];
                        sc += quad_table[code];
                    }
                    sc /= (N - 3);

                    if (sc > global_best_sc) {
                        global_best_sc = sc;
                        strcpy(global_best_crib, crib);
                        global_best_pos = pos;
                        strcpy(global_best_alph, alph_keywords[a_idx]);
                        strcpy(global_best_pt, pt_alph);
                        if (sc > -5.5f) {
                            printf("HIT! alph=%s crib=%s at pos %d score=%.3f\n",
                                   alph_keywords[a_idx], crib, pos, sc);
                            printf("  Key: %c%c%c%c%c%c%c\n",
                                   alph[shifts[0]], alph[shifts[1]], alph[shifts[2]],
                                   alph[shifts[3]], alph[shifts[4]], alph[shifts[5]], alph[shifts[6]]);
                            printf("  PT: %s\n", pt_alph);
                        }
                    }
                } else if (n_unset == 1) {
                    // Try all 26 shifts for the 1 unset column
                    int u = unset_cols[0];
                    for (int su = 0; su < 26; su++) {
                        shifts[u] = su;
                        int pt_std[N];
                        char pt_alph[N+1];
                        for (int k = 0; k < N; k++) {
                            int p = (c_arr[k] - shifts[k % 7] + 26) % 26;
                            pt_std[k] = alph_to_std[p];
                            pt_alph[k] = alph[p];
                        }
                        pt_alph[N] = '\0';
                        float sc = 0.0f;
                        for (int k = 0; k < N - 3; k++) {
                            int code = ((pt_std[k] * 26 + pt_std[k+1]) * 26 + pt_std[k+2]) * 26 + pt_std[k+3];
                            sc += quad_table[code];
                        }
                        sc /= (N - 3);

                        if (sc > global_best_sc) {
                            global_best_sc = sc;
                            strcpy(global_best_crib, crib);
                            global_best_pos = pos;
                            strcpy(global_best_alph, alph_keywords[a_idx]);
                            strcpy(global_best_pt, pt_alph);
                            if (sc > -5.5f) {
                                printf("HIT! alph=%s crib=%s at pos %d score=%.3f\n",
                                       alph_keywords[a_idx], crib, pos, sc);
                                printf("  Key: %c%c%c%c%c%c%c\n",
                                       alph[shifts[0]], alph[shifts[1]], alph[shifts[2]],
                                       alph[shifts[3]], alph[shifts[4]], alph[shifts[5]], alph[shifts[6]]);
                                printf("  PT: %s\n", pt_alph);
                            }
                        }
                    }
                }
            }
        }
    }

    printf("\nFinished dragging all cribs across all alphabets.\n");
    printf("Best result: score=%.3f with crib '%s' at pos %d (alph=%s)\n",
           global_best_sc, global_best_crib, global_best_pos, global_best_alph);
    printf("PT: %s\n", global_best_pt);
    return 0;
}
