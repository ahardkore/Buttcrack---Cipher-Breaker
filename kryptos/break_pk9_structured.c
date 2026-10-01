/*
 * Answer-free structure-aware attack on Paradigm Kryptos PK9.
 *
 * The public but unverified Q5/Q6/Q7/T8 lead is tested more broadly than a
 * single pipeline: any subset of the three additive KRYPTOS clocks may occur on
 * either side of T8. Canonical, inverse, and uniformly row-reversed rectangular
 * layouts are covered.
 *
 * Motivated by PK8's recovered insertion relation, this program tests whether
 * Q5 -> Q6 -> Q7 is a one-character insertion ladder. It enumerates every such
 * chain in the repository's broad dictionaries. For each chain it solves the
 * unknown 8-column assignment with a position-aware Held-Karp dynamic program.
 * It can also sweep every clock phase/sign for PK8's literal Q5/Q6/Q7 keys and
 * every phase for the motivated Q5+Q6 -> T8 -> Q7 split. No PK9 answer material
 * is present in this source.
 *
 * Build/run from repository root:
 *   cc -std=c11 -O3 -march=native -fopenmp -Wall -Wextra -Werror \
 *      kryptos/break_pk9_structured.c -o /tmp/break_pk9_structured -lm
 *   /tmp/break_pk9_structured --self-test
 *   OMP_NUM_THREADS=32 /tmp/break_pk9_structured
 *   OMP_NUM_THREADS=32 /tmp/break_pk9_structured --phased-split
 *   /tmp/break_pk9_structured --fixed-pk8
 */

#define _POSIX_C_SOURCE 200809L

#include <math.h>
#include <omp.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define A 26
#define N 144
#define WIDTH 8
#define HEIGHT 18
#define TOP 30
#define QSIZE (A*A*A*A)
#define BSIZE (A*A)
#define MAX_WORDS 100000

static const char *KALPH = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
static const char *PK9 =
    "KSYAWFEYYOISZGEUFBLYATAIBYFAQBQYYVDWJKLJXMYIEPIFVHPQNHZGSUHUUDXL"
    "EHRHUMALHEGLHXSJMUXGNUIVBXGUJHZRZGUSVHMLSCTSUQXHSUMQQIFUQGKHJGUQ"
    "GLHDKEWSKAMHIJXD";
static const char *CONTROL_PLAIN =
    "THEWHITESMITHSWORKSHOPISFILLEDWITHTHEOLDTOOLSOFHISTRADEMYEYESAREDRAWN"
    "TOTHEGUTTERALONGTHEWALLWHICHISSTREWNWITHEXQUISITENEEDLESTHEWHITESMITHSAYSHE";

static int kindex[256], to_std[A], target_ct[N];
static float *quad, *bigram;

typedef struct {
    char text[9];
} Word;

typedef struct {
    float quad_score;
    float bigram_score;
    char q5[6], q6[7], q7[8];
    unsigned char offset5,offset6,offset7;
    unsigned char block_at_col[WIDTH];
    char plain[N + 1];
} Hit;

static Word *words5, *words6, *words7, *words8;
static int n5, n6, n7, n8;

static inline int qidx(int a, int b, int c, int d) {
    return ((a * A + b) * A + c) * A + d;
}

static float *load_ngram(const char *path, int order, int size) {
    float *table = calloc((size_t)size, sizeof(*table));
    if (!table) exit(2);
    char command[512];
    snprintf(command, sizeof(command), "gzip -cd -- '%s'", path);
    FILE *f = popen(command, "r");
    if (!f) { fprintf(stderr, "cannot load %s\n", path); exit(2); }
    char line[128], gram[8];
    long long count, total = 0;
    while (fgets(line, sizeof(line), f)) {
        if (sscanf(line, "%7s %lld", gram, &count) != 2 ||
            (int)strlen(gram) != order) continue;
        int at;
        if (order == 4) {
            int a=gram[0]-'A', b=gram[1]-'A', c=gram[2]-'A', d=gram[3]-'A';
            if (a<0||a>=A||b<0||b>=A||c<0||c>=A||d<0||d>=A) continue;
            at = qidx(a,b,c,d);
        } else {
            int a=gram[0]-'A', b=gram[1]-'A';
            if (a<0||a>=A||b<0||b>=A) continue;
            at = a*A+b;
        }
        table[at] = (float)count;
        total += count;
    }
    if (pclose(f) != 0 || total == 0) {
        fprintf(stderr, "bad ngram model %s\n", path);
        exit(2);
    }
    float log_total = (float)log10((double)total);
    float floor_score = (float)log10(0.1 / (double)total);
    for (int i=0; i<size; i++)
        table[i] = table[i] > 0 ? log10f(table[i])-log_total : floor_score;
    return table;
}

