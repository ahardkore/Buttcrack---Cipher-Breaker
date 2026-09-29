#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

#define N 144
#define W 12
#define H 12

static float quad[26][26][26][26];

void load_quads() {
    for (int a=0; a<26; a++)
        for (int b=0; b<26; b++)
            for (int c=0; c<26; c++)
                for (int d=0; d<26; d++)
                    quad[a][b][c][d] = -9.5f;
    FILE *f = fopen("english_quadgrams.txt", "r");
    if (!f) return;
    char q[16]; float cnt;
    double total = 0;
    while (fscanf(f, "%s %f", q, &cnt) == 2) {
        if (strlen(q) == 4) total += cnt;
    }
    rewind(f);
    while (fscanf(f, "%s %f", q, &cnt) == 2) {
        if (strlen(q) == 4) {
            int a = q[0]-'A', b = q[1]-'A', c = q[2]-'A', d = q[3]-'A';
            if (a>=0 && a<26 && b>=0 && b<26 && c>=0 && c<26 && d>=0 && d<26) {
                quad[a][b][c][d] = (float)log10((cnt + 0.01) / total);
            }
        }
    }
    fclose(f);
}

static const char *KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
static const char *PK9_REAL = "KSYAWFEYYOISZGEUFBLYATAIBYFAQBQYYVDWJKLJXMYIEPIFVHPQNHZGSUHUUDXLEHRHUMALHEGLHXSJMUXGNUIVBXGUJHZRZGUSVHMLSCTSUQXHSUMQQIFUQGKHJGUQGLHDKEWSKAMHIJXD";

static int ct_kr[N];
static int k_to_std[26];
static int std_to_k[26];

void init() {
    for (int i=0; i<26; i++) {
        k_to_std[i] = KRYPTOS[i] - 'A';
        std_to_k[KRYPTOS[i] - 'A'] = i;
    }
    for (int i=0; i<N; i++) {
        ct_kr[i] = std_to_k[PK9_REAL[i] - 'A'];
    }
}

static const int perm[W] = {
    3, 0, 6, 2, 11, 5, 4, 1, 9, 7, 8, 10
};

// Common word dictionary hash table for fast lookups
#define HASH_SIZE 65536
typedef struct WordNode {
    char word[16];
    struct WordNode *next;
} WordNode;

static WordNode *dict[HASH_SIZE];

unsigned int hash_str(const char *s, int len) {
    unsigned int h = 5381;
    for (int i=0; i<len; i++) h = ((h << 5) + h) + s[i];
    return h % HASH_SIZE;
}

void load_dict() {
    FILE *f = fopen("theophilus_hendrie.txt", "r");
    if (!f) return;
    char buf[64];
    while (fscanf(f, "%63s", buf) == 1) {
        char clean[16]; int len = 0;
        for (int i=0; buf[i] && len < 15; i++) {
            char c = buf[i];
            if (c >= 'a' && c <= 'z') c -= 32;
            if (c >= 'A' && c <= 'Z') clean[len++] = c;
        }
        clean[len] = '\0';
        if (len >= 3 && len <= 12) {
            unsigned int h = hash_str(clean, len);
            int exists = 0;
            for (WordNode *p = dict[h]; p; p = p->next) {
                if (strcmp(p->word, clean) == 0) { exists = 1; break; }
            }
            if (!exists) {
                WordNode *node = (WordNode*)malloc(sizeof(WordNode));
                strcpy(node->word, clean);
                node->next = dict[h];
                dict[h] = node;
            }
        }
    }
    fclose(f);
}

int is_word(const char *s, int len) {
    if (len < 3 || len > 12) return 0;
    unsigned int h = hash_str(s, len);
    for (WordNode *p = dict[h]; p; p = p->next) {
        if (strncmp(p->word, s, len) == 0 && p->word[len] == '\0') return 1;
    }
    return 0;
}

float score_text_with_words(const char *t) {
    float q_sc = 0.0f;
    for (int i=0; i<N-3; i++) {
        q_sc += quad[t[i]-'A'][t[i+1]-'A'][t[i+2]-'A'][t[i+3]-'A'];
    }
    float avg_q = q_sc / (N - 3);
    
    // Scan for words across the text
    float word_bonus = 0.0f;
    for (int i=0; i<N; i++) {
        for (int l=3; l<=8 && i+l<=N; l++) {
            if (is_word(t + i, l)) {
                word_bonus += (float)l * 0.15f;
            }
        }
    }
    return avg_q + word_bonus;
}

void build_text(const int *shifts, char *out) {
    char z[N];
    for (int i=0; i<N; i++) {
        int p_kr = (ct_kr[i] - shifts[i % 28] + 26) % 26;
        z[i] = k_to_std[p_kr] + 'A';
    }
    int idx = 0;
    for (int r=0; r<H; r++) {
        for (int c=0; c<W; c++) {
            out[idx++] = z[perm[c] * H + r];
        }
    }
    out[N] = '\0';
}

int main() {
    load_quads();
    load_dict();
    init();
    
    int shifts[28] = {
        5, 4, 9, 15, 16, 5, 6, 14, 5, 25, 20, 21, 10, 6, 14, 11, 7, 25, 10, 24, 22, 23, 18, 1, 7, 10, 7, 3
    };
    
    char pt[N+1];
    build_text(shifts, pt);
    float best_sc = score_text_with_words(pt);
    printf("Initial Combined Score: %.4f\n", best_sc);
    printf("Initial PT: %s\n", pt);
    
    int improved = 1;
    int cycle = 0;
    while (improved && cycle < 10) {
        improved = 0;
        cycle++;
        for (int s_idx = 0; s_idx < 28; s_idx++) {
            int orig_val = shifts[s_idx];
            int best_val = orig_val;
            float local_best = best_sc;
            
            for (int v = 0; v < 26; v++) {
                shifts[s_idx] = v;
                char cur_pt[N+1];
                build_text(shifts, cur_pt);
                float sc = score_text_with_words(cur_pt);
                if (sc > local_best) {
                    local_best = sc;
                    best_val = v;
                    strcpy(pt, cur_pt);
                }
            }
            if (best_val != orig_val) {
                shifts[s_idx] = best_val;
                best_sc = local_best;
                improved = 1;
                printf("Cycle %d: shift[%d] changed %d -> %d | New Score: %.4f\n",
                       cycle, s_idx, orig_val, best_val, best_sc);
            } else {
                shifts[s_idx] = orig_val;
            }
        }
    }
    
    printf("\nFinal Converged Shifts: [");
    for (int i=0; i<28; i++) printf("%d%s", shifts[i], i==27?"":", ");
    printf("]\n");
    printf("Final Combined Score: %.4f\n", best_sc);
    printf("Final Plaintext:\n");
    for (int r=0; r<H; r++) {
        char row[W+1];
        strncpy(row, pt + r*W, W);
        row[W] = '\0';
        printf("Row %2d: %s\n", r, row);
    }
    return 0;
}
