#include <stdio.h>
#include <stdlib.h>
#include <string.h>

const char *ALPH = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
const char *CT = "KSYAWFEYYOISZGEUFBLYATAIBYFAQBQYYVDWJKLJXMYIEPIFVHPQNHZGSUHUUDXLEHRHUMALHEGLHXSJMUXGNUIVBXGUJHZRZGUSVHMLSCTSUQXHSUMQQIFUQGKHJGUQGLHDKEWSKAMHIJXD";

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
    for (int i = 0; i < N; i++) c_arr[i] = get_idx(CT[i]);

    FILE *f = fopen("/home/user/words_alpha.txt", "r");
    if (!f) return 1;

    char line[128];
    int tested = 0;
    float best_sc = -999.0f;
    char best_word[64] = "";
    char best_pt[N+1];

    while (fgets(line, sizeof(line), f)) {
        int L = strlen(line);
        while (L > 0 && (line[L-1] == '\r' || line[L-1] == '\n')) line[--L] = '\0';
        if (L < 3 || L > 12) continue;

        int ok = 1;
        int primer[32];
        for (int i = 0; i < L; i++) {
            char c = line[i];
            if (c >= 'a' && c <= 'z') c = c - 'a' + 'A';
            int v = get_idx(c);
            if (v < 0) { ok = 0; break; }
            primer[i] = v;
        }
        if (!ok) continue;
        tested++;

        // Decrypt with Plaintext Autokey:
        // P[i] = (C[i] - primer[i]) mod 26 for i < L
        // P[i] = (C[i] - P[i - L]) mod 26 for i >= L
        int P[N];
        for (int i = 0; i < L; i++) {
            P[i] = (c_arr[i] - primer[i] + 26) % 26;
        }
        for (int i = L; i < N; i++) {
            P[i] = (c_arr[i] - P[i - L] + 26) % 26;
        }

        // Score with quadgrams
        float sc = 0.0f;
        for (int i = 0; i < N - 3; i++) {
            int code = ((alph_to_std[P[i]] * 26 + alph_to_std[P[i+1]]) * 26 + alph_to_std[P[i+2]]) * 26 + alph_to_std[P[i+3]];
            sc += quad_table[code];
        }
        sc /= (N - 3);

        if (sc > best_sc) {
            best_sc = sc;
            strcpy(best_word, line);
            for (int i = 0; i < N; i++) best_pt[i] = ALPH[P[i]];
            best_pt[N] = '\0';
            if (sc > -5.5f) {
                printf("AUTOKEY HIT: word=%s (len %d), score=%.3f | PT: %s\n", line, L, sc, best_pt);
            }
        }
    }
    fclose(f);

    printf("Tested %d autokey words (len 3..12). Best score: %.3f with word '%s'\n", tested, best_sc, best_word);
    printf("PT: %s\n", best_pt);
    return 0;
}
