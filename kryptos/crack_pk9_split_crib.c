/*
 * Exact prefix-crib attack for split-layer PK9 hypothesis Q5+Q6 -> T8 -> Q7
 *
 *     P -> Q(5)+Q(6) -> complete columnar T(8) -> Q(7) -> C.
 *
 * Thirty consecutive plaintext letters overdetermine the 16 gauge-independent
 * wheel coordinates. For every candidate crib and 8! column assignment, this
 * solves the system independently over GF(2) and GF(13), combines the result
 * modulo 26, verifies all supplied crib letters, and decrypts the complete
 * message. Rank-15 assignments are handled by enumerating their 26 affine
 * solutions. --all-offsets tests every valid placement rather than position 0.
 *
 * The --word-filter modes first require that some gauge-equivalent Q5, Q6, and
 * Q7 are literal dictionary words.  Dense normalized-pattern tables handle Q5
 * and Q6; an open-addressed table handles Q7.  This rejects almost all keys
 * before full decryption.  Optional T8-word modes enumerate only permutations
 * induced by stable alphabetical ranking of supplied 8-letter words.
 * --all-keys modes remove the Q-word filter and score every full-crib survivor;
 * they can be combined with an arbitrary or supplied-word T8 set.  The
 * synthetic tests verify both arbitrary wheels and the planted
 * STEEL/SILVER/DRAWING word-wheel path.
 *
 * This is a bounded hypothesis test, not a claim that the architecture, crib,
 * or dictionary-wheel assumption is correct.
 *
 * Build/run from repository root:
 *   cc -O3 -march=native -fopenmp kryptos/crack_pk9_split_crib.c \
 *      -o /tmp/crack_pk9_split_crib -lm
 *   /tmp/crack_pk9_split_crib --word-filter CRIB_FILE
 *   /tmp/crack_pk9_split_crib --word-filter-all-offsets CRIB_FILE
 */

#include <math.h>
#include <omp.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define N 144
#define N8 153
#define W 8
#define H 18
#define NV 16
#define CRIB_ROWS 30
#define NPERM 40320
#define TOP 20
#define A 26
#define QSIZE (A*A*A*A)
#define SPACE5 (A*A*A*A)
#define SPACE6 (A*A*A*A*A)
#define H7SIZE 131072

static const char *KALPH = "KRYPTOSABCDEFGHIJLMNQUVWXZ";
static const char *PK9 =
    "KSYAWFEYYOISZGEUFBLYATAIBYFAQBQYYVDWJKLJXMYIEPIFVHPQNHZGSUHUUDXL"
    "EHRHUMALHEGLHXSJMUXGNUIVBXGUJHZRZGUSVHMLSCTSUQXHSUMQQIFUQGKHJGUQ"
    "GLHDKEWSKAMHIJXD";
static const char *PK8 =
    "COPVEJJVSVURTVIPYOTPLHGBTMAUCCPESIWIGZBWSJPKTRPUEKQFIFCLHMXTHIMHWO"
    "YIGURBOMPARCVXVKBDDVBVHDRHGCVNWWVLBMYWMWHICFIXZWBVZYCQGNOGJGUMLNPUT"
    "HQCXNWPQZOIRJZGSWVPY";
static const char *CONTROL_PLAIN =
    "THEWHITESMITHSWORKSHOPISFILLEDWITHTHEOLDTOOLSOFHISTRADEMYEYESAREDRAWN"
    "TOTHEGUTTERALONGTHEWALLWHICHISSTREWNWITHEXQUISITENEEDLESTHEWHITESMITHSAYSHE";

static int kindex[256], to_std[A];
static float *quad;
static unsigned char perms[NPERM][W];       /* block_at_col */
static unsigned char base_key[NPERM][NV];  /* A^-1 * Ccrib(order) */
static unsigned char inv26[NPERM][NV][CRIB_ROWS];
static unsigned char perm_valid[NPERM];
typedef struct {
    int pi,rank[2],free_col[2];
    unsigned char coeff[2][CRIB_ROWS][NV];
    unsigned char left[2][CRIB_ROWS][CRIB_ROWS];
    signed char pivot_col[2][NV];
} SingularSystem;
static SingularSystem singulars[32];
static int nsingular;
static int nperm;
static uint32_t *wordmask5, *wordmask6;
static uint32_t h7code[H7SIZE], h7mask[H7SIZE];
static unsigned char h7used[H7SIZE];
static int active_perms[NPERM], nactive;
static char t8_word_by_perm[NPERM][9];
#define MAX_W4 20000
static char bridge_w4[MAX_W4][5];
static unsigned char bridge_q4[MAX_W4][4];
static int nbridge_w4,bridge_ct8[N8];

typedef struct {
    float score;
    int offset;
    char crib[65];
    unsigned char key[NV];
    unsigned char perm[W];
    char word_keys[32];
    char t8_key[9];
    char plain[N+1];
} Hit;

