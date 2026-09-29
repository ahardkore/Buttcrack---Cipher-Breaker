#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>
#include <time.h>

#define N 504

static char ct10[N + 1];

void load_real_ct10() {
    FILE *f = fopen("pk_all_ciphertexts.json", "r");
    if (!f) { printf("Cannot open pk_all_ciphertexts.json\n"); exit(1); }
    char buf[4096];
    int found = 0;
    while (fgets(buf, sizeof(buf), f)) {
        if (strstr(buf, "\"PK10\"")) {
            char *p = strchr(buf, ':');
            if (p) {
                p = strchr(p, '\"');
                if (p) {
                    p++;
                    char *end = strchr(p, '\"');
                    if (end) {
                        *end = '\0';
                        strcpy(ct10, p);
                        found = 1;
                        break;
                    }
                }
            }
        }
    }
    fclose(f);
    if (!found || strlen(ct10) != N) {
        printf("Failed to load real PK10\n"); exit(1);
    }
}

// Fast slice IoC
static inline double calc_slice_ioc(const char *s, int p) {
    double sum_ioc = 0.0;
    int m = N / p;
    for (int r = 0; r < p; r++) {
        int cnt[26] = {0};
        for (int i = r; i < N; i += p) {
            cnt[s[i] - 'A']++;
        }
        int pairs = 0;
        for (int c = 0; c < 26; c++) pairs += cnt[c] * (cnt[c] - 1);
        sum_ioc += (double)pairs / (m * (m - 1));
    }
    return sum_ioc / p;
}

int main() {
    load_real_ct10();
    printf("Loaded PK10 (len %zu)\n", strlen(ct10));

    // Test 1: 7 blocks of 72 chars (7! = 5040)
    printf("\n--- Testing all 5,040 permutations of 7 blocks of 72 chars ---\n");
    double best_ioc7 = 0.0;
    int best_p7[7];
    int best_period7 = 0;

    int p[9];
    for (int i = 0; i < 7; i++) p[i] = i;

    // Generate permutations
    void permute7(int k, double *best_ioc, int *best_p, int *best_period, int *arr) {
        if (k == 7) {
            char s[N + 1];
            for (int b = 0; b < 7; b++) {
                memcpy(s + b * 72, ct10 + arr[b] * 72, 72);
            }
            s[N] = '\0';
            for (int pr = 7; pr <= 9; pr++) {
                double val = calc_slice_ioc(s, pr);
                if (val > *best_ioc) {
                    *best_ioc = val;
                    *best_period = pr;
                    memcpy(best_p, arr, 7 * sizeof(int));
                }
            }
            return;
        }
        for (int i = k; i < 7; i++) {
            int tmp = arr[k]; arr[k] = arr[i]; arr[i] = tmp;
            permute7(k + 1, best_ioc, best_p, best_period, arr);
            tmp = arr[k]; arr[k] = arr[i]; arr[i] = tmp;
        }
    }

    permute7(0, &best_ioc7, best_p7, &best_period7, p);
    printf("Best IoC for 7 blocks of 72: %.5f (period %d) | Perm: [", best_ioc7, best_period7);
    for (int i = 0; i < 7; i++) printf("%d%s", best_p7[i], i == 6 ? "" : ", ");
    printf("]\n");

    // Test 2: 8 blocks of 63 chars (8! = 40,320)
    printf("\n--- Testing all 40,320 permutations of 8 blocks of 63 chars ---\n");
    double best_ioc8 = 0.0;
    int best_p8[8];
    int best_period8 = 0;
    for (int i = 0; i < 8; i++) p[i] = i;

    void permute8(int k, double *best_ioc, int *best_p, int *best_period, int *arr) {
        if (k == 8) {
            char s[N + 1];
            for (int b = 0; b < 8; b++) {
                memcpy(s + b * 63, ct10 + arr[b] * 63, 63);
            }
            s[N] = '\0';
            for (int pr = 7; pr <= 9; pr++) {
                double val = calc_slice_ioc(s, pr);
                if (val > *best_ioc) {
                    *best_ioc = val;
                    *best_period = pr;
                    memcpy(best_p, arr, 8 * sizeof(int));
                }
            }
            return;
        }
        for (int i = k; i < 8; i++) {
            int tmp = arr[k]; arr[k] = arr[i]; arr[i] = tmp;
            permute8(k + 1, best_ioc, best_p, best_period, arr);
            tmp = arr[k]; arr[k] = arr[i]; arr[i] = tmp;
        }
    }

    permute8(0, &best_ioc8, best_p8, &best_period8, p);
    printf("Best IoC for 8 blocks of 63: %.5f (period %d) | Perm: [", best_ioc8, best_period8);
    for (int i = 0; i < 8; i++) printf("%d%s", best_p8[i], i == 7 ? "" : ", ");
    printf("]\n");

    // Test 3: 9 blocks of 56 chars (9! = 362,880)
    printf("\n--- Testing all 362,880 permutations of 9 blocks of 56 chars ---\n");
    double best_ioc9 = 0.0;
    int best_p9[9];
    int best_period9 = 0;
    for (int i = 0; i < 9; i++) p[i] = i;

    void permute9(int k, double *best_ioc, int *best_p, int *best_period, int *arr) {
        if (k == 9) {
            char s[N + 1];
            for (int b = 0; b < 9; b++) {
                memcpy(s + b * 56, ct10 + arr[b] * 56, 56);
            }
            s[N] = '\0';
            for (int pr = 7; pr <= 9; pr++) {
                double val = calc_slice_ioc(s, pr);
                if (val > *best_ioc) {
                    *best_ioc = val;
                    *best_period = pr;
                    memcpy(best_p, arr, 9 * sizeof(int));
                }
            }
            return;
        }
        for (int i = k; i < 9; i++) {
            int tmp = arr[k]; arr[k] = arr[i]; arr[i] = tmp;
            permute9(k + 1, best_ioc, best_p, best_period, arr);
            tmp = arr[k]; arr[k] = arr[i]; arr[i] = tmp;
        }
    }

    permute9(0, &best_ioc9, best_p9, &best_period9, p);
    printf("Best IoC for 9 blocks of 56: %.5f (period %d) | Perm: [", best_ioc9, best_period9);
    for (int i = 0; i < 9; i++) printf("%d%s", best_p9[i], i == 8 ? "" : ", ");
    printf("]\n");

    return 0;
}
