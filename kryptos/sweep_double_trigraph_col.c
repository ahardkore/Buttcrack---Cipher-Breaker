#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <omp.h>

#define N 144
#define N_ATOMS 48
#define UNIT 3

static float quad[26][26][26][26];

void load_quads() {
    for (int a=0; a<26; a++)
        for (int b=0; b<26; b++)
            for (int c=0; c<26; c++)
                for (int d=0; d<26; d++)
                    quad[a][b][c][d] = -9.5f;
    FILE *f = fopen("english_quadgrams.txt", "r");
    if (!f) { printf("Cannot open english_quadgrams.txt\n"); exit(1); }
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

static const char *PK9_CT = "KSYAWFEYYOISZGEUFBLYATAIBYFAQBQGZGSMMJHJQNHSVHAWFLHXLSKALEHHSUUFBVBXJXMMHIRHUMQQLYAGUJYIEJXDMALIFUTAIHZRPIFLSEYYSJMQYYLHDUHUCTSOISUXGVDWKEWUDXUQXZGENUIJK";
static const char *KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ";

// Split PK9_CT into 48 trigraph atoms
static char ct_atoms[N_ATOMS][UNIT + 1];

void init_atoms() {
    for (int i=0; i<N_ATOMS; i++) {
        memcpy(ct_atoms[i], PK9_CT + i * UNIT, UNIT);
        ct_atoms[i][UNIT] = '\0';
    }
}

// Atom-level columnar undo map:
// For width w, each column has h = 48 / w atoms.
// Ciphertext atoms are filled column by column in order o.
// col c receives atoms c*h .. (c+1)*h - 1.
// In the grid, row r, col o[c] has atom:
// pt_atom[r * w + o[c]] = ct_atom[c * h + r]
void get_atom_map(int w, const int *o, int *map) {
    int h = N_ATOMS / w;
    for (int c = 0; c < w; c++) {
        int col = o[c];
        for (int r = 0; r < h; r++) {
            map[r * w + col] = c * h + r;
        }
    }
}

// All permutations of 0..w-1
int generate_perms(int w, int (*perms)[8]) {
    int count = 0;
    int p[8];
    for (int i=0; i<w; i++) p[i] = i;
    
    // Heap's algorithm or simple recursive
    // For w=6: 720
    // For w=8: 40320
    void permute(int k) {
        if (k == 1) {
            for (int i=0; i<w; i++) perms[count][i] = p[i];
            count++;
            return;
        }
        for (int i=0; i<k; i++) {
            permute(k - 1);
            int tmp;
            if (k % 2 == 1) {
                tmp = p[0]; p[0] = p[k-1]; p[k-1] = tmp;
            } else {
                tmp = p[i]; p[i] = p[k-1]; p[k-1] = tmp;
            }
        }
    }
    permute(w);
    return count;
}

// Calculate slice IoC at period 7 on atom-level undone text
float eval_ioc7(const char *txt) {
    int counts[26];
    float total_ioc = 0.0f;
    for (int rem = 0; rem < 7; rem++) {
        memset(counts, 0, sizeof(counts));
        int n = 0;
        for (int i = rem; i < N; i += 7) {
            counts[txt[i] - 'A']++;
            n++;
        }
        if (n > 1) {
            int num = 0;
            for (int k = 0; k < 26; k++) num += counts[k] * (counts[k] - 1);
            total_ioc += (float)num / (float)(n * (n - 1));
        }
    }
    return total_ioc / 7.0f;
}

int main() {
    load_quads();
    init_atoms();
    printf("Models loaded. 48 trigraph atoms initialized.\n");
    
    // Generate permutations for width 6
    int (*perms6)[8] = malloc(720 * sizeof(*perms6));
    int n_p6 = generate_perms(6, perms6);
    printf("Generated %d permutations for width 6.\n", n_p6);
    
    // Test (6, 6) double trigraph columnar
    printf("\n=== Testing all 720 x 720 = 518,400 pairs of (T1(6), T2(6)) ===\n");
    double t0 = omp_get_wtime();
    
    float best_ioc = 0.0f;
    int best_o1[6], best_o2[6];
    char best_text[N+1];
    best_text[N] = '\0';
    
    #pragma omp parallel
    {
        float local_best_ioc = 0.0f;
        int local_o1[6], local_o2[6];
        char local_text[N+1];
        int map1[N_ATOMS], map2[N_ATOMS];
        char undone[N+1];
        undone[N] = '\0';
        
        #pragma omp for schedule(dynamic)
        for (int i = 0; i < n_p6; i++) {
            get_atom_map(6, perms6[i], map1);
            for (int j = 0; j < n_p6; j++) {
                get_atom_map(6, perms6[j], map2);
                
                // Composite map on atoms: pt_atom[k] = ct_atom[map1[map2[k]]]
                for (int k = 0; k < N_ATOMS; k++) {
                    int src = map1[map2[k]];
                    memcpy(undone + k * UNIT, ct_atoms[src], UNIT);
                }
                
                float ioc = eval_ioc7(undone);
                if (ioc > 0.075f) {
                    #pragma omp critical
                    {
                        printf("High IoC Hit! IoC=%.5f | o1=[%d,%d,%d,%d,%d,%d] o2=[%d,%d,%d,%d,%d,%d]\n",
                               ioc, perms6[i][0], perms6[i][1], perms6[i][2], perms6[i][3], perms6[i][4], perms6[i][5],
                               perms6[j][0], perms6[j][1], perms6[j][2], perms6[j][3], perms6[j][4], perms6[j][5]);
                    }
                }
                if (ioc > local_best_ioc) {
                    local_best_ioc = ioc;
                    memcpy(local_o1, perms6[i], sizeof(local_o1));
                    memcpy(local_o2, perms6[j], sizeof(local_o2));
                    strcpy(local_text, undone);
                }
            }
        }
        
        #pragma omp critical
        {
            if (local_best_ioc > best_ioc) {
                best_ioc = local_best_ioc;
                memcpy(best_o1, local_o1, sizeof(best_o1));
                memcpy(best_o2, local_o2, sizeof(best_o2));
                strcpy(best_text, local_text);
            }
        }
    }
    
    double elapsed = omp_get_wtime() - t0;
    printf("Evaluated 518,400 pairs in %.2f s (%.0f pairs/sec)\n", elapsed, 518400.0 / elapsed);
    printf("Global Best Period-7 IoC: %.5f\n", best_ioc);
    printf("o1: [%d, %d, %d, %d, %d, %d]\n", best_o1[0], best_o1[1], best_o1[2], best_o1[3], best_o1[4], best_o1[5]);
    printf("o2: [%d, %d, %d, %d, %d, %d]\n", best_o2[0], best_o2[1], best_o2[2], best_o2[3], best_o2[4], best_o2[5]);
    printf("Undone Text: %s\n", best_text);
    
    free(perms6);
    return 0;
}