typedef struct {
    float combined,pk8_score,pk9_score;
    int offset;
    char crib[65],word_keys[32],q4[5],pk8_plain[N8+1],pk9_plain[N+1];
    unsigned char key[NV],perm[W];
} BridgeHit;

static inline int qidx(int a,int b,int c,int d) {
    return ((a*A+b)*A+c)*A+d;
}

static float *load_quads(void) {
    float *t = calloc(QSIZE, sizeof(*t));
    if (!t) exit(2);
    FILE *f = popen("gzip -cd -- 'buttcrack/data/english_quadgrams.txt.gz'", "r");
    if (!f) { fprintf(stderr,"cannot load quadgrams\n"); exit(2); }
    char line[128], g[8]; long long count, total=0;
    while (fgets(line,sizeof(line),f)) {
        if (sscanf(line,"%7s %lld",g,&count)!=2 || strlen(g)!=4) continue;
        int a=g[0]-'A',b=g[1]-'A',c=g[2]-'A',d=g[3]-'A';
        if (a<0||a>=A||b<0||b>=A||c<0||c>=A||d<0||d>=A) continue;
        t[qidx(a,b,c,d)]=(float)count; total+=count;
    }
    if (pclose(f)!=0 || !total) { fprintf(stderr,"bad quadgram model\n"); exit(2); }
    float lt=(float)log10((double)total), floor=(float)log10(0.1/(double)total);
    for(int i=0;i<QSIZE;i++) t[i]=t[i]>0?log10f(t[i])-lt:floor;
    return t;
}

static int inv_prime(int x,int prime){x%=prime;if(x<0)x+=prime;for(int y=1;y<prime;y++)if((x*y)%prime==1)return y;return -1;}

static void prepare_singular(SingularSystem *ss,int pno,int offset){
    ss->pi=pno;
    const int primes[2]={2,13};
    for(int pass=0;pass<2;pass++){
        int prime=primes[pass],m[CRIB_ROWS][NV+CRIB_ROWS];memset(m,0,sizeof(m));
        for(int row=0;row<CRIB_ROWS;row++){
            int i=offset+row,c=i%W,r=i/W,source=perms[pno][c]*H+r;
            if(i%5)m[row][i%5-1]=1;
            if(i%6)m[row][4+i%6-1]=1;
            m[row][9+source%7]=1;m[row][NV+row]=1;
        }
        for(int i=0;i<NV;i++)ss->pivot_col[pass][i]=-1;
        int rank=0;
        for(int col=0;col<NV;col++){
            int pivot=-1;for(int row=rank;row<CRIB_ROWS;row++)if(m[row][col]%prime){pivot=row;break;}
            if(pivot<0)continue;
            if(pivot!=rank)for(int j=0;j<NV+CRIB_ROWS;j++){int z=m[rank][j];m[rank][j]=m[pivot][j];m[pivot][j]=z;}
            int iv=inv_prime(m[rank][col],prime);
            for(int j=0;j<NV+CRIB_ROWS;j++)m[rank][j]=(m[rank][j]*iv)%prime;
            for(int row=0;row<CRIB_ROWS;row++)if(row!=rank){int z=m[row][col];for(int j=0;j<NV+CRIB_ROWS;j++){m[row][j]=(m[row][j]-z*m[rank][j])%prime;if(m[row][j]<0)m[row][j]+=prime;}}
            ss->pivot_col[pass][rank]=(signed char)col;rank++;
        }
        ss->rank[pass]=rank;ss->free_col[pass]=-1;
        int is_pivot[NV]={0};for(int row=0;row<rank;row++)is_pivot[(int)ss->pivot_col[pass][row]]=1;
        for(int col=0;col<NV;col++)if(!is_pivot[col]){ss->free_col[pass]=col;break;}
        for(int row=0;row<CRIB_ROWS;row++){
            for(int col=0;col<NV;col++)ss->coeff[pass][row][col]=(unsigned char)m[row][col];
            for(int j=0;j<CRIB_ROWS;j++)ss->left[pass][row][j]=(unsigned char)m[row][NV+j];
        }
    }
}

