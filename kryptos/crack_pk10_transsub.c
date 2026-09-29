#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <time.h>
#include <omp.h>

static float quad[26][26][26][26];

void load_quadgrams() {
    FILE *f = fopen("english_quadgrams.txt", "r");
    if (!f) { printf("Failed to open english_quadgrams.txt\n"); exit(1); }
    char line[128];
    double total = 0;
    static double counts[26][26][26][26];
    memset(counts, 0, sizeof(counts));
    while (fgets(line, sizeof(line), f)) {
        char gram[5]; double count;
        if (sscanf(line, "%4s %lf", gram, &count) == 2) {
            int a = gram[0] - 'A', b = gram[1] - 'A', c = gram[2] - 'A', d = gram[3] - 'A';
            if (a>=0 && a<26 && b>=0 && b<26 && c>=0 && c<26 && d>=0 && d<26) {
                counts[a][b][c][d] = count;
                total += count;
            }
        }
    }
    fclose(f);
    float floor_val = log10f(0.01f / total);
    for (int a=0; a<26; a++)
        for (int b=0; b<26; b++)
            for (int c=0; c<26; c++)
                for (int d=0; d<26; d++)
                    quad[a][b][c][d] = counts[a][b][c][d] > 0 ? log10f(counts[a][b][c][d] / total) : floor_val;
}

const char *KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
const char *STD = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";
const char *PK10_CT = "UBINFYJSFQXQVRLJJAJDGBXIWKDMAREZTGSHQWRXCHEPCLYSDNGYRRBTCVOZJYVLYWREJTCDOYVEYCJJVZKRMKTRPGVHRWMJSRCSHXZMJEVQKJYJJAYZKDFQBGRSWXATJMEXKFXAXKSIZXOERFESNVCGCNRHEOBCNCBUPXTJJRCIMDMRUVZWRDRRFXAPGPIGSPLILFIZSTDZYOVQGGDFUFZPUOJPJVWREUVRQIYPCEHGYUZUKWTFXELUNOKBANZFTFRMXZSXXQSBGPCWGXPFSCANSVUYLMTZIRCCCJJPBQAEPWVCDIMLOPOXQEGJKVQIVHEFAPQMVCYSQAFKCTYTPAOOJZCWIPGDPAFTINBFFHVXYEQXCEIDJJOUABBAHSWKHGMLJBXDSQEFBBDLTLJPLZPIPPTRGDRZIZPUPYJODOCSOYCZZWTKYWMBQTFMFEQZWVPQYLJTMEYKYBNOPEPUMHCFJSLFWOISWLKFFABTYFQDTEQBDELIEOZQ";

static inline float score_text(const int *txt, int n) {
    float sc = 0.0f;
    for (int i = 0; i < n - 3; i++) {
        sc += quad[txt[i]][txt[i+1]][txt[i+2]][txt[i+3]];
    }
    return sc / (n - 3);
}

const char *KEYWORDS[] = {
    "PROVENANCE", "PORTAL", "PENTIMENTO", "ORDINATE", "KRYPTOS",
    "PELLEGRIN", "WHITESMITH", "PALIMPSEST", "ABSCISSA", "MARGINS",
    "HEARTH", "BELLOWS", "DRAWPLATE", "CRUCIBLE", "ANNEALING",
    "TEMPERING", "FURNACE", "HAMMER", "ANVIL", "TONGS",
    "NEEDLE", "UNRAVEL", "KNOT", "FIBERS", "FURLONGS", "SURGICAL",
    "VIENNESE", "BERN", "EASTNORTHEAST", "BERLINCLOCK", "TENYEARS"
};
const int NUM_KEYWORDS = sizeof(KEYWORDS) / sizeof(KEYWORDS[0]);

int next_perm(int *a, int n) {
    int i = n - 2;
    while (i >= 0 && a[i] >= a[i + 1]) i--;
    if (i < 0) return 0;
    int j = n - 1;
    while (a[j] <= a[i]) j--;
    int t = a[i]; a[i] = a[j]; a[j] = t;
    int l = i + 1, r = n - 1;
    while (l < r) {
        t = a[l]; a[l] = a[r]; a[r] = t;
        l++; r--;
    }
    return 1;
}

void test_exhaustive_width(int W, const char *alpha, const char *alpha_name) {
    int N = strlen(PK10_CT);
    if (N % W != 0) return;
    int H = N / W;

    int c_idx[600];
    int alpha_to_std[26];
    for (int i = 0; i < 26; i++) alpha_to_std[i] = alpha[i] - 'A';
    for (int i = 0; i < N; i++) c_idx[i] = strchr(alpha, PK10_CT[i]) - alpha;

    printf("Exhaustive W=%d (H=%d) under %s...\n", W, H, alpha_name);

    #pragma omp parallel for schedule(dynamic)
    for (int kw_idx = 0; kw_idx < NUM_KEYWORDS; kw_idx++) {
        const char *kw = KEYWORDS[kw_idx];
        int kw_len = strlen(kw);
        int key_shifts[100];
        for (int i = 0; i < kw_len; i++) key_shifts[i] = strchr(alpha, kw[i]) - alpha;

        int order[64];
        for (int i = 0; i < W; i++) order[i] = i;

        int z[600], pt[600];
        float best_sc = -999.0f;
        int best_order[64];
        char best_pt[600];

        do {
            // un-transpose: column order[k] has characters c_idx[k*H ... (k+1)*H - 1]
            for (int k = 0; k < W; k++) {
                int col = order[k];
                for (int r = 0; r < H; r++) {
                    z[r * W + col] = c_idx[k * H + r];
                }
            }
            // Quagmire III decrypt: P_i = (Z_i - K_{i % kw_len}) mod 26
            for (int i = 0; i < N; i++) {
                int p = (z[i] - key_shifts[i % kw_len] + 26) % 26;
                pt[i] = alpha_to_std[p];
            }
            float sc = score_text(pt, N);
            if (sc > best_sc) {
                best_sc = sc;
                memcpy(best_order, order, sizeof(int) * W);
                for (int i = 0; i < N; i++) best_pt[i] = 'A' + pt[i];
                best_pt[N] = '\0';
            }
        } while (next_perm(order, W));

        if (best_sc > -6.0f) {
            #pragma omp critical
            {
                printf("  [W=%d %s] KEY: %-12s | SCORE: %6.4f | %s\n",
                       W, alpha_name, kw, best_sc, best_pt);
                fflush(stdout);
            }
        }
    }
}

