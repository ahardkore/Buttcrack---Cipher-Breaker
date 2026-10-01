/*
 * Exact cross-cipher test of a concrete PK8/PK9 bridge hypothesis:
 *
 * PK8[i] = P8[i] + Q4[i%4] + Q5[i%5] + Q6[i%6] + Q7[i%7]
 * Z9[i]  = P9[i]            + Q5[i%5] + Q6[i%6] + Q7[i%7]
 * PK9     = complete-columnar-T8(Z9)
 *
 * If Q5/Q6/Q7 are shared and phase-aligned, subtracting each proposed inverse
 * T8 of PK9 from PK8 cancels all three clocks.  The residual is the difference
 * of two English plaintexts plus Q4.  We rank all 8! T8 assignments using the
 * exact English-letter-difference distribution, optimizing all four Q4 shifts
 * independently.  A stronger English-bigram-difference model then re-ranks the
 * unary finalists while optimizing the four-state Q4 cycle exactly by max-sum
 * dynamic programming.
 *
 * This is a falsifiable bridge test, not an assertion that the public
 * Q4567/Q567T8 architecture or shared-wheel premise is established.
 */

#include <math.h>
#include <omp.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define A 26
#define N8 153
#define N9 144
#define W 8
#define H 18
#define NPERM 40320
#define PAIR_FINALISTS 2000

static const char *KALPH="KRYPTOSABCDEFGHIJLMNQUVWXZ";
static const char *C8S=
 "COPVEJJVSVURTVIPYOTPLHGBTMAUCCPESIWIGZBWSJPKTRPUEKQFIFCLHMXTHIMHWO"
 "YIGURBOMPARCVXVKBDDVBVHDRHGCVNWWVLBMYWMWHICFIXZWBVZYCQGNOGJGUMLNPUT"
 "HQCXNWPQZOIRJZGSWVPY";
static const char *C9S=
 "KSYAWFEYYOISZGEUFBLYATAIBYFAQBQYYVDWJKLJXMYIEPIFVHPQNHZGSUHUUDXLEH"
 "RHUMALHEGLHXSJMUXGNUIVBXGUJHZRZGUSVHMLSCTSUQXHSUMQQIFUQGKHJGUQGLHDK"
 "EWSKAMHIJXD";
static const char *P8_CONTROL=
 "THEWHITESMITHSWORKSHOPISFILLEDWITHTHEOLDTOOLSOFHISTRADEMYEYESAREDRAWN"
 "TOTHEGUTTERALONGTHEWALLWHICHISSTREWNWITHEXQUISITENEEDLESTHEWHITESMITHS"
 "AYSHEMAKESONEE";
static const char *P9_CONTROL=
 "HEPOINTEDTOTHEHEARTHANDSAIDTHATTHEWORKCOULDONLYBEGINWHENTHEFIREREACHEDI"
 "TSPROPERHEATWITHLONGTONGSHEHELDTHESTEELINTOCOALSTHATGLOWEDWHITEINTHEBEL"
 "LO";

static int kindex[256],c8[N8],c9[N9];
static unsigned char perms[NPERM][W];
static int nperm;
static double logdiff[A],logdiffpair[A][A];

typedef struct {
    int pi;
    double unary,pair;
    unsigned char q4[4];
} Candidate;

static void gen_perm(int d,unsigned used,unsigned char cur[W]) {
    if(d==W){memcpy(perms[nperm++],cur,W);return;}
    for(int b=0;b<W;b++)if(!(used&(1u<<b))){cur[d]=(unsigned char)b;gen_perm(d+1,used|(1u<<b),cur);}
}

