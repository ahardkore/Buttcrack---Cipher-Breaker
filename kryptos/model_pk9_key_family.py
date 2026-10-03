#!/usr/bin/env python3
"""Rank PK9 wheel triples by key-family transformations seen in PK8.

PK8's METE -> METER -> METIER is not just edit distance: each successor keeps
an ordered subsequence and adds letters while preserving the stem.  This tool
models that rule plus the less literal families worth testing: reversed stems,
cyclic stems, repeated letters, and Kryptos-index affine relationships.  It
only ranks candidates; the PK9 scorer remains the authority.
"""
from __future__ import annotations
import argparse
from pathlib import Path
from collections import Counter
A = "KRYPTOSABCDEFGHIJLMNQUVWXZ"

def words(p): return sorted({x.strip().upper() for x in Path(p).read_text().splitlines() if x.strip().isalpha()})
def subseq(a,b):
 i=0
 for c in b:
  i += i < len(a) and c == a[i]
 return i == len(a)
def lcs(a,b):
 r=[0]*(len(b)+1)
 for x in a:
  old=0
  for j,y in enumerate(b,1):
   z=r[j]; r[j]=old+1 if x==y else max(r[j],r[j-1]); old=z
 return r[-1]
def affine(a,b):
 # Compare aligned Kryptos-index differences for common-length words.
 if len(a)!=len(b): return False
 d=[(A.index(y)-A.index(x))%26 for x,y in zip(a,b)]
 return len(set(d))==1
def score(a,b):
 s=0
 if subseq(a,b): s+=5
 if subseq(b,a): s+=5
 s += 3*lcs(a,b)/max(len(a),len(b))
 if a[::-1] in b or b[::-1] in a: s+=2
 if Counter(a) <= Counter(b) or Counter(b) <= Counter(a): s+=2
 if affine(a,b): s+=3
 # reward shared ordered prefix/suffix without requiring literal identity
 for n in range(2,min(len(a),len(b))+1):
  if a[:n]==b[:n]: s+=.15
  if a[-n:]==b[-n:]: s+=.15
 return s

def main():
 ap=argparse.ArgumentParser(); ap.add_argument('v5'); ap.add_argument('v6'); ap.add_argument('v7'); ap.add_argument('--out',required=True); ap.add_argument('--limit',type=int,default=5000); args=ap.parse_args()
 w5,w6,w7=map(words,(args.v5,args.v6,args.v7)); rows=[]
 for a in w5:
  for b in w6:
   x=score(a,b)
   if x<5: continue
   for c in w7:
    y=score(b,c)
    if y>=5: rows.append((x+y,a,b,c))
 rows.sort(reverse=True)
 Path(args.out).write_text(''.join(f'{x:.3f} {a} {b} {c}\n' for x,a,b,c in rows[:args.limit]))
 print(f'candidate triples: {len(rows)}; wrote {min(len(rows),args.limit)} to {args.out}')
 print('\n'.join(f'{x:.3f} {a} {b} {c}' for x,a,b,c in rows[:10]))
if __name__=='__main__': main()
