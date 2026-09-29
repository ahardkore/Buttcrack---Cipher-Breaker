#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>

#define N 144
#define W 12
#define H (N / W)

const char *KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
const char *PK9_CT = "KSYAWFEYYOISZGEUFBLYATAIBYFAQBQYYVDWJKLJXMYIEPIFVHPQNHZGSUHUUDXLEHRHUMALHEGLHXSJMUXGNUIVBXGUJHZRZGUSVHMLSCTSUQXHSUMQQIFUQGKHJGUQGLHDKEWSKAMHIJXD";

static int c_idx[N];
static int k_to_std[26];
static float quad[26][26][26][26];

void load_quadgrams() {
    for (int a = 0; a < 26; a++)
        for (int b = 0; b < 26; b++)
            for (int c = 0; c < 26; c++)
                for (int d = 0; d < 26; d++)
                    quad[a][b][c][d] = -9.5f;

    FILE *f = fopen("english_quads.tsv", "r");
    if (!f) return;
    char q[16]; float sc;
    while (fscanf(f, "%s %f", q, &sc) == 2) {
        if (strlen(q) == 4) {
            int a = q[0]-'A', b = q[1]-'A', c = q[2]-'A', d = q[3]-'A';
            if (a>=0 && a<26 && b>=0 && b<26 && c>=0 && c<26 && d>=0 && d<26) {
                quad[a][b][c][d] = sc;
            }
        }
    }
    fclose(f);
}

void init_tables() {
    for (int i = 0; i < 26; i++) {
        k_to_std[i] = KRYPTOS[i] - 'A';
    }
    for (int i = 0; i < N; i++) {
        c_idx[i] = strchr(KRYPTOS, PK9_CT[i]) - KRYPTOS;
    }
}

void single_col_decode(const int *in, int len, int width, const int *order, int *out) {
    int h = len / width;
    int grid[20][20];
    int k = 0;
    for (int m = 0; m < width; m++) {
        int col = order[m];
        for (int r = 0; r < h; r++) {
            grid[r][col] = in[k++];
        }
    }
    int idx = 0;
    for (int r = 0; r < h; r++) {
        for (int c = 0; c < width; c++) {
            out[idx++] = grid[r][c];
        }
    }
}

float compute_coset_ioc(const int *text, int len, int P) {
    float total = 0.0f;
    int slices = 0;
    for (int r = 0; r < P; r++) {
        int counts[26] = {0};
        int cnt = 0;
        for (int i = r; i < len; i += P) {
            counts[text[i]]++;
            cnt++;
        }
        if (cnt >= 2) {
            int sum_sq = 0;
            for (int c = 0; c < 26; c++) sum_sq += counts[c] * (counts[c] - 1);
            total += (float)sum_sq / (float)(cnt * (cnt - 1));
            slices++;
        }
    }
    return slices > 0 ? (total / slices) : 0.0f;
}

void word_to_order(const char *w, int len, int *order) {
    typedef struct { char ch; int orig; } Pair;
    Pair p[32];
    for (int i = 0; i < len; i++) { p[i].ch = w[i]; p[i].orig = i; }
    for (int i = 0; i < len - 1; i++) {
        for (int j = i + 1; j < len; j++) {
            if (p[j].ch < p[i].ch || (p[j].ch == p[i].ch && p[j].orig < p[i].orig)) {
                Pair tmp = p[i]; p[i] = p[j]; p[j] = tmp;
            }
        }
    }
    for (int i = 0; i < len; i++) order[i] = p[i].orig;
}

typedef struct {
    char word[16];
    int order[12];
} Word12;