static int compare_words(const void *a, const void *b) {
    return strcmp(((const Word *)a)->text, ((const Word *)b)->text);
}

static void add_words_from(const char *path, int length, Word *out, int *count) {
    FILE *f = fopen(path, "r");
    if (!f) { perror(path); exit(2); }
    char line[256];
    while (fgets(line, sizeof(line), f)) {
        char clean[9];
        int n=0, letters=0;
        for (int i=0; line[i]; i++) if (line[i]>='A' && line[i]<='Z') {
            letters++;
            if (n < 8) clean[n++] = line[i];
        }
        if (letters != length) continue;
        clean[n] = 0;
        if (*count >= MAX_WORDS) { fprintf(stderr, "too many words\n"); exit(2); }
        strcpy(out[(*count)++].text, clean);
    }
    fclose(f);
}

static int deduplicate(Word *words, int count) {
    qsort(words, (size_t)count, sizeof(*words), compare_words);
    int out=0;
    for (int i=0; i<count; i++) {
        if (out && !strcmp(words[i].text, words[out-1].text)) continue;
        words[out++] = words[i];
    }
    return out;
}

static void load_words(void) {
    words5=malloc(MAX_WORDS*sizeof(*words5)); words6=malloc(MAX_WORDS*sizeof(*words6));
    words7=malloc(MAX_WORDS*sizeof(*words7)); words8=malloc(MAX_WORDS*sizeof(*words8));
    if (!words5||!words6||!words7||!words8) exit(2);
    Word *sets[4]={words5,words6,words7,words8};
    int *counts[4]={&n5,&n6,&n7,&n8};
    for (int j=0; j<4; j++) {
        int length=j+5;
        char path[64];
        add_words_from("kryptos/all_words.txt",length,sets[j],counts[j]);
        snprintf(path,sizeof(path),"kryptos/words_%d.txt",length);
        add_words_from(path,length,sets[j],counts[j]);
        *counts[j]=deduplicate(sets[j],*counts[j]);
    }
    printf("dictionary words: len5=%d len6=%d len7=%d len8=%d\n",n5,n6,n7,n8);
}

static const Word *find_word(const Word *words, int count, const char *text) {
    Word probe={{0}};
    strcpy(probe.text,text);
    return bsearch(&probe,words,(size_t)count,sizeof(*words),compare_words);
}

static void remove_at(const char *source, int length, int at, char *dest) {
    int out=0;
    for (int i=0; i<length; i++) if (i!=at) dest[out++]=source[i];
    dest[out]=0;
}

static void word_values(const char *word, int length, int *values) {
    for (int i=0; i<length; i++) values[i]=kindex[(unsigned char)word[i]];
}

/* Solve the complete-columnar assignment exactly for the chosen likelihood.
 * Forward layouts use every plaintext bigram, including row boundaries.
 * Inverse layouts consist of contiguous blocks, so all quadgrams decompose into
 * internal-block and adjacent-block terms and can be optimized exactly. */