static void build_inverse(int offset) {
    int valid_count=0;
    #pragma omp parallel for schedule(static) reduction(+:valid_count)
    for(int pno=0;pno<NPERM;pno++) {
        unsigned char left[2][NV][CRIB_ROWS];
        int ok=1;
        const int primes[2]={2,13};
        for(int pass=0;pass<2&&ok;pass++) {
            int prime=primes[pass];
            int m[CRIB_ROWS][NV+CRIB_ROWS];memset(m,0,sizeof(m));
            for(int row=0;row<CRIB_ROWS;row++) {
                int i=offset+row,c=i%W,r=i/W;
                int source=perms[pno][c]*H+r;
                if(i%5)m[row][i%5-1]=1;
                if(i%6)m[row][4+i%6-1]=1;
                m[row][9+source%7]=1;
                m[row][NV+row]=1;
            }
            for(int col=0;col<NV;col++) {
                int pivot=-1;
                for(int row=col;row<CRIB_ROWS;row++)if(m[row][col]%prime){pivot=row;break;}
                if(pivot<0){ok=0;break;}
                if(pivot!=col)for(int j=0;j<NV+CRIB_ROWS;j++){int z=m[col][j];m[col][j]=m[pivot][j];m[pivot][j]=z;}
                int iv=inv_prime(m[col][col],prime);
                for(int j=0;j<NV+CRIB_ROWS;j++)m[col][j]=(m[col][j]*iv)%prime;
                for(int row=0;row<CRIB_ROWS;row++)if(row!=col){int z=m[row][col];for(int j=0;j<NV+CRIB_ROWS;j++){m[row][j]=(m[row][j]-z*m[col][j])%prime;if(m[row][j]<0)m[row][j]+=prime;}}
            }
            if(ok)for(int i=0;i<NV;i++)for(int j=0;j<CRIB_ROWS;j++)left[pass][i][j]=(unsigned char)m[i][NV+j];
        }
        perm_valid[pno]=(unsigned char)ok;
        if(ok){
            valid_count++;
            for(int i=0;i<NV;i++)for(int j=0;j<CRIB_ROWS;j++){
                int x=left[1][i][j];
                if((x&1)!=left[0][i][j])x+=13;
                inv26[pno][i][j]=(unsigned char)x;
            }
        }
    }
    fprintf(stderr,"offset %d full-rank split matrices=%d/%d\n",offset,valid_count,NPERM);
    nsingular=0;
    if(NPERM-valid_count<=32)for(int pno=0;pno<NPERM;pno++)if(!perm_valid[pno])
        prepare_singular(&singulars[nsingular++],pno,offset);
}

static int singular_keys(int pi,const int ct[N],const int pv[CRIB_ROWS],int offset,
                         unsigned char out[26][NV]){
    const SingularSystem *ss=NULL;
    for(int i=0;i<nsingular;i++)if(singulars[i].pi==pi){ss=&singulars[i];break;}
    if(!ss||ss->rank[0]!=NV-1||ss->rank[1]!=NV-1)return 0;
    const int primes[2]={2,13};
    unsigned char solutions[2][13][NV];
    for(int pass=0;pass<2;pass++){
        int prime=primes[pass],b[CRIB_ROWS];
        for(int row=0;row<CRIB_ROWS;row++){
            int z=0;
            for(int j=0;j<CRIB_ROWS;j++){
                int i=offset+j,c=i%W,r=i/W,source=perms[pi][c]*H+r;
                int y=(ct[source]-pv[j])%prime;if(y<0)y+=prime;
                z+=ss->left[pass][row][j]*y;
            }
            b[row]=z%prime;
        }
        for(int row=ss->rank[pass];row<CRIB_ROWS;row++)if(b[row])return 0;
        int free_col=ss->free_col[pass];
        for(int free_value=0;free_value<prime;free_value++){
            memset(solutions[pass][free_value],0,NV);
            solutions[pass][free_value][free_col]=(unsigned char)free_value;
            for(int row=0;row<ss->rank[pass];row++){
                int col=ss->pivot_col[pass][row];
                int x=(b[row]-ss->coeff[pass][row][free_col]*free_value)%prime;
                if(x<0)x+=prime;
                solutions[pass][free_value][col]=(unsigned char)x;
            }
        }
    }
    int n=0;
    for(int a=0;a<2;a++)for(int b=0;b<13;b++){
        for(int v=0;v<NV;v++){
            int x=solutions[1][b][v];if((x&1)!=solutions[0][a][v])x+=13;
            out[n][v]=(unsigned char)x;
        }
        n++;
    }
    return n;
}

static void gen_perm_rec(int depth, unsigned used, unsigned char cur[W]) {
    if(depth==W){memcpy(perms[nperm++],cur,W);return;}
    for(int b=0;b<W;b++) if(!(used&(1u<<b))){cur[depth]=(unsigned char)b;gen_perm_rec(depth+1,used|(1u<<b),cur);}
}

static void make_perms(void) {
    unsigned char cur[W]; nperm=0; gen_perm_rec(0,0,cur);
    if(nperm!=NPERM){fprintf(stderr,"permutation count %d\n",nperm);exit(2);}
    nactive=NPERM;for(int i=0;i<NPERM;i++)active_perms[i]=i;
}

static int perm_rank(const unsigned char p[W]) {
    int rank=0;
    for(int i=0;i<W;i++) {
        int smaller=0;
        for(int j=i+1;j<W;j++)if(p[j]<p[i])smaller++;
        rank=rank*(W-i)+smaller;
    }
    return rank;
}

