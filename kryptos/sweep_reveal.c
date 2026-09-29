#include <stdio.h>
#include <stdlib.h>
#include <string.h>

const char *CT9 = "KSYAWFEYYOISZGEUFBLYATAIBYFAQBQYYVDWJKLJXMYIEPIFVHPQNHZGSUHUUDXLEHRHUMALHEGLHXSJMUXGNUIVBXGUJHZRZGUSVHMLSCTSUQXHSUMQQIFUQGKHJGUQGLHDKEWSKAMHIJXD";
const int N = 144;

double calc_ioc(const char *s, int len) {
    if (len < 2) return 0.0;
    int counts[26] = {0};
    for (int i = 0; i < len; i++) counts[s[i] - 'A']++;
    double sum = 0;
    for (int i = 0; i < 26; i++) sum += counts[i] * (counts[i] - 1);
    return sum / ((double)len * (len - 1));
}

// Generate permutations and test average slice IoC
double best_ioc_for_config(int width, int unit, int *best_period, int *best_perm_out) {
    int total_units = N / unit;
    if (total_units % width != 0) return 0.0;
    int rows = total_units / width;
    
    // We only brute force if width <= 8
    if (width > 8) return 0.0;
    
    int p[8];
    for (int i = 0; i < width; i++) p[i] = i;
    
    double max_avg_ioc = 0.0;
    
    // Helper to run all perms
    // We use standard Heap's algorithm or recursion
    int c[8] = {0};
    int i = 0;
    char undone[145];
    undone[144] = '\0';
    
    while (1) {
        // Decode with perm p
        // In columnar decoding: ciphertext has columns in order p[0], p[1], ...
        // Each column has 'rows' units, so rows * unit characters.
        for (int col = 0; col < width; col++) {
            int orig_col = p[col];
            for (int r = 0; r < rows; r++) {
                for (int u = 0; u < unit; u++) {
                    undone[(r * width + orig_col) * unit + u] = CT9[(col * rows + r) * unit + u];
                }
            }
        }
        
        // Test periods from 2 to 20
        for (int per = 2; per <= 20; per++) {
            double sum_ioc = 0.0;
            char slice[145];
            for (int rem = 0; rem < per; rem++) {
                int slen = 0;
                for (int idx = rem; idx < N; idx += per) {
                    slice[slen++] = undone[idx];
                }
                sum_ioc += calc_ioc(slice, slen);
            }
            double avg = sum_ioc / per;
            if (avg > max_avg_ioc) {
                max_avg_ioc = avg;
                *best_period = per;
                for (int k = 0; k < width; k++) best_perm_out[k] = p[k];
            }
        }
        
        // Next perm
        while (i < width && c[i] >= i) {
            c[i] = 0;
            i++;
        }
        if (i >= width) break;
        if (i % 2 == 0) {
            int tmp = p[0]; p[0] = p[i]; p[i] = tmp;
        } else {
            int tmp = p[c[i]]; p[c[i]] = p[i]; p[i] = tmp;
        }
        c[i]++;
        i = 0;
    }
    return max_avg_ioc;
}

int main() {
    printf("Sweeping all (width, unit) geometries on PK9:\n");
    for (int unit = 1; unit <= 4; unit++) {
        for (int width = 2; width <= 8; width++) {
            if ((N / unit) % width != 0) continue;
            int best_p = 0;
            int best_perm[8] = {0};
            double ioc = best_ioc_for_config(width, unit, &best_p, best_perm);
            printf("unit=%d, width=%d: max_ioc=%.5f (period=%2d), perm=[", unit, width, ioc, best_p);
            for (int k = 0; k < width; k++) printf("%d%s", best_perm[k], k == width - 1 ? "" : ", ");
            printf("]\n");
        }
    }
    return 0;
}
