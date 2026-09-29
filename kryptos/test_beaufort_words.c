#include <stdio.h>
#include <stdlib.h>
#include <string.h>

const char *ALPH = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";
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
    double max_ioc = 0;
    char best_word[32] = "";

    while (fgets(line, sizeof(line), f)) {
        int len = strlen(line);
        while (len > 0 && (line[len-1] == '\r' || line[len-1] == '\n')) {
            line[--len] = '\0';
        }
        if (len == 7) {
            int ok = 1;
            int k_idxs[7];
            for (int i = 0; i < 7; i++) {
                char c = line[i];
                if (c >= 'a' && c <= 'z') c = c - 'a' + 'A';
                int val = get_idx(c);
                if (val < 0) { ok = 0; break; }
                k_idxs[i] = val;
            }
            if (!ok) continue;

            tested++;
            // Beaufort: P = (K - C) mod 26
            int counts[26] = {0};
            for (int i = 0; i < n; i++) {
                int p = (c_arr[i] + k_idxs[i % 7]) % 26;
                counts[p]++;
            }

            int sum_coinc = 0;
            for (int k = 0; k < 26; k++) {
                sum_coinc += counts[k] * (counts[k] - 1);
            }
            double ioc = (double)sum_coinc / (n * (n - 1));
            if (ioc > max_ioc) {
                max_ioc = ioc;
                strcpy(best_word, line);
                printf("New max IoC = %.5f with word %s\n", max_ioc, best_word);
            }
        }
    }
    fclose(f);

    printf("Tested %d words of length 7. Max IoC = %.5f (word=%s)\n", tested, max_ioc, best_word);
    return 0;
}