static void load_t8_filter(const char *path) {
    FILE *f=fopen(path,"r");if(!f){perror(path);exit(2);}
    unsigned char selected[NPERM]={0};
    char line[256];int words=0;
    while(fgets(line,sizeof(line),f)) {
        char word[9];int n=0,too_long=0;
        for(int i=0;line[i];i++)if(line[i]>='A'&&line[i]<='Z') {
            if(n<W)word[n++]=line[i];else too_long=1;
        }
        if(n!=W||too_long)continue;
        word[W]=0;words++;
        int order[W];for(int i=0;i<W;i++)order[i]=i;
        for(int i=1;i<W;i++) {
            int x=order[i],j=i-1;
            while(j>=0 && (word[order[j]]>word[x] || (word[order[j]]==word[x] && order[j]>x))) {
                order[j+1]=order[j];j--;
            }
            order[j+1]=x;
        }
        unsigned char block_at_col[W];
        for(int block=0;block<W;block++)block_at_col[order[block]]=(unsigned char)block;
        int pi=perm_rank(block_at_col);
        if(pi<0||pi>=NPERM||memcmp(perms[pi],block_at_col,W)){fprintf(stderr,"T8 permutation indexing failed\n");exit(2);}
        selected[pi]=1;
        if(!t8_word_by_perm[pi][0])strcpy(t8_word_by_perm[pi],word);
    }
    fclose(f);
    nactive=0;for(int i=0;i<NPERM;i++)if(selected[i])active_perms[nactive++]=i;
    if(!nactive){fprintf(stderr,"no usable 8-letter T8 keys in %s\n",path);exit(2);}
    printf("T8-filter entries loaded: words=%d distinct_permutations=%d\n",words,nactive);
}

static inline uint32_t tuple_code(const int *x, int n) {
    uint32_t z=0;
    for(int i=0;i<n;i++)z=z*A+(uint32_t)x[i];
    return z;
}

static void add_word_filter(const char *word, int len) {
    int v[7], d[6];
    for(int i=0;i<len;i++){v[i]=kindex[(unsigned char)word[i]];if(v[i]<0)return;}
    for(int i=1;i<len;i++){d[i-1]=(v[i]-v[0])%A;if(d[i-1]<0)d[i-1]+=A;}
    uint32_t bit=UINT32_C(1)<<v[0];
    if(len==5) wordmask5[tuple_code(d,4)]|=bit;
    else if(len==6) wordmask6[tuple_code(d,5)]|=bit;
    else if(len==7) {
        uint32_t code=tuple_code(d,6), at=(code*UINT32_C(2654435761))&(H7SIZE-1);
        while(h7used[at] && h7code[at]!=code)at=(at+1)&(H7SIZE-1);
        h7used[at]=1;h7code[at]=code;h7mask[at]|=bit;
    }
}

static void build_word_filter(void) {
    wordmask5=calloc(SPACE5,sizeof(*wordmask5));
    wordmask6=calloc(SPACE6,sizeof(*wordmask6));
    if(!wordmask5||!wordmask6){fprintf(stderr,"word-filter allocation failed\n");exit(2);}
    const char *paths[]={"kryptos/all_words.txt","kryptos/words_5.txt","kryptos/words_6.txt","kryptos/words_7.txt"};
    long long loaded[8]={0};
    for(int fno=0;fno<4;fno++) {
        FILE *f=fopen(paths[fno],"r");if(!f){perror(paths[fno]);exit(2);}
        char line[128];
        while(fgets(line,sizeof(line),f)) {
            char w[8];int n=0;
            for(int i=0;line[i]&&n<7;i++)if(line[i]>='A'&&line[i]<='Z')w[n++]=line[i];
            if(n<5||n>7)continue;
            /* Reject lines longer than the captured prefix. */
            int more=0;for(int i=n;line[i];i++)if(line[i]>='A'&&line[i]<='Z')more=1;
            if(more)continue;
            w[n]=0;add_word_filter(w,n);loaded[n]++;
        }
        fclose(f);
    }
    printf("word-filter entries loaded: len5=%lld len6=%lld len7=%lld\n",loaded[5],loaded[6],loaded[7]);
}

static void init_pk8_bridge(void) {
    FILE *f=fopen("kryptos/words_4.txt","r");if(!f){perror("kryptos/words_4.txt");exit(2);}
    char line[128];nbridge_w4=0;
    while(fgets(line,sizeof(line),f)&&nbridge_w4<MAX_W4) {
        char w[5];int n=0,letters=0;
        for(int i=0;line[i];i++)if(line[i]>='A'&&line[i]<='Z'){letters++;if(n<4)w[n++]=line[i];}
        if(letters!=4)continue;
        w[4]=0;strcpy(bridge_w4[nbridge_w4],w);
        for(int i=0;i<4;i++)bridge_q4[nbridge_w4][i]=(unsigned char)kindex[(unsigned char)w[i]];
        nbridge_w4++;
    }
    fclose(f);
    for(int i=0;i<N8;i++)bridge_ct8[i]=kindex[(unsigned char)PK8[i]];
    printf("PK8 bridge: q4_words=%d\n",nbridge_w4);
}

