with open("test_pk9_amsco12.c") as f:
    s = f.read()

s = s.replace("""        #pragma omp parallel for schedule(dynamic, 100)
        for (int w_idx = 0; w_idx < n_words; w_idx++) {
            for (int pat = 1; pat <= 2; pat++) {
                int pt[N];
                decode_amsco(z, pat, words[w_idx].order, pt);
                float sc = score_quads(pt);

                if (sc > local_best) {
                    #pragma omp critical
                    {
                        if (sc > global_best_sc) {
                            global_best_sc = sc;
                            strcpy(global_best_word, words[w_idx].word);
                            global_best_cand = t;
                            global_best_pat = pat;
                            for (int k = 0; k < N; k++) global_best_pt[k] = pt[k] + 'A';
                            global_best_pt[N] = 0;

                            printf(">>> NEW BEST: %.4f | Cand #%d (Mode %d) | Pat %d | Word: %s <<<\\n",
                                   sc, t, c->mode, pat, words[w_idx].word);
                            printf("  PT: %.100s...\\n\\n", global_best_pt);
                        }
                    }
                }
            }
        }""",
"""        #pragma omp parallel
        {
            float local_best = -999.0f;
            char local_w[16] = "";
            int local_pat = 1;
            char local_pt[N+1];

            #pragma omp for schedule(dynamic, 100)
            for (int w_idx = 0; w_idx < n_words; w_idx++) {
                for (int pat = 1; pat <= 2; pat++) {
                    int pt[N];
                    decode_amsco(z, pat, words[w_idx].order, pt);
                    float sc = score_quads(pt);

                    if (sc > local_best) {
                        local_best = sc;
                        strcpy(local_w, words[w_idx].word);
                        local_pat = pat;
                        for (int k = 0; k < N; k++) local_pt[k] = pt[k] + 'A';
                        local_pt[N] = 0;
                    }
                }
            }

            #pragma omp critical
            {
                if (local_best > global_best_sc) {
                    global_best_sc = local_best;
                    strcpy(global_best_word, local_w);
                    global_best_cand = t;
                    global_best_pat = local_pat;
                    strcpy(global_best_pt, local_pt);

                    printf(">>> NEW BEST: %.4f | Cand #%d (Mode %d) | Pat %d | Word: %s <<<\\n",
                           local_best, t, c->mode, local_pat, local_w);
                    printf("  PT: %.100s...\\n\\n", local_pt);
                }
            }
        }""")

with open("test_pk9_amsco12.c", "w") as f:
    f.write(s)
