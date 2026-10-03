#!/usr/bin/env python3
"""Expand ranked Q5/Q6/Q7 families with related width-8 T8 keys."""
from pathlib import Path
import argparse
from collections import Counter

A = "KRYPTOSABCDEFGHIJLMNQUVWXZ"

def sub(a,b):
 i=0
 for c in b:
  if i<len(a) and c==a[i]: i+=1
 return i==len(a)
def lcs(a,b):
 r=[0]*(len(b)+1)
 for x in a:
  old=0
  for j,y in enumerate(b,1):
   z=r[j]; r[j]=old+1 if x==y else max(r[j],r[j-1]); old=z
 return r[-1]
def affine(a,b):
 if len(a) != len(b): return False
 try: d=[(A.index(y)-A.index(x))%26 for x,y in zip(a,b)]
 except ValueError: return False
 return len(set(d)) == 1

def rel(a,b):
 # Include transformations that preserve a family without preserving order.
 if sub(a,b) or sub(b,a) or lcs(a,b)>=max(3,min(len(a),len(b))-2): return True
 if a[::-1] in b or b[::-1] in a: return True
 if len(a)==len(b) and any(a[i:]+a[:i] == b for i in range(1,len(a))): return True
 if len(a)==len(b) and Counter(a)==Counter(b): return True
 return affine(a,b)
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('families'); ap.add_argument('v8'); ap.add_argument('--out',required=True); args=ap.parse_args()
 v8=sorted(set(x.strip().upper() for x in Path(args.v8).read_text().splitlines()
        if len(x.strip())==8 and len(set(x.strip().upper()))==8))
 out=[]
 for line in Path(args.families).read_text().splitlines():
  p=line.split();
  if len(p)==4: _,a,b,c=p
  elif len(p)==3: a,b,c=p
  else: continue
  for d in v8:
   if rel(c,d): out.append((a,b,c,d))
 Path(args.out).write_text(''.join('%s %s %s %s\n'%x for x in out))
 print('four-key candidates:',len(out))
if __name__=='__main__': main()