static uint32_t lookup7(uint32_t code) {
    uint32_t at=(code*UINT32_C(2654435761))&(H7SIZE-1);
    while(h7used[at]){if(h7code[at]==code)return h7mask[at];at=(at+1)&(H7SIZE-1);}
    return 0;
}

static int word_key_hit(const unsigned char key[NV], char out[32]) {
    int d5[4],d6[5],d7[6];
    for(int i=0;i<4;i++)d5[i]=key[i];
    for(int i=0;i<5;i++)d6[i]=key[4+i];
    for(int i=0;i<6;i++){d7[i]=(key[10+i]-key[9])%A;if(d7[i]<0)d7[i]+=A;}
    uint32_t m5=wordmask5[tuple_code(d5,4)];if(!m5)return 0;
    uint32_t m6=wordmask6[tuple_code(d6,5)];if(!m6)return 0;
    uint32_t m7=lookup7(tuple_code(d7,6));if(!m7)return 0;
    for(int a=0;a<A;a++)if(m5&(UINT32_C(1)<<a))
        for(int b=0;b<A;b++)if(m6&(UINT32_C(1)<<b)) {
            int c=(key[9]-a-b)%A;if(c<0)c+=A;
            if(!(m7&(UINT32_C(1)<<c)))continue;
            int pos=0;
            for(int i=0;i<5;i++){int z=(i?key[i-1]:0)+a;out[pos++]=KALPH[z%A];}
            out[pos++]='/';
            for(int i=0;i<6;i++){int z=(i?key[4+i-1]:0)+b;out[pos++]=KALPH[z%A];}
            out[pos++]='/';
            for(int i=0;i<7;i++){int z=(key[9+i]-a-b)%A;if(z<0)z+=A;out[pos++]=KALPH[z];}
            out[pos]=0;
            return 1;
        }
    return 0;
}

static void encrypt_control(int ct[N], int word_control) {
    int q5[5]={11,3,24,8,17},q6[6]={9,21,2,14,6,25},q7[7]={4,19,0,23,12,7,16};
    int order[W]={5,1,7,0,3,6,2,4};
    if(word_control) {
        for(int i=0;i<5;i++)q5[i]=kindex[(unsigned char)"STEEL"[i]];
        for(int i=0;i<6;i++)q6[i]=kindex[(unsigned char)"SILVER"[i]];
        for(int i=0;i<7;i++)q7[i]=kindex[(unsigned char)"DRAWING"[i]];
        for(int i=0;i<W;i++)order[i]=i;
        for(int i=1;i<W;i++) {
            int x=order[i],j=i-1;
            while(j>=0 && ("LANGUAGE"[order[j]]>"LANGUAGE"[x] ||
                  ("LANGUAGE"[order[j]]=="LANGUAGE"[x] && order[j]>x))) {
                order[j+1]=order[j];j--;
            }
            order[j+1]=x;
        }
    }
    int z[N],out=0;
    for(int i=0;i<N;i++) z[i]=(kindex[(unsigned char)CONTROL_PLAIN[i]]+q5[i%5]+q6[i%6])%A;
    for(int b=0;b<W;b++) for(int r=0;r<H;r++){int source=out++;ct[source]=(z[r*W+order[b]]+q7[source%7])%A;}
}

static void precompute_base(const int ct[N], int offset) {
    #pragma omp parallel for schedule(static)
    for(int p=0;p<NPERM;p++) {
        if(!perm_valid[p])continue;
        int y[CRIB_ROWS];
        for(int row=0;row<CRIB_ROWS;row++) {
            int i=offset+row;
            y[row]=ct[perms[p][i%W]*H+i/W];
        }
        for(int v=0;v<NV;v++) {
            int z=0; for(int i=0;i<CRIB_ROWS;i++) z+=inv26[p][v][i]*y[i];
            base_key[p][v]=(unsigned char)(z%A);
        }
    }
}

static inline int crib_matches(const int ct[N], const unsigned char key[NV],
                               const unsigned char block_at_col[W],
                               const char *crib, int offset, int len) {
    int q5[5]={0,key[0],key[1],key[2],key[3]};
    int q6[6]={0,key[4],key[5],key[6],key[7],key[8]};
    const unsigned char *q7=key+9;
    /* The first NV letters constructed the key. Check any extra letters. */
    for(int j=NV;j<len;j++) {
        int i=offset+j,c=i%W,r=i/W;
        int source=block_at_col[c]*H+r;
        int x=ct[source]-q5[i%5]-q6[i%6]-q7[source%7];
        x%=A;if(x<0)x+=A;
        if(x!=kindex[(unsigned char)crib[j]])return 0;
    }
    return 1;
}

