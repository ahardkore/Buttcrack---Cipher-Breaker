#include <stdio.h>
#include <stdlib.h>
#include <string.h>

const char *ALPH = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
const char *CT = "KSYAWFEYYOISZGEUFBLYATAIBYFAQBQYYVDWJKLJXMYIEPIFVHPQNHZGSUHUUDXLEHRHUMALHEGLHXSJMUXGNUIVBXGUJHZRZGUSVHMLSCTSUQXHSUMQQIFUQGKHJGUQGLHDKEWSKAMHIJXD";

int get_idx(char c) {
    for (int i = 0; i < 26; i++) {
        if (ALPH[i] == c) return i;
    }
    return -1;
}

int main() {
    int n = strlen(CT);
    int c_arr[144];
    for (int i = 0; i < n; i++) {
        c_arr[i] = get_idx(CT[i]);
    }

    FILE *f = fopen("/home/user/words_alpha.txt", "r");
    if (!f) return 1;

    char line[128];
    int tested = 0;
    double max_ioc_v = 0, max_ioc_b = 0;
    char best_word_v[32] = "", best_word_b[32] = "";

    while (fgets(line, sizeof(line), f)) {
        int len = strlen(line);
        while (len > 0 && (line[len-1] == '\r' || line[len-1] == '\n')) {
            line[--len] = '\0';
        }
        if (len == 14) {
            int ok = 1;
            int k_idxs[14];
            for (int i = 0; i < 14; i++) {
                char c = line[i];
                if (c >= 'a' && c <= 'z') c = c - 'a' + 'A';
                int val = get_idx(c);
                if (val < 0) { ok = 0; break; }
                k_idxs[i] = val;
            }
            if (!ok) continue;

            tested++;
            // Vigenere: P = (C - K) mod 26
            int cv[26] = {0};
            // Beaufort: P = (K - C) mod 26
            int cb[26] = {0};

            for (int i = 0; i < n; i++) {
                int pv = (c_arr[i] - k_idxs[i % 14] + 26) % 26;
                cv[pv]++;
                int pb = (k_idxs[i % 14] - c_arr[i] + 26) % 26;
                cb[pb]++;
            }

            int sum_v = 0, sum_b = 0;
            for (int k = 0; k < 26; k++) {
                sum_v += cv[k] * (cv[k] - 1);
                sum_b += cb[k] * (cb[k] - 1);
            }
            double ioc_v = (double)sum_v / (n * (n - 1));
            double ioc_b = (double)sum_b / (n * (n - 1));

            if (ioc_v > max_ioc_v) {
                max_ioc_v = ioc_v;
                strcpy(best_word_v, line);
                if (max_ioc_v > 0.055) {
                    printf("New Vigenere IoC = %.5f with word %s\n", max_ioc_v, best_word_v);
                }
            }
            if (ioc_b > max_ioc_b) {
                max_ioc_b = ioc_b;
                strcpy(best_word_b, line);
                if (max_ioc_b > 0.055) {
                    printf("New Beaufort IoC = %.5f with word %s\n", max_ioc_b, best_word_b);
                }
            }
        }
    }
    fclose(f);

    printf("Tested %d words of len 14.\nMax Vigenere IoC = %.5f (%s)\nMax Beaufort IoC = %.5f (%s)\n",
           tested, max_ioc_v, best_word_v, max_ioc_b, best_word_b);
    return 0;
}