int main() {
    init_tables();
    load_quadgrams();

    // Load all 12-letter words from words_12.txt
    FILE *f = fopen("words_12.txt", "r");
    if (!f) return 1;

    Word12 *words = malloc(25000 * sizeof(Word12));
    int n_words = 0;
    char line[64];
    while (fgets(line, sizeof(line), f)) {
        char w[32];
        if (sscanf(line, "%s", w) == 1 && strlen(w) == 12) {
            strcpy(words[n_words].word, w);
            word_to_order(w, 12, words[n_words].order);
            n_words++;
        }
    }
    fclose(f);
    printf("Loaded %d 12-letter words\n", n_words);

    // Filter thematic 12-letter words
    const char *thematic_patterns[] = {
        "SMITH", "WORK", "CRAFT", "FORG", "METAL", "GOLD", "SILVER", "NEEDLE",
        "HAMMER", "ANVIL", "IRON", "STEEL", "BRASS", "COPPER", "TEMPER",
        "QUENCH", "ANNEAL", "WIRE", "DRAW", "BLOW", "FIRE", "COAL", "HEARTH",
        "FURNACE", "CRUCIBLE", "PORTAL", "TEMPLE", "CHURCH", "MONK", "PRIEST",
        "MASTER", "MAKING", "STUDY", "TENYEAR", "YEARS", "MINUTE", "SECOND"
    };
    int n_patterns = sizeof(thematic_patterns) / sizeof(thematic_patterns[0]);

    Word12 *thematic = malloc(5000 * sizeof(Word12));
    int n_them = 0;
    for (int i = 0; i < n_words; i++) {
        int is_them = 0;
        for (int p = 0; p < n_patterns; p++) {
            if (strstr(words[i].word, thematic_patterns[p])) {
                is_them = 1;
                break;
            }
        }
        if (is_them) {
            thematic[n_them++] = words[i];
        }
    }
    printf("Filtered %d thematic 12-letter words\n", n_them);

    // Test Pipeline B: P -> Q3 -> Y -> T1 -> T2 -> C (Double columnar then Q3)
    // Here Y = T1^-1(T2^-1(C))
    long long total_pairs = (long long)n_them * n_them;
    printf("\n=== Testing Pipeline B: Double Columnar (12, 12) on %lld pairs ===\n", total_pairs);

    float best_ioc7 = 0.0f;
    char best_w1_7[16] = "", best_w2_7[16] = "";
    float best_ioc12 = 0.0f;
    char best_w1_12[16] = "", best_w2_12[16] = "";

    double t0 = omp_get_wtime();

    #pragma omp parallel
    {
        float local_ioc7 = 0.0f;
        char local_w1_7[16] = "", local_w2_7[16] = "";
        float local_ioc12 = 0.0f;
        char local_w1_12[16] = "", local_w2_12[16] = "";

        #pragma omp for schedule(dynamic, 100)
        for (long long idx = 0; idx < total_pairs; idx++) {
            int i1 = idx / n_them;
            int i2 = idx % n_them;

            int inter[N], Y[N];
            single_col_decode(c_idx, N, 12, thematic[i2].order, inter);
            single_col_decode(inter, N, 12, thematic[i1].order, Y);

            float ioc7 = compute_coset_ioc(Y, N, 7);
            if (ioc7 > local_ioc7) {
                local_ioc7 = ioc7;
                strcpy(local_w1_7, thematic[i1].word);
                strcpy(local_w2_7, thematic[i2].word);
            }

            float ioc12 = compute_coset_ioc(Y, N, 12);
            if (ioc12 > local_ioc12) {
                local_ioc12 = ioc12;
                strcpy(local_w1_12, thematic[i1].word);
                strcpy(local_w2_12, thematic[i2].word);
            }
        }

        #pragma omp critical
        {
            if (local_ioc7 > best_ioc7) {
                best_ioc7 = local_ioc7;
                strcpy(best_w1_7, local_w1_7);
                strcpy(best_w2_7, local_w2_7);
            }
            if (local_ioc12 > best_ioc12) {
                best_ioc12 = local_ioc12;
                strcpy(best_w1_12, local_w1_12);
                strcpy(best_w2_12, local_w2_12);
            }
        }
    }

    double elapsed = omp_get_wtime() - t0;
    printf("Completed in %.3f s (%.1f million pairs/sec)\n", elapsed, total_pairs / (elapsed * 1e6));
    printf("Best Period  7 Coset IoC: %.5f | Words: (%s, %s)\n", best_ioc7, best_w1_7, best_w2_7);
    printf("Best Period 12 Coset IoC: %.5f | Words: (%s, %s)\n", best_ioc12, best_w1_12, best_w2_12);

    return 0;
}