static inline float decrypt_score(const int ct[N], const unsigned char key[NV],
                                  const unsigned char block_at_col[W], char out[N+1]) {
    int q5[5]={0,key[0],key[1],key[2],key[3]};
    int q6[6]={0,key[4],key[5],key[6],key[7],key[8]};
    const unsigned char *q7=key+9;
    int p[N];
    for(int i=0;i<N;i++) {
        int c=i%W,r=i/W;
        int source=block_at_col[c]*H+r;
        int x=ct[source]-q5[i%5]-q6[i%6]-q7[source%7];
        x%=A;if(x<0)x+=A;
        p[i]=to_std[x]; out[i]=(char)('A'+p[i]);
    }
    out[N]=0;
    float s=0;
    for(int i=0;i<=N-4;i++) s+=quad[qidx(p[i],p[i+1],p[i+2],p[i+3])];
    return s/(N-3);
}

static BridgeHit evaluate_pk8_bridge(const int ct9[N],const unsigned char key[NV],
                                     const unsigned char perm[W],const char *words,
                                     const char *crib,int offset) {
    BridgeHit h;h.pk9_score=decrypt_score(ct9,key,perm,h.pk9_plain);
    h.pk8_score=-1e30f;int q5[5]={0,key[0],key[1],key[2],key[3]};
    int q6[6]={0,key[4],key[5],key[6],key[7],key[8]};const unsigned char*q7=key+9;
    int bestp[N8];
    for(int w=0;w<nbridge_w4;w++) {
        int p[N8];float s=0;
        for(int i=0;i<N8;i++) {
            int x=bridge_ct8[i]-bridge_q4[w][i%4]-q5[i%5]-q6[i%6]-q7[i%7];
            x%=A;if(x<0)x+=A;p[i]=to_std[x];
            if(i>=3)s+=quad[qidx(p[i-3],p[i-2],p[i-1],p[i])];
        }
        s/=(N8-3);
        if(s>h.pk8_score){h.pk8_score=s;memcpy(bestp,p,sizeof(bestp));strcpy(h.q4,bridge_w4[w]);}
    }
    for(int i=0;i<N8;i++)h.pk8_plain[i]=(char)('A'+bestp[i]);
    h.pk8_plain[N8]=0;
    h.combined=(h.pk8_score+h.pk9_score)*0.5f;h.offset=offset;
    strcpy(h.crib,crib);strcpy(h.word_keys,words);memcpy(h.key,key,NV);memcpy(h.perm,perm,W);
    return h;
}

static void insert_bridge(BridgeHit top[TOP],const BridgeHit*h) {
    for(int j=0;j<TOP;j++)if(top[j].combined>-1e20f&&top[j].offset==h->offset&&
        !memcmp(top[j].key,h->key,NV)&&!memcmp(top[j].perm,h->perm,W))return;
    if(h->combined<=top[TOP-1].combined)return;
    int i=TOP-1;
    while(i>0&&h->combined>top[i-1].combined){top[i]=top[i-1];i--;}
    top[i]=*h;
}

static void insert_hit(Hit top[TOP], const Hit *h) {
    if(h->score<=top[TOP-1].score)return;
    int i=TOP-1;
    while(i>0 && h->score>top[i-1].score){top[i]=top[i-1];i--;}
    top[i]=*h;
}

static int load_cribs(const char *path, char (**out)[65]) {
    FILE *f=fopen(path,"r"); if(!f){perror(path);exit(2);}
    int cap=4096,n=0; char (*a)[65]=malloc((size_t)cap*65); char line[512];
    while(fgets(line,sizeof(line),f)) {
        char clean[65]; int k=0;
        for(int i=0;line[i]&&k<64;i++) if(line[i]>='A'&&line[i]<='Z')clean[k++]=line[i];
        if(k<NV) continue;
        clean[k]=0;
        if(n==cap){cap*=2;a=realloc(a,(size_t)cap*65);if(!a)exit(2);}
        strcpy(a[n++],clean);
    }
    fclose(f); *out=a; return n;
}

static void print_hit(const Hit *h,int rank) {
    printf("\n#%d score=%.6f offset=%d crib=%s",rank,h->score,h->offset,h->crib);
    if(h->word_keys[0])printf(" word_keys=%s",h->word_keys);
    if(h->t8_key[0])printf(" t8_key=%s",h->t8_key);
    printf("\n");
    printf("q5=[0,%d,%d,%d,%d]\n",h->key[0],h->key[1],h->key[2],h->key[3]);
    printf("q6=[0,%d,%d,%d,%d,%d]\n",h->key[4],h->key[5],h->key[6],h->key[7],h->key[8]);
    printf("q7=[");for(int i=9;i<NV;i++)printf("%d%s",h->key[i],i==NV-1?"]\n":",");
    printf("block_at_col=[");for(int i=0;i<W;i++)printf("%d%s",h->perm[i],i==W-1?"]\n":",");
    printf("plaintext=%s\n",h->plain);
}

