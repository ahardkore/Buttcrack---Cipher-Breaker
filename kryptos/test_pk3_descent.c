#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <time.h>
#include <omp.h>

static float qgram[26][26][26][26];

void load_qgrams() {
    FILE *f = fopen("english_quadgrams.txt", "r");
    if (!f) {
        fprintf(stderr, "Cannot open english_quadgrams.txt\n");
        exit(1);
    }
    char line[128];
    double total = 0;
    static double counts[26][26][26][26];
    memset(counts, 0, sizeof(counts));
    while (fgets(line, sizeof(line), f)) {
        char gram[5];
        double count;
        if (sscanf(line, "%4s %lf", gram, &count) == 2) {
            int a = gram[0] - 'A';
            int b = gram[1] - 'A';
            int c = gram[2] - 'A';
            int d = gram[3] - 'A';
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
                    qgram[a][b][c][d] = counts[a][b][c][d] > 0 ? log10f(counts[a][b][c][d] / total) : floor_val;
}

const char *KRYPTOS = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
const char *PK3_CT = "HWZTRPPVHZLHRBQBQOMZBACNOTHLYGBATBTKHERQHRVZWWXCTZLRRVZCROHCIOTBVJKCALNKFJHEIMKUHJPFNVBCGQYNZMOHGBUTDPTJTDSUBOLYPLSKIEMANXMFNDBCTNRTLLVQOXUBPAXQUVDNXUMCIFOGETZWHJDIWDBWQFXAOMWBBCQXYZFZBTRIQMYOFFMVWSFLPTHFFQUINGLAMSQJOPUESPIQGZZCTJVRLQMIIRROOGBWNPQMXFQDVFTCVGNRIXQKUYYKBRTWPCDHLAWC";

float score_text(const int *pt, int len) {
    float sc = 0;
    for (int i = 0; i < len - 3; i++) {
        sc += qgram[pt[i]][pt[i+1]][pt[i+2]][pt[i+3]];
    }
    return sc;
}

int main() {
    load_qgrams();
    int N = strlen(PK3_CT);
    int c_idx[300];
    int k_to_std[26];
    for (int i = 0; i < 26; i++) {
        k_to_std[i] = KRYPTOS[i] - 'A';
    }
    for (int i = 0; i < N; i++) {
        c_idx[i] = strchr(KRYPTOS, PK3_CT[i]) - KRYPTOS;
    }

    int P = 40;
    printf("Starting coordinate descent on PK3 (P=%d, N=%d)...\n", P, N);

    float global_best_sc = -99999.0f;
    int global_best_shifts[40];

    #pragma omp parallel
    {
        unsigned int seed = 12345 + omp_get_thread_num() * 777;
        int shifts[40];
        int pt_std[300];
        int pt_k[300];

        #pragma omp for
        for (int restart = 0; restart < 5000; restart++) {
            for (int j = 0; j < P; j++) {
                shifts[j] = rand_r(&seed) % 26;
            }
            // initial plaintext
            for (int i = 0; i < N; i++) {
                pt_k[i] = (c_idx[i] - shifts[i % P] + 26) % 26;
                pt_std[i] = k_to_std[pt_k[i]];
            }
            float cur_sc = score_text(pt_std, N);

            // coordinate descent sweeps
            int improved = 1;
            int iter = 0;
            while (improved && iter < 30) {
                improved = 0;
                iter++;
                for (int j = 0; j < P; j++) {
                    int best_s = shifts[j];
                    float best_s_sc = cur_sc;
                    int old_s = shifts[j];

                    for (int cand_s = 0; cand_s < 26; cand_s++) {
                        if (cand_s == old_s) continue;
                        // update plaintext at positions i % P == j
                        for (int i = j; i < N; i += P) {
                            pt_k[i] = (c_idx[i] - cand_s + 26) % 26;
                            pt_std[i] = k_to_std[pt_k[i]];
                        }
                        float sc = score_text(pt_std, N);
                        if (sc > best_s_sc) {
                            best_s_sc = sc;
                            best_s = cand_s;
                        }
                    }
                    if (best_s != old_s) {
                        shifts[j] = best_s;
                        cur_sc = best_s_sc;
                        improved = 1;
                    }
                    // restore best
                    for (int i = j; i < N; i += P) {
                        pt_k[i] = (c_idx[i] - shifts[j] + 26) % 26;
                        pt_std[i] = k_to_std[pt_k[i]];
                    }
                }
            }

            #pragma omp critical
            {
                if (cur_sc > global_best_sc) {
                    global_best_sc = cur_sc;
                    memcpy(global_best_shifts, shifts, sizeof(shifts));
                    printf("Restart %5d: Score = %8.2f (avg %6.4f) | ", restart, cur_sc, cur_sc / (N - 3));
                    for (int i = 0; i < 40; i++) printf("%c", 'A' + pt_std[i]);
                    printf("\n");
                    fflush(stdout);
                }
            }
        }
    }

    printf("\nFinished! Global best score: %.2f\n", global_best_sc);
    return 0;
}
