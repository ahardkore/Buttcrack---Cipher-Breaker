#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

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

    // Load words of length 4 and 7 from words_alpha.txt
    FILE *f = fopen("/home/user/words_alpha.txt", "r");
    if (!f) {
        printf("Failed to open wordlist\n");
        return 1;
    }

    char **w4 = malloc(10000 * sizeof(char*));
    char **w7 = malloc(50000 * sizeof(char*));
    int *w4_idx = malloc(10000 * 4 * sizeof(int));
    int *w7_idx = malloc(50000 * 7 * sizeof(int));
    int n4 = 0, n7 = 0;

    char line[128];
    while (fgets(line, sizeof(line), f)) {
        int len = strlen(line);
        while (len > 0 && (line[len-1] == '\r' || line[len-1] == '\n')) {
            line[--len] = '\0';
        }
        if (len == 4) {
            int ok = 1;
            int idxs[4];
            for (int i = 0; i < 4; i++) {
                char c = line[i];
                if (c >= 'a' && c <= 'z') c = c - 'a' + 'A';
                int val = get_idx(c);
                if (val < 0) { ok = 0; break; }
                idxs[i] = val;
            }
            if (ok) {
                w4[n4] = strdup(line);
                memcpy(&w4_idx[n4 * 4], idxs, sizeof(idxs));
                n4++;
            }
        } else if (len == 7) {
            int ok = 1;
            int idxs[7];
            for (int i = 0; i < 7; i++) {
                char c = line[i];
                if (c >= 'a' && c <= 'z') c = c - 'a' + 'A';
                int val = get_idx(c);
                if (val < 0) { ok = 0; break; }
                idxs[i] = val;
            }
            if (ok) {
                w7[n7] = strdup(line);
                memcpy(&w7_idx[n7 * 7], idxs, sizeof(idxs));
                n7++;
            }
        }
    }
    fclose(f);

    printf("Loaded %d words of len 4, %d words of len 7. Total pairs: %.2e\n",
           n4, n7, (double)n4 * n7);

    clock_t t0 = clock();
    int matches = 0;
    double max_ioc = 0.0;
    char best_w4[16] = "", best_w7[16] = "";

    // Precompute mod 4 and mod 7 indices for 144
    int m4[144], m7[144];
    for (int i = 0; i < n; i++) {
        m4[i] = i % 4;
        m7[i] = i % 7;
    }

    // Threshold for IoC: 144 * 143 = 20592. IoC = sum / 20592.
    // If IoC > 0.058: sum > 1194.
    // If IoC > 0.060: sum > 1235.
    int thresh = 1200;

    #pragma omp parallel for reduction(+:matches)
    for (int i = 0; i < n4; i++) {
        int a[4];
        for (int k = 0; k < 4; k++) a[k] = w4_idx[i * 4 + k];

        for (int j = 0; j < n7; j++) {
            int b[7];
            for (int k = 0; k < 7; k++) b[k] = w7_idx[j * 7 + k];

            int counts[26] = {0};
            for (int t = 0; t < n; t++) {
                int ks = (a[m4[t]] + b[m7[t]]) % 26;
                int p = (c_arr[t] - ks + 26) % 26;
                counts[p]++;
            }

            int sum_coinc = 0;
            for (int k = 0; k < 26; k++) {
                sum_coinc += counts[k] * (counts[k] - 1);
            }

            if (sum_coinc > thresh) {
                double ioc = (double)sum_coinc / (n * (n - 1));
                #pragma omp critical
                {
                    matches++;
                    if (ioc > max_ioc) {
                        max_ioc = ioc;
                        strcpy(best_w4, w4[i]);
                        strcpy(best_w7, w7[j]);
                    }
                    printf("MATCH! IoC = %.5f | W4 = %s, W7 = %s\n", ioc, w4[i], w7[j]);
                }
            }
        }
    }

    clock_t t1 = clock();
    double elapsed = (double)(t1 - t0) / CLOCKS_PER_SEC;
    printf("\nCompleted in %.2f seconds. Matches found: %d\n", elapsed, matches);
    if (matches > 0) {
        printf("Highest IoC = %.5f (W4=%s, W7=%s)\n", max_ioc, best_w4, best_w7);
    }

    return 0;
}