static void print_bridge(const BridgeHit*h,int rank) {
    printf("\nBRIDGE #%d combined=%.6f pk8=%.6f pk9=%.6f offset=%d crib=%s\n",
           rank,h->combined,h->pk8_score,h->pk9_score,h->offset,h->crib);
    printf("shared_q567=%s pk8_q4=%s\n",h->word_keys,h->q4);
    printf("pk8_plaintext=%s\n",h->pk8_plain);
    printf("pk9_plaintext=%s\n",h->pk9_plain);
}

int main(int argc,char **argv) {
    int word_t8_self=argc==2 && !strcmp(argv[1],"--word-t8-self-test");
    int word_self=(argc==2 && !strcmp(argv[1],"--word-self-test")) || word_t8_self;
    int self=(argc==2 && !strcmp(argv[1],"--self-test")) || word_self;
    int t8_all_keys=argc==4 && (!strcmp(argv[1],"--all-keys-t8") || !strcmp(argv[1],"--all-keys-t8-all-offsets"));
    int t8_filter=word_t8_self || t8_all_keys || (argc==4 && (!strcmp(argv[1],"--word-filter-t8") || !strcmp(argv[1],"--word-filter-t8-all-offsets")));
    int bridge=argc==3 && (!strcmp(argv[1],"--bridge-pk8") || !strcmp(argv[1],"--bridge-pk8-all-offsets"));
    int all_keys=t8_all_keys || (argc==3 && (!strcmp(argv[1],"--all-keys") || !strcmp(argv[1],"--all-keys-all-offsets")));
    int word_filter=word_self || (t8_filter&&!t8_all_keys) || bridge || (argc==3 && (!strcmp(argv[1],"--word-filter") || !strcmp(argv[1],"--word-filter-all-offsets")));
    int all_offsets=(argc==3 && (!strcmp(argv[1],"--all-offsets") || !strcmp(argv[1],"--word-filter-all-offsets") || !strcmp(argv[1],"--bridge-pk8-all-offsets") || !strcmp(argv[1],"--all-keys-all-offsets"))) ||
                    (t8_filter && (!strcmp(argv[1],"--word-filter-t8-all-offsets") || !strcmp(argv[1],"--all-keys-t8-all-offsets")));
    if(!(self || argc==2 || all_offsets || word_filter || all_keys)) {
        fprintf(stderr,"usage: %s CRIB_FILE | --all-offsets CRIB_FILE | --word-filter CRIB_FILE | --word-filter-all-offsets CRIB_FILE | --word-filter-t8 T8_WORDS CRIB_FILE | --word-filter-t8-all-offsets T8_WORDS CRIB_FILE | --all-keys-t8 T8_WORDS CRIB_FILE | --all-keys-t8-all-offsets T8_WORDS CRIB_FILE | --all-keys CRIB_FILE | --all-keys-all-offsets CRIB_FILE | --bridge-pk8 CRIB_FILE | --bridge-pk8-all-offsets CRIB_FILE | --self-test | --word-self-test | --word-t8-self-test\n",argv[0]);
        return 2;
    }
    memset(kindex,-1,sizeof(kindex));
    for(int i=0;i<A;i++){kindex[(unsigned char)KALPH[i]]=i;to_std[i]=KALPH[i]-'A';}
    quad=load_quads(); make_perms();
    if(word_filter) {
        build_word_filter();
        unsigned char probe[NV];
        int a=kindex[(unsigned char)'S'],b=kindex[(unsigned char)'S'];
        for(int i=1;i<5;i++)probe[i-1]=(unsigned char)((kindex[(unsigned char)"STEEL"[i]]-a+A)%A);
        for(int i=1;i<6;i++)probe[4+i-1]=(unsigned char)((kindex[(unsigned char)"SILVER"[i]]-b+A)%A);
        for(int i=0;i<7;i++)probe[9+i]=(unsigned char)((kindex[(unsigned char)"DRAWING"[i]]+a+b)%A);
        char words[32];
        if(!word_key_hit(probe,words)){fprintf(stderr,"word-filter positive control failed\n");return 2;}
        printf("word-filter positive control: %s\n",words);
    }
    if(t8_filter)load_t8_filter(word_t8_self?"kryptos/theophilus_w8.txt":argv[2]);
    if(bridge)init_pk8_bridge();
    int ct[N]; char (*cribs)[65]=NULL; int nc=0;
    if(self) {
        encrypt_control(ct,word_self);
        cribs=malloc(2*65);
        strcpy(cribs[0],"THEWHITESMITHSWORKSHOPISFILLED");
        strcpy(cribs[1],"THEWHITESMITHSWORKSHOPISFILLED");
        nc=2;
    } else {
        for(int i=0;i<N;i++)ct[i]=kindex[(unsigned char)PK9[i]];
        const char *crib_path=t8_filter?argv[3]:((all_offsets||word_filter||all_keys)?argv[2]:argv[1]);
        nc=load_cribs(crib_path,&cribs);
    }
    int first_offset=0,last_offset=0;
    if(all_offsets)for(int ci=0;ci<nc;ci++) {
        int last=N-(int)strlen(cribs[ci]);
        if(last>last_offset)last_offset=last;
    }
    long long placements=0;
    for(int ci=0;ci<nc;ci++) {
        int len=(int)strlen(cribs[ci]);
        placements+=all_offsets?(len<=N?N-len+1:0):(len<=N);
    }
    long long candidates=placements*nactive;
    printf("cribs=%d offsets=%d placements=%lld permutations=%d candidates=%lld threads=%d\n",
           nc,last_offset-first_offset+1,placements,nactive,candidates,omp_get_max_threads());
    double t0=omp_get_wtime();
    Hit global[TOP];for(int i=0;i<TOP;i++)global[i].score=-1e30f;
    BridgeHit bridge_global[TOP];for(int i=0;i<TOP;i++)bridge_global[i].combined=-1e30f;
    long long word_hits=0, verified_word_hits=0;

    for(int offset=first_offset;offset<=last_offset;offset++) {
        build_inverse(offset);
        precompute_base(ct,offset);
        #pragma omp parallel
        {
            Hit local[TOP];for(int i=0;i<TOP;i++)local[i].score=-1e30f;
            BridgeHit bridge_local[TOP];for(int i=0;i<TOP;i++)bridge_local[i].combined=-1e30f;
            #pragma omp for schedule(dynamic,1)
            for(int ci=0;ci<nc;ci++) {
                int crib_len=(int)strlen(cribs[ci]);
                if(crib_len<CRIB_ROWS||offset+crib_len>N)continue;
                int pv[CRIB_ROWS];
                for(int i=0;i<CRIB_ROWS;i++)pv[i]=kindex[(unsigned char)cribs[ci][i]];
                for(int pj=0;pj<nactive;pj++) {
                    int pi=active_perms[pj],nsolutions;
                    unsigned char keys[26][NV];
                    if(perm_valid[pi]) {
                        int projected[NV];
                        for(int v=0;v<NV;v++){int z=0;for(int i=0;i<CRIB_ROWS;i++)z+=inv26[pi][v][i]*pv[i];projected[v]=z%A;}
                        for(int v=0;v<NV;v++)keys[0][v]=(unsigned char)((base_key[pi][v]-projected[v]+A)%A);
                        nsolutions=1;
                    } else nsolutions=singular_keys(pi,ct,pv,offset,keys);
                    for(int solution=0;solution<nsolutions;solution++) {
                        Hit h;
                        memcpy(h.key,keys[solution],NV);
                        h.word_keys[0]=0;h.t8_key[0]=0;
                        if(t8_filter)strcpy(h.t8_key,t8_word_by_perm[pi]);
                        if(word_filter && !word_key_hit(h.key,h.word_keys))continue;
                        if(word_filter) {
                            #pragma omp atomic
                            word_hits++;
                        }
                        if(bridge) {
                            BridgeHit bh=evaluate_pk8_bridge(ct,h.key,perms[pi],h.word_keys,cribs[ci],offset);
                            insert_bridge(bridge_local,&bh);
                        }
                        if(!crib_matches(ct,h.key,perms[pi],cribs[ci],offset,crib_len))continue;
                        if(word_filter||all_keys) {
                            #pragma omp atomic
                            verified_word_hits++;
                        }
                        h.score=decrypt_score(ct,h.key,perms[pi],h.plain);
                        if(h.score>local[TOP-1].score) {
                            h.offset=offset;
                            strcpy(h.crib,cribs[ci]);
                            memcpy(h.perm,perms[pi],W);
                            insert_hit(local,&h);
                        }
                    }
                }
            }
            #pragma omp critical
            {
                for(int i=0;i<TOP;i++){insert_hit(global,&local[i]);insert_bridge(bridge_global,&bridge_local[i]);}
            }
        }
        if(all_offsets && (offset%16==15 || offset==last_offset)) {
            if(global[0].score>-1e20f)fprintf(stderr,"offset %d/%d best %.6f\n",offset,last_offset,global[0].score);
            else fprintf(stderr,"offset %d/%d no full-crib survivor\n",offset,last_offset);
        }
    }
    double elapsed=omp_get_wtime()-t0;
    printf("elapsed=%.3fs rate=%.3f million candidates/s",elapsed,candidates/elapsed/1e6);
    if(word_filter)printf(" word_key_hits=%lld full_crib_hits=%lld",word_hits,verified_word_hits);
    else if(all_keys)printf(" full_crib_hits=%lld",verified_word_hits);
    printf("\n");
    for(int i=0;i<TOP;i++)if(global[i].score>-1e20f)print_hit(&global[i],i+1);
    if(bridge)for(int i=0;i<TOP;i++)if(bridge_global[i].combined>-1e20f)print_bridge(&bridge_global[i],i+1);
    if(self){int ok=!strcmp(global[0].plain,CONTROL_PLAIN);printf("self_test_exact=%s\n",ok?"PASS":"FAIL");free(cribs);return ok?0:1;}
    free(cribs);return 0;
}