static void init_model(void) {
    memset(kindex,-1,sizeof(kindex));for(int i=0;i<A;i++)kindex[(unsigned char)KALPH[i]]=i;
    for(int i=0;i<N8;i++)c8[i]=kindex[(unsigned char)C8S[i]];
    for(int i=0;i<N9;i++)c9[i]=kindex[(unsigned char)C9S[i]];
    unsigned char cur[W];gen_perm(0,0,cur);if(nperm!=NPERM){fprintf(stderr,"bad permutation count\n");exit(2);}

    double bg[A][A];memset(bg,0,sizeof(bg));
    FILE*f=popen("gzip -cd -- 'buttcrack/data/english_bigrams.txt.gz'","r");
    if(!f){fprintf(stderr,"cannot load bigrams\n");exit(2);}char line[128],g[8];long long count,total=0;
    while(fgets(line,sizeof(line),f))if(sscanf(line,"%7s %lld",g,&count)==2&&strlen(g)==2) {
        int a=g[0]-'A',b=g[1]-'A';if(a>=0&&a<A&&b>=0&&b<A){bg[kindex[(unsigned char)g[0]]][kindex[(unsigned char)g[1]]]+=(double)count;total+=count;}
    }
    if(pclose(f)!=0||!total){fprintf(stderr,"bad bigrams\n");exit(2);}
    double mono[A]={0};for(int a=0;a<A;a++)for(int b=0;b<A;b++){bg[a][b]/=(double)total;mono[a]+=bg[a][b];}
    double diff[A]={0},dp[A][A];memset(dp,0,sizeof(dp));
    for(int a=0;a<A;a++)for(int b=0;b<A;b++)diff[(a-b+A)%A]+=mono[a]*mono[b];
    for(int a=0;a<A;a++)for(int b=0;b<A;b++)for(int c=0;c<A;c++)for(int d=0;d<A;d++)
        dp[(a-c+A)%A][(b-d+A)%A]+=bg[a][b]*bg[c][d];
    for(int x=0;x<A;x++){logdiff[x]=log10(diff[x]+1e-300);for(int y=0;y<A;y++)logdiffpair[x][y]=log10(dp[x][y]+1e-300);}
}

static inline int z9_at(const int ct[N9],int pi,int i) {
    int c=i%W,r=i/W;return ct[perms[pi][c]*H+r];
}

static Candidate score_unary(const int ct8[N8],const int ct9[N9],int pi) {
    int hist[4][A];memset(hist,0,sizeof(hist));
    for(int i=0;i<N9;i++)hist[i%4][(ct8[i]-z9_at(ct9,pi,i)+A)%A]++;
    Candidate out={.pi=pi,.unary=0,.pair=-1e300};
    for(int r=0;r<4;r++) {
        double best=-1e300;int bq=0;
        for(int q=0;q<A;q++){double s=0;for(int d=0;d<A;d++)s+=hist[r][d]*logdiff[(d-q+A)%A];if(s>best){best=s;bq=q;}}
        out.q4[r]=(unsigned char)bq;out.unary+=best;
    }
    out.unary/=N9;return out;
}

static void score_pair(const int ct8[N8],const int ct9[N9],Candidate*out) {
    int raw[N9];for(int i=0;i<N9;i++)raw[i]=(ct8[i]-z9_at(ct9,out->pi,i)+A)%A;
    double edge[4][A][A];memset(edge,0,sizeof(edge));
    for(int i=0;i<N9-1;i++) {
        int r=i%4;
        for(int qa=0;qa<A;qa++)for(int qb=0;qb<A;qb++)
            edge[r][qa][qb]+=logdiffpair[(raw[i]-qa+A)%A][(raw[i+1]-qb+A)%A];
    }
    double global=-1e300;unsigned char bestq[4]={0};
    for(int q0=0;q0<A;q0++) {
        double d1[A],d2[A],d3[A];unsigned char p2[A],p3[A];
        for(int q1=0;q1<A;q1++)d1[q1]=edge[0][q0][q1];
        for(int q2=0;q2<A;q2++){d2[q2]=-1e300;p2[q2]=0;for(int q1=0;q1<A;q1++){double v=d1[q1]+edge[1][q1][q2];if(v>d2[q2]){d2[q2]=v;p2[q2]=(unsigned char)q1;}}}
        for(int q3=0;q3<A;q3++){d3[q3]=-1e300;p3[q3]=0;for(int q2=0;q2<A;q2++){double v=d2[q2]+edge[2][q2][q3];if(v>d3[q3]){d3[q3]=v;p3[q3]=(unsigned char)q2;}}}
        for(int q3=0;q3<A;q3++){double v=d3[q3]+edge[3][q3][q0];if(v>global){int q2=p3[q3],q1=p2[q2];global=v;bestq[0]=(unsigned char)q0;bestq[1]=(unsigned char)q1;bestq[2]=(unsigned char)q2;bestq[3]=(unsigned char)q3;}}
    }
    out->pair=global/(N9-1);memcpy(out->q4,bestq,4);
}

