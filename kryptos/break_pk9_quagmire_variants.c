/*
 * Controlled PK9 attack on nonuniform Quagmire variants.
 *
 * The solved Paradigm puzzles use Quagmire III("KRYPTOS", key), but this tests
 * whether PK9 changes family: each Q5/Q6/Q7 layer may be Quagmire I, II, III,
 * or the repository's two-argument Quagmire IV, using KRYPTOS as the alphabet
 * key. T8 may occur at any of the four boundaries and all six Q-layer orders
 * are covered. The unknown complete-columnar assignment is solved exactly for
 * the bigram objective and candidates are ranked by full quadgrams.
 *
 * Build from repository root:
 *   cc -std=c11 -O3 -march=native -fopenmp -Wall -Wextra -Werror \
 *      kryptos/break_pk9_quagmire_variants.c -o /tmp/pk9_qvariants -lm
 *   /tmp/pk9_qvariants --self-test
 *   OMP_NUM_THREADS=32 /tmp/pk9_qvariants
 *   /tmp/pk9_qvariants --fixed CLOCK BERLIN KRYPTOS
 */
#define main structured_included_main
#include "break_pk9_structured.c"
#undef main

#define NLAYERS 3

typedef struct {
    unsigned char enc[7][26];
    unsigned char dec[7][26];
} VariantMap;

static int find_in_alphabet(const int alphabet[26],int letter) {
    for(int i=0;i<26;i++)if(alphabet[i]==letter)return i;
    return -1;
}

static void make_variant_map(int type,const char *word,int period,VariantMap *out) {
    int standard[26],keyed[26],qi_top[26],top[26],rep[26];
    for(int i=0;i<26;i++)standard[i]=i;
    for(int i=0;i<26;i++)keyed[i]=KALPH[i]-'A';
    int at=0,used[26]={0};
    for(const char *p="KRYPTOS";*p;p++){int x=*p-'A';if(!used[x]){used[x]=1;qi_top[at++]=x;}}
    int dedup_len=at;
    at=0;memset(used,0,sizeof(used));
    for(int x=0;x<26;x++)if(!strchr("KRYPTOS",'A'+x)){qi_top[at++]=x;used[x]=1;}
    for(int i=0;i<dedup_len;i++){int x="KRYPTOS"[i]-'A';if(!used[x]){qi_top[at++]=x;used[x]=1;}}
    if(at!=26){fprintf(stderr,"internal alphabet error\n");exit(2);}

    if(type==0){memcpy(top,qi_top,sizeof(top));memcpy(rep,standard,sizeof(rep));}
    else if(type==1){memcpy(top,standard,sizeof(top));memcpy(rep,keyed,sizeof(rep));}
    else if(type==2){memcpy(top,keyed,sizeof(top));memcpy(rep,keyed,sizeof(rep));}
    else {memcpy(top,standard,sizeof(top));memcpy(rep,keyed,sizeof(rep));}

    for(int phase=0;phase<period;phase++) {
        int literal=word[phase]-'A';
        int key_index=type==3?literal:find_in_alphabet(rep,literal);
        if(key_index<0){fprintf(stderr,"bad indicator letter\n");exit(2);}
        for(int letter=0;letter<26;letter++) {
            int input=find_in_alphabet(top,letter);
            int encoded=rep[(input+key_index)%26];
            out->enc[phase][letter]=(unsigned char)encoded;
            out->dec[phase][encoded]=(unsigned char)letter;
        }
    }
}

