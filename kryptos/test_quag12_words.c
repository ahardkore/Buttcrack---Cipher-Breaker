#include <stdio.h>
#include <stdlib.h>
#include <string.h>

const char *KRYP = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
const char *STD  = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";
const char *CT   = "KSYAWFEYYOISZGEUFBLYATAIBYFAQBQYYVDWJKLJXMYIEPIFVHPQNHZGSUHUUDXLEHRHUMALHEGLHXSJMUXGNUIVBXGUJHZRZGUSVHMLSCTSUQXHSUMQQIFUQGKHJGUQGLHDKEWSKAMHIJXD";

#define N 144
float quad_table[26*26*26*26];
int kryp_to_std[26];
int std_to_kryp[26];

void load_quads() {
    for (int i = 0; i < 26*26*26*26; i++) quad_table[i] = -8.0f;
    for (int i = 0; i < 26; i++) {
        kryp_to_std[i] = KRYP[i] - 'A';
        for (int j = 0; j < 26; j++) {
            if (KRYP[j] == STD[i]) {
                std_to_kryp[i] = j;
                break;
            }
        }
    }

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
    int c_std[N];
    int c_kryp[N];
    for (int i = 0; i < N; i++) {
        c_std[i] = CT[i] - 'A';
        c_kryp[i] = std_to_kryp[CT[i] - 'A'];
    }

    FILE *f = fopen("/home/user/words_alpha.txt", "r");
    if (!f) return 1;

    char line[128];
    float best_q1 = -999.0f, best_q2 = -999.0f;
    char best_w1[32] = "", best_w2[32] = "";

    while (fgets(line, sizeof(line), f)) {
        int L = strlen(line);
        while (L > 0 && (line[L-1] == '\r' || line[L-1] == '\n')) line[--L] = '\0';
        if (L != 7) continue;

        // Quagmire I: PT in KRYPTOS, CT in STD, key in STD
        // C = (P_kryp + K_std) mod 26 in STD?
        // Specifically: Quagmire I tableau has standard alphabet top row (CT), keyed alphabet shifted (PT).
        // Standard formula: PT_kryp = (C_std - K_std) mod 26 -> PT_std = kryp_to_std[PT_kryp]
        int k_std[7];
        int k_kryp[7];
        for (int i = 0; i < 7; i++) {
            char c = line[i] - 'a' + 'A';
            k_std[i] = c - 'A';
            k_kryp[i] = std_to_kryp[c - 'A'];
        }

        // Test Quagmire I:
        int pt_std[N];
        for (int i = 0; i < N; i++) {
            int p_k = (c_std[i] - k_std[i % 7] + 26) % 26;
            pt_std[i] = kryp_to_std[p_k];
        }
        float sc = 0.0f;
        for (int i = 0; i < N - 3; i++) {
            int code = ((pt_std[i] * 26 + pt_std[i+1]) * 26 + pt_std[i+2]) * 26 + pt_std[i+3];
            sc += quad_table[code];
        }
        sc /= (N - 3);
        if (sc > best_q1) {
            best_q1 = sc;
            strcpy(best_w1, line);
            if (sc > -5.5f) printf("Q1 HIT: %s score=%.3f\n", line, sc);
        }

        // Test Quagmire II: PT in STD, CT in KRYPTOS, key in KRYPTOS
        // PT_std = (C_kryp - K_kryp) mod 26
        for (int i = 0; i < N; i++) {
            pt_std[i] = (c_kryp[i] - k_kryp[i % 7] + 26) % 26;
        }
        sc = 0.0f;
        for (int i = 0; i < N - 3; i++) {
            int code = ((pt_std[i] * 26 + pt_std[i+1]) * 26 + pt_std[i+2]) * 26 + pt_std[i+3];
            sc += quad_table[code];
        }
        sc /= (N - 3);
        if (sc > best_q2) {
            best_q2 = sc;
            strcpy(best_w2, line);
            if (sc > -5.5f) printf("Q2 HIT: %s score=%.3f\n", line, sc);
        }
    }
    fclose(f);

    printf("Best Q1: score=%.3f with '%s'\n", best_q1, best_w1);
    printf("Best Q2: score=%.3f with '%s'\n", best_q2, best_w2);
    return 0;
}
