#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

#define N 144
static const char *ALPH = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
static const char *PK9_CT = "KSYAWFEYYOISZGEUFBLYATAIBYFAQBQYYVDWJKLJXMYIEPIFVHPQNHZGSUHUUDXLEHRHUMALHEGLHXSJMUXGNUIVBXGUJHZRZGUSVHMLSCTSUQXHSUMQQIFUQGKHJGUQGLHDKEWSKAMHIJXD";

static int std_to_kr[26];
static int ct_kr[N];
static int is_rare[26];

static const double eng_freq[26] = {
    0.08167, 0.01492, 0.02782, 0.04253, 0.12702,
    0.02228, 0.02015, 0.06094, 0.06966, 0.00153,
    0.00772, 0.04025, 0.02406, 0.06749, 0.07507,
    0.01929, 0.00095, 0.05987, 0.06327, 0.09056,
    0.02758, 0.00978, 0.02360, 0.00150, 0.01974,
    0.00074
};

static void init_tables(void) {
    for (int i = 0; i < 26; i++) std_to_kr[ALPH[i] - 'A'] = i;
    for (int i = 0; i < N; i++) ct_kr[i] = std_to_kr[PK9_CT[i] - 'A'];
    memset(is_rare, 0, sizeof(is_rare));
    is_rare['Q' - 'A'] = 1;
    is_rare['X' - 'A'] = 1;
    is_rare['Z' - 'A'] = 1;
    is_rare['J' - 'A'] = 1;
}

int main(void) {
    init_tables();

    FILE *f = fopen("words_7.txt", "r");
    char w[16];
    double best_chi2 = 1e9;
    char best_w[16];
    int best_mode = 0;
    int best_rare = 0;

    while (fscanf(f, "%15s", w) == 1) {
        if (strlen(w) != 7) continue;
        int k[7];
        for (int j = 0; j < 7; j++) k[j] = std_to_kr[w[j] - 'A'];

        for (int is_beau = 0; is_beau < 2; is_beau++) {
            int counts[26] = {0};
            for (int t = 0; t < N; t++) {
                int shift = k[t % 7];
                int p = is_beau ? (shift - ct_kr[t] + 26) % 26 : (ct_kr[t] - shift + 26) % 26;
                int ch = ALPH[p] - 'A';
                counts[ch]++;
            }

            int rare = counts['Q' - 'A'] + counts['X' - 'A'] + counts['Z' - 'A'] + counts['J' - 'A'];
            if (rare > 6) continue;

            double chi2 = 0;
            for (int a = 0; a < 26; a++) {
                double exp_cnt = N * eng_freq[a];
                double diff = counts[a] - exp_cnt;
                chi2 += (diff * diff) / exp_cnt;
            }

            if (chi2 < best_chi2) {
                best_chi2 = chi2;
                strcpy(best_w, w);
                best_mode = is_beau;
                best_rare = rare;
            }
        }
    }
    fclose(f);

    printf("Best pure period-7 word on PK9:\n");
    printf("Word: %s | Mode: %s | Chi2: %.2f | Rare: %d\n",
        best_w, best_mode ? "Beaufort" : "Vigenere", best_chi2, best_rare);

    return 0;
}