static Hit solve_chain(const int ct[N], const char *w5, const char *w6, const char *w7,
                       unsigned inner_mask, int inverse_layout, int reverse_rows,
                       int offset5, int offset6, int offset7,
                       int sign5, int sign6, int sign7) {
    int q5[5],q6[6],q7[7];
    word_values(w5,5,q5); word_values(w6,6,q6); word_values(w7,7,q7);

    unsigned char dec[WIDTH][WIDTH][HEIGHT]; /* destination col/block, CT block/col, row */
    for (int c=0; c<WIDTH; c++) for (int b=0; b<WIDTH; b++) for (int r=0; r<HEIGHT; r++) {
        int source=inverse_layout ? r*WIDTH+b : b*HEIGHT+(reverse_rows?HEIGHT-1-r:r);
        int destination=inverse_layout ? c*HEIGHT+r : r*WIDTH+c;
        int value=ct[source];
        value-=sign5*q5[(((inner_mask&1u)?destination:source)+offset5)%5];
        value-=sign6*q6[(((inner_mask&2u)?destination:source)+offset6)%6];
        value-=sign7*q7[(((inner_mask&4u)?destination:source)+offset7)%7];
        value%=A;
        if (value<0) value+=A;
        dec[c][b][r]=(unsigned char)to_std[value];
    }

    float edge[WIDTH][WIDTH][WIDTH]={{{0}}};
    float unary[WIDTH][WIDTH]={{0}};
    float boundary[WIDTH][WIDTH]={{0}};
    if (!inverse_layout) {
        for (int c=1; c<WIDTH; c++) for (int a=0; a<WIDTH; a++) for (int b=0; b<WIDTH; b++) {
            if (a==b) continue;
            for (int r=0; r<HEIGHT; r++) edge[c][a][b]+=bigram[dec[c-1][a][r]*A+dec[c][b][r]];
        }
        for (int last=0; last<WIDTH; last++) for (int first=0; first<WIDTH; first++) {
            if (last==first) continue;
            for (int r=0; r<HEIGHT-1; r++) boundary[last][first]+=bigram[dec[7][last][r]*A+dec[0][first][r+1]];
        }
    } else {
        /* In this orientation each candidate is one contiguous 18-letter
         * plaintext block.  The complete quadgram score decomposes into an
         * internal unary term and three crossing quadgrams for each adjacent
         * pair, so the same Hamilton-path DP can optimize quadgrams exactly.
         * Bigram ordering is too weak here: only seven bigrams depend on the
         * block permutation and can rank a wrong planted order first. */
        for (int c=0; c<WIDTH; c++) for (int b=0; b<WIDTH; b++)
            for (int r=0; r<=HEIGHT-4; r++)
                unary[c][b]+=quad[qidx(dec[c][b][r],dec[c][b][r+1],
                                      dec[c][b][r+2],dec[c][b][r+3])];
        for (int c=1; c<WIDTH; c++) for (int a=0; a<WIDTH; a++) for (int b=0; b<WIDTH; b++) {
            if (a==b) continue;
            edge[c][a][b]=
                quad[qidx(dec[c-1][a][HEIGHT-3],dec[c-1][a][HEIGHT-2],
                          dec[c-1][a][HEIGHT-1],dec[c][b][0])]+
                quad[qidx(dec[c-1][a][HEIGHT-2],dec[c-1][a][HEIGHT-1],
                          dec[c][b][0],dec[c][b][1])]+
                quad[qidx(dec[c-1][a][HEIGHT-1],dec[c][b][0],
                          dec[c][b][1],dec[c][b][2])];
        }
    }

    float best=-1e30f;
    unsigned char best_order[WIDTH]={0};
    int first_begin=inverse_layout?0:0, first_end=inverse_layout?1:WIDTH;
    for (int first=first_begin; first<first_end; first++) {
        float dp[1<<WIDTH][WIDTH];
        signed char parent[1<<WIDTH][WIDTH];
        for (int m=0; m<(1<<WIDTH); m++) for (int b=0; b<WIDTH; b++) {
            dp[m][b]=-1e30f; parent[m][b]=-1;
        }
        if (inverse_layout) {
            for (int b=0; b<WIDTH; b++) dp[1<<b][b]=unary[0][b];
        } else {
            dp[1<<first][first]=0;
        }
        for (int mask=1; mask<(1<<WIDTH); mask++) {
            if (!inverse_layout && !(mask&(1<<first))) continue;
            int used=__builtin_popcount((unsigned)mask);
            if (used>=WIDTH) continue;
            int c=used;
            for (int last=0; last<WIDTH; last++) {
                float base=dp[mask][last];
                if (base < -1e20f) continue;
                for (int b=0; b<WIDTH; b++) if (!(mask&(1<<b))) {
                    int nm=mask|(1<<b);
                    float value=base+edge[c][last][b]+unary[c][b];
                    if (value>dp[nm][b]) { dp[nm][b]=value; parent[nm][b]=(signed char)last; }
                }
            }
        }
        int full=(1<<WIDTH)-1;
        for (int last=0; last<WIDTH; last++) {
            float value=dp[full][last]+(inverse_layout?0:boundary[last][first]);
            if (value<=best) continue;
            best=value;
            int mask=full, at=last;
            for (int c=WIDTH-1; c>=0; c--) {
                best_order[c]=(unsigned char)at;
                int previous=parent[mask][at];
                mask^=1<<at;
                at=previous;
            }
        }
    }

    Hit hit;
    strcpy(hit.q5,w5); strcpy(hit.q6,w6); strcpy(hit.q7,w7);
    hit.offset5=(unsigned char)offset5; hit.offset6=(unsigned char)offset6;
    hit.offset7=(unsigned char)offset7;
    memcpy(hit.block_at_col,best_order,WIDTH);
    int p[N];
    for (int r=0; r<HEIGHT; r++) for (int c=0; c<WIDTH; c++) {
        int i=inverse_layout?c*HEIGHT+r:r*WIDTH+c;
        p[i]=dec[c][best_order[c]][r];
        hit.plain[i]=(char)('A'+p[i]);
    }
    hit.plain[N]=0;
    float score=0;
    for (int i=0; i<N-1; i++) score+=bigram[p[i]*A+p[i+1]];
    hit.bigram_score=score/(N-1);
    score=0;
    for (int i=0; i<=N-4; i++) score+=quad[qidx(p[i],p[i+1],p[i+2],p[i+3])];
    hit.quad_score=score/(N-3);
    return hit;
}