static int cmp_unary(const void*a,const void*b){double x=((const Candidate*)a)->unary,y=((const Candidate*)b)->unary;return x<y?1:x>y?-1:0;}
static int cmp_pair(const void*a,const void*b){double x=((const Candidate*)a)->pair,y=((const Candidate*)b)->pair;return x<y?1:x>y?-1:0;}

static int find_perm(const unsigned char p[W]){for(int i=0;i<NPERM;i++)if(!memcmp(perms[i],p,W))return i;return -1;}

static void make_control(int out8[N8],int out9[N9],int*truth_pi) {
    const int q4[4]={3,17,8,22},q5[5]={11,3,24,8,17},q6[6]={9,21,2,14,6,25},q7[7]={4,19,0,23,12,7,16};
    const unsigned char order[W]={5,1,7,0,3,6,2,4};unsigned char block_at_col[W];
    for(int b=0;b<W;b++)block_at_col[order[b]]=(unsigned char)b;
    *truth_pi=find_perm(block_at_col);
    for(int i=0;i<N8;i++)out8[i]=(kindex[(unsigned char)P8_CONTROL[i]]+q4[i%4]+q5[i%5]+q6[i%6]+q7[i%7])%A;
    int z[N9];for(int i=0;i<N9;i++)z[i]=(kindex[(unsigned char)P9_CONTROL[i]]+q5[i%5]+q6[i%6]+q7[i%7])%A;
    int at=0;for(int b=0;b<W;b++)for(int r=0;r<H;r++)out9[at++]=z[r*W+order[b]];
}

static void run_case(const char*label,const int ct8[N8],const int ct9[N9],int truth_pi) {
    Candidate*cand=malloc(NPERM*sizeof(*cand));if(!cand)exit(2);double t0=omp_get_wtime();
    #pragma omp parallel for schedule(static)
    for(int pi=0;pi<NPERM;pi++)cand[pi]=score_unary(ct8,ct9,pi);
    qsort(cand,NPERM,sizeof(*cand),cmp_unary);int truth_rank=-1;
    for(int i=0;i<NPERM;i++)if(cand[i].pi==truth_pi)truth_rank=i+1;
    printf("\n%s unary elapsed=%.3fs",label,omp_get_wtime()-t0);if(truth_pi>=0)printf(" truth_rank=%d/%d",truth_rank,NPERM);printf("\n");
    int nf=PAIR_FINALISTS;if(truth_pi>=0&&truth_rank>nf)nf=truth_rank;
    t0=omp_get_wtime();
    #pragma omp parallel for schedule(dynamic,1)
    for(int i=0;i<nf;i++)score_pair(ct8,ct9,&cand[i]);
    qsort(cand,nf,sizeof(*cand),cmp_pair);truth_rank=-1;for(int i=0;i<nf;i++)if(cand[i].pi==truth_pi)truth_rank=i+1;
    printf("%s pair finalists=%d elapsed=%.3fs",label,nf,omp_get_wtime()-t0);if(truth_pi>=0)printf(" truth_rank=%d/%d",truth_rank,nf);printf("\n");
    int show=nf<10?nf:10;
    for(int k=0;k<show;k++){Candidate*x=&cand[k];printf("#%d pair=%.6f unary=%.6f q4=[%d,%d,%d,%d] block_at_col=[",k+1,x->pair,x->unary,x->q4[0],x->q4[1],x->q4[2],x->q4[3]);for(int i=0;i<W;i++)printf("%d%s",perms[x->pi][i],i==W-1?"]\n":",");}
    free(cand);
}

int main(void) {
    if(strlen(C8S)!=N8||strlen(C9S)!=N9||strlen(P8_CONTROL)!=N8||strlen(P9_CONTROL)!=N9){fprintf(stderr,"length error %zu %zu %zu %zu\n",strlen(C8S),strlen(C9S),strlen(P8_CONTROL),strlen(P9_CONTROL));return 2;}
    init_model();int s8[N8],s9[N9],truth;make_control(s8,s9,&truth);
    printf("threads=%d exact_permutations=%d synthetic_truth_pi=%d\n",omp_get_max_threads(),NPERM,truth);
    run_case("SYNTHETIC",s8,s9,truth);
    run_case("REAL PK8/PK9",c8,c9,-1);
    return 0;
}