void test_sa_width(int W, const char *alpha, const char *alpha_name, int restarts) {
    int N = strlen(PK10_CT);
    if (N % W != 0) return;
    int H = N / W;

    int c_idx[600];
    int alpha_to_std[26];
    for (int i = 0; i < 26; i++) alpha_to_std[i] = alpha[i] - 'A';
    for (int i = 0; i < N; i++) c_idx[i] = strchr(alpha, PK10_CT[i]) - alpha;

    printf("SA W=%d (H=%d, %d restarts) under %s...\n", W, H, restarts, alpha_name);

    #pragma omp parallel for schedule(dynamic)
    for (int kw_idx = 0; kw_idx < NUM_KEYWORDS; kw_idx++) {
        const char *kw = KEYWORDS[kw_idx];
        int kw_len = strlen(kw);
        int key_shifts[100];
        for (int i = 0; i < kw_len; i++) key_shifts[i] = strchr(alpha, kw[i]) - alpha;

        unsigned int seed = 12345 + omp_get_thread_num() * 1111 + kw_idx * 31;
        float kw_best_sc = -999.0f;
        char kw_best_pt[600];

        for (int r = 0; r < restarts; r++) {
            int order[64];
            for (int i = 0; i < W; i++) order[i] = i;
            // shuffle order
            for (int i = W - 1; i > 0; i--) {
                int j = rand_r(&seed) % (i + 1);
                int t = order[i]; order[i] = order[j]; order[j] = t;
            }

            int z[600], pt[600];
            for (int k = 0; k < W; k++) {
                int col = order[k];
                for (int row = 0; row < H; row++) z[row * W + col] = c_idx[k * H + row];
            }
            for (int i = 0; i < N; i++) pt[i] = alpha_to_std[(z[i] - key_shifts[i % kw_len] + 26) % 26];
            float cur_sc = score_text(pt, N);

            float T = 5.0f, T_min = 0.05f, cooling = 0.999f;
            for (int step = 0; step < 3000 && T > T_min; step++) {
                T *= cooling;
                int i1 = rand_r(&seed) % W;
                int i2 = rand_r(&seed) % W;
                if (i1 == i2) continue;

                int t = order[i1]; order[i1] = order[i2]; order[i2] = t;

                for (int k = 0; k < W; k++) {
                    int col = order[k];
                    for (int row = 0; row < H; row++) z[row * W + col] = c_idx[k * H + row];
                }
                for (int i = 0; i < N; i++) pt[i] = alpha_to_std[(z[i] - key_shifts[i % kw_len] + 26) % 26];
                float new_sc = score_text(pt, N);
                float delta = new_sc - cur_sc;

                if (delta > 0 || expf(delta / T) > ((float)rand_r(&seed) / RAND_MAX)) {
                    cur_sc = new_sc;
                } else {
                    t = order[i1]; order[i1] = order[i2]; order[i2] = t;
                }
            }

            if (cur_sc > kw_best_sc) {
                kw_best_sc = cur_sc;
                for (int k = 0; k < W; k++) {
                    int col = order[k];
                    for (int row = 0; row < H; row++) z[row * W + col] = c_idx[k * H + row];
                }
                for (int i = 0; i < N; i++) kw_best_pt[i] = 'A' + alpha_to_std[(z[i] - key_shifts[i % kw_len] + 26) % 26];
                kw_best_pt[N] = '\0';
            }
        }

        if (kw_best_sc > -5.8f) {
            #pragma omp critical
            {
                printf("  [W=%d %s] KEY: %-12s | SCORE: %6.4f | %s\n",
                       W, alpha_name, kw, kw_best_sc, kw_best_pt);
                fflush(stdout);
            }
        }
    }
}

int main() {
    load_quadgrams();
    // Test exhaustive widths 6, 7, 8
    for (int w = 6; w <= 8; w++) {
        test_exhaustive_width(w, KRYPTOS, "KRYPTOS");
        test_exhaustive_width(w, STD, "STD");
    }
    // Test SA widths 9, 12, 14, 18
    int widths[] = {9, 12, 14, 18, 21, 24, 28};
    for (int i = 0; i < sizeof(widths)/sizeof(widths[0]); i++) {
        test_sa_width(widths[i], KRYPTOS, "KRYPTOS", 30);
        test_sa_width(widths[i], STD, "STD", 30);
    }
    return 0;
}