static void insert_hit(Hit top[TOP], const Hit *hit, int by_quad) {
    float value=by_quad?hit->quad_score:hit->bigram_score;
    float tail=by_quad?top[TOP-1].quad_score:top[TOP-1].bigram_score;
    if (value<=tail) return;
    int at=TOP-1;
    while (at>0) {
        float prev=by_quad?top[at-1].quad_score:top[at-1].bigram_score;
        if (value<=prev) break;
        top[at]=top[at-1]; at--;
    }
    top[at]=*hit;
}

static int rank_char(unsigned char block, const unsigned char order[WIDTH]) {
    for (int c=0; c<WIDTH; c++) if (order[c]==block) return c;
    return -1;
}

static int keyword_matches_order(const char *word, const unsigned char block_at_col[WIDTH]) {
    int read_order[WIDTH];
    for (int i=0; i<WIDTH; i++) read_order[i]=i;
    for (int i=1; i<WIDTH; i++) {
        int value=read_order[i],j=i-1;
        while (j>=0 && word[read_order[j]]>word[value]) {
            read_order[j+1]=read_order[j]; j--;
        }
        read_order[j+1]=value; /* stable for repeated letters */
    }
    for (int block=0; block<WIDTH; block++) {
        int col=read_order[block];
        if (block_at_col[col]!=block) return 0;
    }
    return 1;
}

static void print_hit(const Hit *h, int rank, const char *kind) {
    printf("\n%s #%d quad=%.6f bigram=%.6f keys=%s/%s/%s offsets=%u,%u,%u\n",
           kind,rank,h->quad_score,h->bigram_score,h->q5,h->q6,h->q7,
           h->offset5,h->offset6,h->offset7);
    printf("block_at_col=");
    for (int c=0; c<WIDTH; c++) printf("%d%s",h->block_at_col[c],c==WIDTH-1?"\n":",");
    printf("column_ranks=");
    for (int b=0; b<WIDTH; b++) printf("%d%s",rank_char((unsigned char)b,h->block_at_col),b==WIDTH-1?"\n":",");
    printf("t8_words=");
    int found=0;
    for (int i=0; i<n8 && found<12; i++) if (keyword_matches_order(words8[i].text,h->block_at_col)) {
        printf("%s%s",found?",":"",words8[i].text); found++;
    }
    if (!found) printf("(none)");
    printf("\nplaintext=%s\n",h->plain);
}

static int same_block_multiset(const char *a, const char *b) {
    int used[WIDTH]={0};
    for (int i=0; i<WIDTH; i++) {
        int found=0;
        for (int j=0; j<WIDTH; j++) if (!used[j] &&
            !memcmp(a+i*HEIGHT,b+j*HEIGHT,HEIGHT)) {
            used[j]=1; found=1; break;
        }
        if (!found) return 0;
    }
    return 1;
}

