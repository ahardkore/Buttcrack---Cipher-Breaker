#include <stdio.h>
#include <stdlib.h>
#include <string.h>

const char *ALPH = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
const char *CT = "KSYAWFEYYOISZGEUFBLYATAIBYFAQBQYYVDWJKLJXMYIEPIFVHPQNHZGSUHUUDXLEHRHUMALHEGLHXSJMUXGNUIVBXGUJHZRZGUSVHMLSCTSUQXHSUMQQIFUQGKHJGUQGLHDKEWSKAMHIJXD";
const char *UNDONE = "QGKVHPZGUKSYHEGBYFHJGQNHSVHAWFLHXAQBUQGZGSMLSEYYSJMQYYLHDUHUCTSOISUXGVDWKEWUDXUQXZGENUIJKLSKALEHHSUUFBVBXJXMMHIRHUMQQLYAGUJYIEJXDMALIFUTAIHZRPIF";

#define N 144
float quad_table[26*26*26*26];
int alph_to_std[26];

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

// Storage for word lists
char w2[200][3]; int n2 = 0;
char w3[3000][4]; int n3 = 0;
char w4[8000][5]; int n4 = 0;
char w5[17000][6]; int n5 = 0;

void load_words() {
    FILE *f = fopen("/home/user/words_alpha.txt", "r");
    if (!f) exit(1);
    char line[128];
    while (fgets(line, sizeof(line), f)) {
        int L = strlen(line);
        while (L > 0 && (line[L-1] == '\r' || line[L-1] == '\n')) line[--L] = '\0';
        for (int i = 0; i < L; i++) {
            if (line[i] >= 'a' && line[i] <= 'z') line[i] = line[i] - 'a' + 'A';
        }
        if (L == 2 && n2 < 200) strcpy(w2[n2++], line);
        else if (L == 3 && n3 < 3000) strcpy(w3[n3++], line);
        else if (L == 4 && n4 < 8000) strcpy(w4[n4++], line);
        else if (L == 5 && n5 < 17000) strcpy(w5[n5++], line);
    }
    fclose(f);
    printf("Loaded words: w2=%d, w3=%d, w4=%d, w5=%d\n", n2, n3, n4, n5);
}

void test_compound_on(const char *text, const char *label) {
    int c_arr[N];
    for (int i = 0; i < N; i++) c_arr[i] = get_idx(text[i]);

    float global_best_sc = -999.0f;
    char global_best_key[32] = "";
    char global_best_pt[N+1];

    // 1. Test W3 + W4
    printf("Testing W3 + W4 on %s (%d x %d = %d)...\n", label, n3, n4, n3*n4);
    for (int i3 = 0; i3 < n3; i3++) {
        int k3[3];
        for (int k = 0; k < 3; k++) k3[k] = get_idx(w3[i3][k]);

        for (int i4 = 0; i4 < n4; i4++) {
            int k[7];
            k[0] = k3[0]; k[1] = k3[1]; k[2] = k3[2];
            k[3] = get_idx(w4[i4][0]);
            k[4] = get_idx(w4[i4][1]);
            k[5] = get_idx(w4[i4][2]);
            k[6] = get_idx(w4[i4][3]);

            // Quick prune on first 16 chars:
            float sc_quick = 0.0f;
            int pt_quick[16];
            for (int j = 0; j < 16; j++) {
                int p = (c_arr[j] - k[j % 7] + 26) % 26;
                pt_quick[j] = alph_to_std[p];
            }
            for (int j = 0; j < 13; j++) {
                int code = ((pt_quick[j] * 26 + pt_quick[j+1]) * 26 + pt_quick[j+2]) * 26 + pt_quick[j+3];
                sc_quick += quad_table[code];
            }
            sc_quick /= 13;
            if (sc_quick < -6.5f) continue;

            // Full score:
            int pt_std[N];
            char pt_alph[N+1];
            for (int j = 0; j < N; j++) {
                int p = (c_arr[j] - k[j % 7] + 26) % 26;
                pt_std[j] = alph_to_std[p];
                pt_alph[j] = ALPH[p];
            }
            pt_alph[N] = '\0';
            float sc = 0.0f;
            for (int j = 0; j < N - 3; j++) {
                int code = ((pt_std[j] * 26 + pt_std[j+1]) * 26 + pt_std[j+2]) * 26 + pt_std[j+3];
                sc += quad_table[code];
            }
            sc /= (N - 3);

            if (sc > global_best_sc) {
                global_best_sc = sc;
                snprintf(global_best_key, sizeof(global_best_key), "%.10s%.10s", w3[i3], w4[i4]);
                strcpy(global_best_pt, pt_alph);
                if (sc > -5.5f) {
                    printf("HIT on %s: key=%s sc=%.3f | PT: %s\n", label, global_best_key, sc, pt_alph);
                }
            }
        }
    }

    // 2. Test W4 + W3
    printf("Testing W4 + W3 on %s (%d x %d = %d)...\n", label, n4, n3, n4*n3);
    for (int i4 = 0; i4 < n4; i4++) {
        int k4[4];
        for (int k = 0; k < 4; k++) k4[k] = get_idx(w4[i4][k]);

        for (int i3 = 0; i3 < n3; i3++) {
            int k[7];
            k[0] = k4[0]; k[1] = k4[1]; k[2] = k4[2]; k[3] = k4[3];
            k[4] = get_idx(w3[i3][0]);
            k[5] = get_idx(w3[i3][1]);
            k[6] = get_idx(w3[i3][2]);

            // Quick prune:
            float sc_quick = 0.0f;
            int pt_quick[16];
            for (int j = 0; j < 16; j++) {
                int p = (c_arr[j] - k[j % 7] + 26) % 26;
                pt_quick[j] = alph_to_std[p];
            }
            for (int j = 0; j < 13; j++) {
                int code = ((pt_quick[j] * 26 + pt_quick[j+1]) * 26 + pt_quick[j+2]) * 26 + pt_quick[j+3];
                sc_quick += quad_table[code];
            }
            sc_quick /= 13;
            if (sc_quick < -6.5f) continue;

            int pt_std[N];
            char pt_alph[N+1];
            for (int j = 0; j < N; j++) {
                int p = (c_arr[j] - k[j % 7] + 26) % 26;
                pt_std[j] = alph_to_std[p];
                pt_alph[j] = ALPH[p];
            }
            pt_alph[N] = '\0';
            float sc = 0.0f;
            for (int j = 0; j < N - 3; j++) {
                int code = ((pt_std[j] * 26 + pt_std[j+1]) * 26 + pt_std[j+2]) * 26 + pt_std[j+3];
                sc += quad_table[code];
            }
            sc /= (N - 3);

            if (sc > global_best_sc) {
                global_best_sc = sc;
                snprintf(global_best_key, sizeof(global_best_key), "%.10s%.10s", w4[i4], w3[i3]);
                strcpy(global_best_pt, pt_alph);
                if (sc > -5.5f) {
                    printf("HIT on %s: key=%s sc=%.3f | PT: %s\n", label, global_best_key, sc, pt_alph);
                }
            }
        }
    }

    printf("Best compound key on %s: %s score=%.3f\n  PT: %s\n\n",
           label, global_best_key, global_best_sc, global_best_pt);
}

int main() {
    load_quads();
    load_words();
    test_compound_on(CT, "CT9");
    test_compound_on(UNDONE, "UNDONE");
    return 0;
}
