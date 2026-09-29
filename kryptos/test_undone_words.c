#include <stdio.h>
#include <stdlib.h>
#include <string.h>

const char *ALPH = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
const char *STD  = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";
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

int main() {
    load_quads();
    int c_arr[N];
    int c_std[N];
    for (int i = 0; i < N; i++) {
        c_arr[i] = get_idx(UNDONE[i]);
        c_std[i] = UNDONE[i] - 'A';
    }

    FILE *f = fopen("/home/user/words_alpha.txt", "r");
    if (!f) return 1;

    char line[128];
    int tested = 0;
    float best_q3 = -999.0f, best_bf = -999.0f, best_vig = -999.0f;
    char best_w_q3[32] = "", best_w_bf[32] = "", best_w_vig[32] = "";
    char best_pt_q3[N+1], best_pt_bf[N+1], best_pt_vig[N+1];

    while (fgets(line, sizeof(line), f)) {
        int L = strlen(line);
        while (L > 0 && (line[L-1] == '\r' || line[L-1] == '\n')) line[--L] = '\0';
        if (L != 7) continue;

        int k_kryp[7];
        int k_std[7];
        int ok = 1;
        for (int i = 0; i < 7; i++) {
            char c = line[i];
            if (c >= 'a' && c <= 'z') c = c - 'a' + 'A';
            k_std[i] = c - 'A';
            k_kryp[i] = get_idx(c);
            if (k_kryp[i] < 0 || k_std[i] < 0 || k_std[i] >= 26) { ok = 0; break; }
        }
        if (!ok) continue;
        tested++;

        // 1. Quagmire III: P = (C - K) mod 26 in KRYPTOS
        int pt_std[N];
        char pt_chars[N+1];
        for (int i = 0; i < N; i++) {
            int p = (c_arr[i] - k_kryp[i % 7] + 26) % 26;
            pt_std[i] = alph_to_std[p];
            pt_chars[i] = ALPH[p];
        }
        pt_chars[N] = '\0';
        float sc = 0.0f;
        for (int i = 0; i < N - 3; i++) {
            int code = ((pt_std[i] * 26 + pt_std[i+1]) * 26 + pt_std[i+2]) * 26 + pt_std[i+3];
            sc += quad_table[code];
        }
        sc /= (N - 3);
        if (sc > best_q3) {
            best_q3 = sc;
            strcpy(best_w_q3, line);
            strcpy(best_pt_q3, pt_chars);
            if (sc > -5.5f) printf("HIT Q3: %s sc=%.3f | %s\n", line, sc, pt_chars);
        }

        // 2. Beaufort: P = (K - C) mod 26 in KRYPTOS
        for (int i = 0; i < N; i++) {
            int p = (k_kryp[i % 7] - c_arr[i] + 26) % 26;
            pt_std[i] = alph_to_std[p];
            pt_chars[i] = ALPH[p];
        }
        pt_chars[N] = '\0';
        sc = 0.0f;
        for (int i = 0; i < N - 3; i++) {
            int code = ((pt_std[i] * 26 + pt_std[i+1]) * 26 + pt_std[i+2]) * 26 + pt_std[i+3];
            sc += quad_table[code];
        }
        sc /= (N - 3);
        if (sc > best_bf) {
            best_bf = sc;
            strcpy(best_w_bf, line);
            strcpy(best_pt_bf, pt_chars);
            if (sc > -5.5f) printf("HIT BF: %s sc=%.3f | %s\n", line, sc, pt_chars);
        }

        // 3. Vigenere (STD): P = (C - K) mod 26 in STD
        for (int i = 0; i < N; i++) {
            pt_std[i] = (c_std[i] - k_std[i % 7] + 26) % 26;
            pt_chars[i] = pt_std[i] + 'A';
        }
        pt_chars[N] = '\0';
        sc = 0.0f;
        for (int i = 0; i < N - 3; i++) {
            int code = ((pt_std[i] * 26 + pt_std[i+1]) * 26 + pt_std[i+2]) * 26 + pt_std[i+3];
            sc += quad_table[code];
        }
        sc /= (N - 3);
        if (sc > best_vig) {
            best_vig = sc;
            strcpy(best_w_vig, line);
            strcpy(best_pt_vig, pt_chars);
            if (sc > -5.5f) printf("HIT VIG: %s sc=%.3f | %s\n", line, sc, pt_chars);
        }
    }
    fclose(f);

    printf("Tested %d 7-letter words on 'undone':\n", tested);
    printf("Best Q3:  score=%.3f with '%s'\n  PT: %s\n", best_q3, best_w_q3, best_pt_q3);
    printf("Best BF:  score=%.3f with '%s'\n  PT: %s\n", best_bf, best_w_bf, best_pt_bf);
    printf("Best VIG: score=%.3f with '%s'\n  PT: %s\n", best_vig, best_w_vig, best_pt_vig);
    return 0;
}