static void encrypt_control(int ct[N], unsigned inner_mask, int inverse_layout,
                            int reverse_rows, int offset5, int offset6, int offset7) {
    const char *w5="IRATE",*w6="PIRATE",*w7="PIRATES",*w8="LANGUAGE";
    int q5[5],q6[6],q7[7],read_order[WIDTH];
    word_values(w5,5,q5); word_values(w6,6,q6); word_values(w7,7,q7);
    for (int i=0; i<WIDTH; i++) read_order[i]=i;
    for (int i=1; i<WIDTH; i++) {
        int value=read_order[i],j=i-1;
        while (j>=0 && w8[read_order[j]]>w8[value]) { read_order[j+1]=read_order[j]; j--; }
        read_order[j+1]=value;
    }

    int stage[N],transposed[N];
    for (int i=0; i<N; i++) {
        int p=kindex[(unsigned char)CONTROL_PLAIN[i]];
        if (inner_mask&1u) p+=q5[(i+offset5)%5];
        if (inner_mask&2u) p+=q6[(i+offset6)%6];
        if (inner_mask&4u) p+=q7[(i+offset7)%7];
        stage[i]=p%A;
    }
    for (int b=0; b<WIDTH; b++) for (int r=0; r<HEIGHT; r++) {
        int source=inverse_layout?r*WIDTH+b:b*HEIGHT+(reverse_rows?HEIGHT-1-r:r);
        int plain_index=inverse_layout?read_order[b]*HEIGHT+r:r*WIDTH+read_order[b];
        transposed[source]=stage[plain_index];
    }
    for (int i=0; i<N; i++) {
        int value=transposed[i];
        if (!(inner_mask&1u)) value+=q5[(i+offset5)%5];
        if (!(inner_mask&2u)) value+=q6[(i+offset6)%6];
        if (!(inner_mask&4u)) value+=q7[(i+offset7)%7];
        ct[i]=value%A;
    }
}

static void format_layers(unsigned mask, char out[32]) {
    int at=0;
    const char *names[3]={"Q5","Q6","Q7"};
    for (int bit=0; bit<3; bit++) if (mask&(1u<<bit)) {
        if (at) out[at++]='+';
        size_t n=strlen(names[bit]); memcpy(out+at,names[bit],n); at+=(int)n;
    }
    if (!at) { memcpy(out,"NONE",4); at=4; }
    out[at]=0;
}