static Hit solve_variant(const int ct[N],const char *w5,const char *w6,const char *w7,
                         const int types[3],const int layer_order[3],int split) {
    const char *words[3]={w5,w6,w7};
    const int periods[3]={5,6,7};
    VariantMap maps[3];
    for(int layer=0;layer<3;layer++)make_variant_map(types[layer],words[layer],periods[layer],&maps[layer]);

    unsigned char decoded[WIDTH][WIDTH][HEIGHT];
    for(int col=0;col<WIDTH;col++)for(int block=0;block<WIDTH;block++)for(int row=0;row<HEIGHT;row++){
        int source=block*HEIGHT+row,destination=row*WIDTH+col;
        int x=ct[source];
        for(int k=2;k>=split;k--){int layer=layer_order[k];x=maps[layer].dec[source%periods[layer]][x];}
        for(int k=split-1;k>=0;k--){int layer=layer_order[k];x=maps[layer].dec[destination%periods[layer]][x];}
        decoded[col][block][row]=(unsigned char)x;
    }

    float edge[WIDTH][WIDTH][WIDTH]={{{0}}},boundary[WIDTH][WIDTH]={{0}};
    for(int col=1;col<WIDTH;col++)for(int a=0;a<WIDTH;a++)for(int b=0;b<WIDTH;b++)if(a!=b)
        for(int row=0;row<HEIGHT;row++)edge[col][a][b]+=bigram[decoded[col-1][a][row]*26+decoded[col][b][row]];
    for(int a=0;a<WIDTH;a++)for(int b=0;b<WIDTH;b++)if(a!=b)
        for(int row=0;row<HEIGHT-1;row++)boundary[a][b]+=bigram[decoded[7][a][row]*26+decoded[0][b][row+1]];

    float best=-1e30f;unsigned char best_order[WIDTH]={0};
    for(int first=0;first<WIDTH;first++){
        float dp[1<<WIDTH][WIDTH];signed char parent[1<<WIDTH][WIDTH];
        for(int mask=0;mask<(1<<WIDTH);mask++)for(int b=0;b<WIDTH;b++){dp[mask][b]=-1e30f;parent[mask][b]=-1;}
        dp[1<<first][first]=0;
        for(int mask=1;mask<(1<<WIDTH);mask++){
            if(!(mask&(1<<first)))continue;
            int used_count=__builtin_popcount((unsigned)mask);
            if(used_count>=WIDTH)continue;
            for(int last=0;last<WIDTH;last++){float base=dp[mask][last];if(base<-1e20f)continue;
                for(int b=0;b<WIDTH;b++)if(!(mask&(1<<b))){int next=mask|(1<<b);float value=base+edge[used_count][last][b];if(value>dp[next][b]){dp[next][b]=value;parent[next][b]=(signed char)last;}}}
        }
        int full=(1<<WIDTH)-1;
        for(int last=0;last<WIDTH;last++){float value=dp[full][last]+boundary[last][first];if(value<=best)continue;best=value;int mask=full,cur=last;for(int col=WIDTH-1;col>=0;col--){best_order[col]=(unsigned char)cur;int previous=parent[mask][cur];mask^=1<<cur;cur=previous;}}
    }

    Hit hit={0};hit.bigram_score=best/(N-1);strcpy(hit.q5,w5);strcpy(hit.q6,w6);strcpy(hit.q7,w7);memcpy(hit.block_at_col,best_order,WIDTH);
    int plain[N];float qscore=0;
    for(int row=0;row<HEIGHT;row++)for(int col=0;col<WIDTH;col++){int i=row*WIDTH+col;plain[i]=decoded[col][best_order[col]][row];hit.plain[i]=(char)('A'+plain[i]);}
    hit.plain[N]=0;for(int i=0;i<=N-4;i++)qscore+=quad[qidx(plain[i],plain[i+1],plain[i+2],plain[i+3])];hit.quad_score=qscore/(N-3);
    return hit;
}

static void encrypt_variant_control(int ct[N],const int types[3],const int order[3],int split) {
    const char *words[3]={"IRATE","PIRATE","PIRATES"};const int periods[3]={5,6,7};VariantMap maps[3];
    for(int layer=0;layer<3;layer++)make_variant_map(types[layer],words[layer],periods[layer],&maps[layer]);
    int stage[N];for(int i=0;i<N;i++){int x=CONTROL_PLAIN[i]-'A';for(int k=0;k<split;k++){int layer=order[k];x=maps[layer].enc[i%periods[layer]][x];}stage[i]=x;}
    const char *keyword="LANGUAGE";int read[WIDTH];for(int i=0;i<WIDTH;i++)read[i]=i;
    for(int i=1;i<WIDTH;i++){int x=read[i],j=i-1;while(j>=0&&(keyword[read[j]]>keyword[x]||(keyword[read[j]]==keyword[x]&&read[j]>x))){read[j+1]=read[j];j--;}read[j+1]=x;}
    int out=0;for(int block=0;block<WIDTH;block++)for(int row=0;row<HEIGHT;row++){int source=out++;int x=stage[row*WIDTH+read[block]];for(int k=split;k<3;k++){int layer=order[k];x=maps[layer].enc[source%periods[layer]][x];}ct[source]=x;}
}

static const char *type_name(int type){static const char*n[]={"QI","QII","QIII","QIV"};return n[type];}
static void show_variant(const Hit *h,const int types[3],const int order[3],int split,const char *label){
    printf("\n%s quad=%.6f bigram=%.6f keys=%s/%s/%s types=%s/%s/%s order=Q%d,Q%d,Q%d split=%d\n",
           label,h->quad_score,h->bigram_score,h->q5,h->q6,h->q7,type_name(types[0]),type_name(types[1]),type_name(types[2]),
           (int[]){5,6,7}[order[0]],(int[]){5,6,7}[order[1]],(int[]){5,6,7}[order[2]],split);
    printf("plaintext=%s\n",h->plain);
}

static void init_variant_attack(void){
    memset(kindex,-1,sizeof(kindex));for(int i=0;i<26;i++){kindex[(unsigned char)KALPH[i]]=i;to_std[i]=KALPH[i]-'A';}
    quad=load_ngram("buttcrack/data/english_quadgrams.txt.gz",4,QSIZE);bigram=load_ngram("buttcrack/data/english_bigrams.txt.gz",2,BSIZE);load_words();
    for(int i=0;i<N;i++)target_ct[i]=PK9[i]-'A';
}

