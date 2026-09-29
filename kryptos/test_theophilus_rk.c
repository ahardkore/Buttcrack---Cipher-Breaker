#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <ctype.h>
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

const char *PK8_CT = "COPVEJJVSVURTVIPYOTPLHGBTMAUCCPESIWIGZBWSJPKTRPUEKQFIFCLHMXTHIMHWOYIGURBOMPARCVXVKBDDVBVHDRHGCVNWWVLBMYWMWHICFIXZWBVZYCQGNOGJGUMLNPUTHQCXNWPQZOIRJZGSWVPY";
const char *PK9_CT = "KSYAWFEYYOISZGEUFBLYATAIBYFAQBQYYVDWJKLJXMYIEPIFVHPQNHZGSUHUUDXLEHRHUMALHEGLHXSJMUXGNUIVBXGUJHZRZGUSVHMLSCTSUQXHSUMQQIFUQGKHJGUQGLHDKEWSKAMHIJXD";
const char *PK10_CT = "UBINFYJSFQXQVRLJJAJDGBXIWKDMAREZTGSHQWRXCHEPCLYSDNGYRRBTCVOZJYVLYWREJTCDOYVEYCJJVZKRMKTRPGVHRWMJSRCSHXZMJEVQKJYJJAYZKDFQBGRSWXATJMEXKFXAXKSIZXOERFESNVCGCNRHEOBCNCBUPXTJJRCIMDMRUVZWRDRRFXAPGPIGSPLILFIZSTDZYOVQGGDFUFZPUOJPJVWREUVRQIYPCEHGYUZUKWTFXELUNOKBANZFTFRMXZSXXQSBGPCWGXPFSCANSVUYLMTZIRCCCJJPBQAEPWVCDIMLOPOXQEGJKVQIVHEFAPQMVCYSQAFKCTYTPAOOJZCWIPGDPAFTINBFFHVXYEQXCEIDJJOUABBAHSWKHGMLJBXDSQEFBBDLTLJPLZPIPPTRGDRZIZPUPYJODOCSOYCZZWTKYWMBQTFMFEQZWVPQYLJTMEYKYBNOPEPUMHCFJSLFWOISWLKFFABTYFQDTEQBDELIEOZQ";

void scan_corpus(const char *target_name, const char *ct, const char *corpus, int corpus_len) {
    int n = strlen(ct);
    printf("Scanning %s (len %d) against corpus (len %d)...\n", target_name, n, corpus_len);

    float global_best_sc = -999.0f;
    char global_best_pt[600];
    int global_best_pos = 0;
    char global_best_mode[32];

    for (int model = 0; model < 4; model++) {
        const char *alpha = (model < 2) ? KRYPTOS : STD;
        int is_beau = (model % 2 == 1);
        const char *alpha_name = (model < 2) ? "KRYPTOS" : "STD";
        const char *mode_name = is_beau ? "Beaufort" : "Vigenere";

        int c_idx[600];
        int alpha_to_std[26];
        for (int i = 0; i < 26; i++) alpha_to_std[i] = alpha[i] - 'A';
        for (int i = 0; i < n; i++) c_idx[i] = strchr(alpha, ct[i]) - alpha;

        static int corpus_idx[500000];
        for (int i = 0; i < corpus_len; i++) corpus_idx[i] = strchr(alpha, corpus[i]) - alpha;

        #pragma omp parallel for schedule(dynamic)
        for (int i = 0; i <= corpus_len - n; i++) {
            int pt[600];
            for (int j = 0; j < n; j++) {
                int k = corpus_idx[i + j];
                int p = is_beau ? ((k - c_idx[j] + 26) % 26) : ((c_idx[j] - k + 26) % 26);
                pt[j] = alpha_to_std[p];
            }
            float sc = 0.0f;
            for (int j = 0; j < n - 3; j++) sc += quad[pt[j]][pt[j+1]][pt[j+2]][pt[j+3]];
            sc /= (n - 3);

            if (sc > -6.0f) {
                #pragma omp critical
                {
                    printf("  HIT! [%s %s pos %d] Score: %6.4f | ", alpha_name, mode_name, i, sc);
                    for (int j = 0; j < 50; j++) printf("%c", 'A' + pt[j]);
                    printf("\n");
                    fflush(stdout);
                }
            }

            #pragma omp critical
            {
                if (sc > global_best_sc) {
                    global_best_sc = sc;
                    global_best_pos = i;
                    sprintf(global_best_mode, "%s %s", alpha_name, mode_name);
                    for (int j = 0; j < n; j++) global_best_pt[j] = 'A' + pt[j];
                    global_best_pt[n] = '\0';
                }
            }
        }
    }
    printf("%s: Best score = %6.4f [%s pos %d] | %s\n\n",
           target_name, global_best_sc, global_best_mode, global_best_pos, global_best_pt);
}

int main() {
    load_quadgrams();

    FILE *f = fopen("theophilus_hendrie.txt", "r");
    if (!f) { printf("Cannot open theophilus_hendrie.txt\n"); return 1; }
    fseek(f, 0, SEEK_END);
    long sz = ftell(f);
    fseek(f, 0, SEEK_SET);
    char *raw = malloc(sz + 1);
    fread(raw, 1, sz, f);
    fclose(f);
    raw[sz] = '\0';

    // Filter to only Book III (pos 512119 to end)
    char *book3 = raw + 512119;
    char *clean = malloc(sz + 1);
    int clean_len = 0;
    for (int i = 0; book3[i]; i++) {
        if (isalpha(book3[i])) clean[clean_len++] = toupper(book3[i]);
    }
    clean[clean_len] = '\0';
    printf("Book III clean letters: %d\n", clean_len);

    scan_corpus("PK8", PK8_CT, clean, clean_len);
    scan_corpus("PK9", PK9_CT, clean, clean_len);
    scan_corpus("PK10", PK10_CT, clean, clean_len);

    free(raw);
    free(clean);
    return 0;
}