int main(int argc, char **argv) {
    int self=argc==2&&!strcmp(argv[1],"--self-test");
    int fixed_pk8=argc==2&&!strcmp(argv[1],"--fixed-pk8");
    int phased_split=argc==2&&!strcmp(argv[1],"--phased-split");
    if (argc!=1&&!self&&!fixed_pk8&&!phased_split) {
        fprintf(stderr,"usage: %s [--self-test|--fixed-pk8|--phased-split]\n",argv[0]); return 2;
    }
    if (strlen(PK9)!=N||strlen(CONTROL_PLAIN)!=N) { fprintf(stderr,"internal length error\n"); return 2; }
    memset(kindex,-1,sizeof(kindex));
    for (int i=0; i<A; i++) { kindex[(unsigned char)KALPH[i]]=i; to_std[i]=KALPH[i]-'A'; }
    quad=load_ngram("buttcrack/data/english_quadgrams.txt.gz",4,QSIZE);
    bigram=load_ngram("buttcrack/data/english_bigrams.txt.gz",2,BSIZE);
    load_words();
    for (int i=0; i<N; i++) target_ct[i]=kindex[(unsigned char)PK9[i]];
    if (self) {
        int all_ok=1;
        for (int route=0; route<3; route++) for (unsigned inner_mask=0; inner_mask<8; inner_mask++) {
            int inverse_layout=route==1,reverse_rows=route==2;
            int ct[N];
            encrypt_control(ct,inner_mask,inverse_layout,reverse_rows,0,0,0);
            Hit hit=solve_chain(ct,"IRATE","PIRATE","PIRATES",inner_mask,
                                inverse_layout,reverse_rows,0,0,0,1,1,1);
            int exact=!strcmp(hit.plain,CONTROL_PLAIN)&&
                      keyword_matches_order("LANGUAGE",hit.block_at_col);
            /* In an inverse layout, advancing one plaintext block changes the
             * position by 18. Q6 therefore has the same phase in every block;
             * with no inner Q5/Q7, the score can identify only the unordered
             * set of perfect 18-letter blocks. */
            int block_permutation=inverse_layout&&(inner_mask&5u)==0&&
                                  same_block_multiset(hit.plain,CONTROL_PLAIN);
            int ok=exact||block_permutation;
            const char *route_name=inverse_layout?"inverse":(reverse_rows?"reversed_rows":"forward");
            printf("self_test_inner_mask_%u_%s=%s exact=%s keys=%s/%s/%s/LANGUAGE quad=%.6f\n",
                   inner_mask,route_name,
                   ok?(exact?"PASS":"PASS_BLOCK_PERMUTATION"):"FAIL",
                   exact?"YES":"NO",hit.q5,hit.q6,hit.q7,hit.quad_score);
            if (!ok) all_ok=0;
        }
        {
            int ct[N];
            encrypt_control(ct,3u,0,0,2,3,4);
            Hit hit=solve_chain(ct,"IRATE","PIRATE","PIRATES",3u,0,0,
                                2,3,4,1,1,1);
            int ok=!strcmp(hit.plain,CONTROL_PLAIN)&&
                   keyword_matches_order("LANGUAGE",hit.block_at_col);
            printf("self_test_nonzero_phases=%s offsets=2,3,4 quad=%.6f\n",
                   ok?"PASS":"FAIL",hit.quad_score);
            if (!ok) all_ok=0;
        }
        return all_ok?0:1;
    }
    if (phased_split) {
        const unsigned inner_mask=3u; /* Q5+Q6 -> T8 -> Q7 */
        Hit global[TOP];
        for (int i=0; i<TOP; i++) global[i].quad_score=-1e30f;
        long long candidates=0;
        double started=omp_get_wtime();
        #pragma omp parallel
        {
            Hit local[TOP];
            for (int i=0; i<TOP; i++) local[i].quad_score=-1e30f;
            long long local_candidates=0;
            #pragma omp for schedule(dynamic,1)
            for (int i7=0; i7<n7; i7++) {
                char seen6[7][7]; int nseen6=0;
                for (int cut7=0; cut7<7; cut7++) {
                    char w6[7]; remove_at(words7[i7].text,7,cut7,w6);
                    int duplicate6=0;
                    for (int j=0; j<nseen6; j++) if (!strcmp(w6,seen6[j])) duplicate6=1;
                    if (duplicate6||!find_word(words6,n6,w6)) continue;
                    strcpy(seen6[nseen6++],w6);
                    char seen5[6][6]; int nseen5=0;
                    for (int cut6=0; cut6<6; cut6++) {
                        char w5[6]; remove_at(w6,6,cut6,w5);
                        int duplicate5=0;
                        for (int j=0; j<nseen5; j++) if (!strcmp(w5,seen5[j])) duplicate5=1;
                        if (duplicate5||!find_word(words5,n5,w5)) continue;
                        strcpy(seen5[nseen5++],w5);
                        for (int o5=0; o5<5; o5++) for (int o6=0; o6<6; o6++)
                            for (int o7=0; o7<7; o7++) {
                                Hit hit=solve_chain(target_ct,w5,w6,words7[i7].text,
                                                    inner_mask,0,0,o5,o6,o7,1,1,1);
                                insert_hit(local,&hit,1); local_candidates++;
                            }
                    }
                }
            }
            #pragma omp atomic
            candidates+=local_candidates;
            #pragma omp critical
            {
                for (int i=0; i<TOP; i++) insert_hit(global,&local[i],1);
            }
        }
        double elapsed=omp_get_wtime()-started;
        printf("\n=== PHASED Q5+Q6 -> T8 -> Q7 (FORWARD LAYOUT) ===\n");
        printf("candidates=%lld elapsed=%.3fs rate=%.3f candidates/s\n",
               candidates,elapsed,candidates/elapsed);
        for (int i=0; i<20; i++) print_hit(&global[i],i+1,"PHASED");
        free(words5);free(words6);free(words7);free(words8);free(quad);free(bigram);
        return 0;
    }
    if (fixed_pk8) {
        for (int model=0; model<24; model++) {
            unsigned inner_mask=(unsigned)model&7u;
            int route=model/8,inverse_layout=route==1,reverse_rows=route==2;
            Hit best={.quad_score=-1e30f};
            int best5=0,best6=0,best7=0,best_signs=0;
            for (int signs=0; signs<8; signs++) {
                int s5=(signs&1)?-1:1,s6=(signs&2)?-1:1,s7=(signs&4)?-1:1;
                for (int o5=0; o5<5; o5++) for (int o6=0; o6<6; o6++)
                    for (int o7=0; o7<7; o7++) {
                        Hit hit=solve_chain(target_ct,"METER","METIER","MASTERY",
                                            inner_mask,inverse_layout,reverse_rows,
                                            o5,o6,o7,s5,s6,s7);
                        if (hit.quad_score>best.quad_score) {
                            best=hit; best5=o5; best6=o6; best7=o7; best_signs=signs;
                        }
                    }
            }
            char inner[32],outer[32];
            format_layers(inner_mask,inner); format_layers((~inner_mask)&7u,outer);
            const char *route_name=inverse_layout?"INVERSE":(reverse_rows?"REVERSED-ROWS":"FORWARD");
            printf("\n=== INNER %s -> T8 -> OUTER %s (%s LAYOUT) ===\n",
                   inner,outer,route_name);
            printf("best_offsets=%d,%d,%d best_signs=%c,%c,%c searched=1680\n",
                   best5,best6,best7,(best_signs&1)?'-':'+',
                   (best_signs&2)?'-':'+',(best_signs&4)?'-':'+');
            print_hit(&best,1,"FIXED_PK8_PHASED_SIGNED");
        }
        free(words5);free(words6);free(words7);free(words8);free(quad);free(bigram);
        return 0;
    }

    for (int model=0; model<24; model++) {
        unsigned inner_mask=(unsigned)model&7u;
        int route=model/8,inverse_layout=route==1,reverse_rows=route==2;
        Hit global_quad[TOP],global_bigram[TOP];
        for (int i=0; i<TOP; i++) {
            global_quad[i].quad_score=-1e30f; global_quad[i].bigram_score=-1e30f;
            global_bigram[i].quad_score=-1e30f; global_bigram[i].bigram_score=-1e30f;
        }
        long long chains=0;
        double started=omp_get_wtime();
        #pragma omp parallel
        {
            Hit local_quad[TOP],local_bigram[TOP];
            for (int i=0; i<TOP; i++) {
                local_quad[i].quad_score=-1e30f; local_quad[i].bigram_score=-1e30f;
                local_bigram[i].quad_score=-1e30f; local_bigram[i].bigram_score=-1e30f;
            }
            long long local_chains=0;
            #pragma omp for schedule(dynamic,32)
            for (int i7=0; i7<n7; i7++) {
                char seen6[7][7]; int nseen6=0;
                for (int cut7=0; cut7<7; cut7++) {
                    char w6[7]; remove_at(words7[i7].text,7,cut7,w6);
                    int duplicate6=0;
                    for (int j=0; j<nseen6; j++) if (!strcmp(w6,seen6[j])) duplicate6=1;
                    if (duplicate6||!find_word(words6,n6,w6)) continue;
                    strcpy(seen6[nseen6++],w6);
                    char seen5[6][6]; int nseen5=0;
                    for (int cut6=0; cut6<6; cut6++) {
                        char w5[6]; remove_at(w6,6,cut6,w5);
                        int duplicate5=0;
                        for (int j=0; j<nseen5; j++) if (!strcmp(w5,seen5[j])) duplicate5=1;
                        if (duplicate5||!find_word(words5,n5,w5)) continue;
                        strcpy(seen5[nseen5++],w5);
                        local_chains++;
                        Hit hit=solve_chain(target_ct,w5,w6,words7[i7].text,
                                            inner_mask,inverse_layout,reverse_rows,
                                            0,0,0,1,1,1);
                        insert_hit(local_quad,&hit,1); insert_hit(local_bigram,&hit,0);
                    }
                }
            }
            #pragma omp atomic
            chains+=local_chains;
            #pragma omp critical
            {
                for (int i=0; i<TOP; i++) {
                    insert_hit(global_quad,&local_quad[i],1);
                    insert_hit(global_bigram,&local_bigram[i],0);
                }
            }
        }
        double elapsed=omp_get_wtime()-started;
        char inner[32],outer[32];
        format_layers(inner_mask,inner); format_layers((~inner_mask)&7u,outer);
        const char *route_name=inverse_layout?"INVERSE":(reverse_rows?"REVERSED-ROWS":"FORWARD");
        printf("\n=== INNER %s -> T8 -> OUTER %s (%s LAYOUT) ===\n",
               inner,outer,route_name);
        printf("insertion_chains=%lld elapsed=%.3fs rate=%.3f chains/s\n",chains,elapsed,chains/elapsed);
        for (int i=0; i<10; i++) print_hit(&global_quad[i],i+1,"QUAD");
        printf("\n--- highest exact-bigram candidates ---\n");
        for (int i=0; i<5; i++) print_hit(&global_bigram[i],i+1,"BIGRAM");
    }

    free(words5);free(words6);free(words7);free(words8);free(quad);free(bigram);
    return 0;
}