int main(int argc,char **argv){
    int self=argc==2&&!strcmp(argv[1],"--self-test");int fixed=argc==5&&!strcmp(argv[1],"--fixed");
    if(!self&&!fixed&&argc!=1){fprintf(stderr,"usage: %s [--self-test | --fixed Q5 Q6 Q7]\n",argv[0]);return 2;}
    init_variant_attack();
    int orders[6][3]={{0,1,2},{0,2,1},{1,0,2},{1,2,0},{2,0,1},{2,1,0}};
    if(self){int all_ok=1;for(int type=0;type<4;type++)for(int split=0;split<4;split++){int types[3]={type,type,type},ct[N];encrypt_variant_control(ct,types,orders[4],split);Hit h=solve_variant(ct,"IRATE","PIRATE","PIRATES",types,orders[4],split);int ok=!strcmp(h.plain,CONTROL_PLAIN)&&keyword_matches_order("LANGUAGE",h.block_at_col);printf("self_%s_split%d=%s score=%.6f\n",type_name(type),split,ok?"PASS":"FAIL",h.quad_score);if(!ok)all_ok=0;}int mixed[3]={0,1,3},ct[N];encrypt_variant_control(ct,mixed,orders[3],2);Hit h=solve_variant(ct,"IRATE","PIRATE","PIRATES",mixed,orders[3],2);int ok=!strcmp(h.plain,CONTROL_PLAIN)&&keyword_matches_order("LANGUAGE",h.block_at_col);printf("self_mixed=%s score=%.6f\n",ok?"PASS":"FAIL",h.quad_score);return all_ok&&ok?0:1;}

    Hit top[TOP];int top_types[TOP][3],top_order[TOP][3],top_split[TOP];for(int i=0;i<TOP;i++)top[i].quad_score=-1e30f;
    const char *fixed_words[3]={fixed?argv[2]:NULL,fixed?argv[3]:NULL,fixed?argv[4]:NULL};
    if(fixed){if(strlen(fixed_words[0])!=5||strlen(fixed_words[1])!=6||strlen(fixed_words[2])!=7){fprintf(stderr,"fixed keys must have lengths 5,6,7\n");return 2;}
        for(int code=0;code<64;code++){int types[3]={code&3,(code>>2)&3,(code>>4)&3};for(int oi=0;oi<6;oi++)for(int split=0;split<4;split++){Hit h=solve_variant(target_ct,fixed_words[0],fixed_words[1],fixed_words[2],types,orders[oi],split);if(h.quad_score<=top[TOP-1].quad_score)continue;int at=TOP-1;while(at&&h.quad_score>top[at-1].quad_score){top[at]=top[at-1];memcpy(top_types[at],top_types[at-1],sizeof(top_types[at]));memcpy(top_order[at],top_order[at-1],sizeof(top_order[at]));top_split[at]=top_split[at-1];at--;}top[at]=h;memcpy(top_types[at],types,sizeof(types));memcpy(top_order[at],orders[oi],sizeof(orders[oi]));top_split[at]=split;}}
    } else {
        for(int type=0;type<4;type++)for(int oi=0;oi<6;oi++)for(int split=0;split<4;split++){
            Hit model_top[TOP];for(int i=0;i<TOP;i++)model_top[i].quad_score=-1e30f;
            #pragma omp parallel
            {Hit local[TOP];for(int i=0;i<TOP;i++)local[i].quad_score=-1e30f;
             #pragma omp for schedule(dynamic,32)
             for(int i7=0;i7<n7;i7++){char seen6[7][7];int ns6=0;for(int cut7=0;cut7<7;cut7++){char x6[7];remove_at(words7[i7].text,7,cut7,x6);int dup=0;for(int j=0;j<ns6;j++)if(!strcmp(x6,seen6[j]))dup=1;if(dup||!find_word(words6,n6,x6))continue;strcpy(seen6[ns6++],x6);char seen5[6][6];int ns5=0;for(int cut6=0;cut6<6;cut6++){char x5[6];remove_at(x6,6,cut6,x5);dup=0;for(int j=0;j<ns5;j++)if(!strcmp(x5,seen5[j]))dup=1;if(dup||!find_word(words5,n5,x5))continue;strcpy(seen5[ns5++],x5);int types[3]={type,type,type};Hit h=solve_variant(target_ct,x5,x6,words7[i7].text,types,orders[oi],split);insert_hit(local,&h,1);}}}
             #pragma omp critical
             {for(int i=0;i<TOP;i++)insert_hit(model_top,&local[i],1);}}
            int types[3]={type,type,type};Hit h=model_top[0];if(h.quad_score>top[TOP-1].quad_score){int at=TOP-1;while(at&&h.quad_score>top[at-1].quad_score){top[at]=top[at-1];memcpy(top_types[at],top_types[at-1],sizeof(top_types[at]));memcpy(top_order[at],top_order[at-1],sizeof(top_order[at]));top_split[at]=top_split[at-1];at--;}top[at]=h;memcpy(top_types[at],types,sizeof(types));memcpy(top_order[at],orders[oi],sizeof(orders[oi]));top_split[at]=split;}
        }
    }
    for(int i=0;i<TOP;i++)show_variant(&top[i],top_types[i],top_order[i],top_split[i],fixed?"FIXED":"LADDER");
    return 0;
}
