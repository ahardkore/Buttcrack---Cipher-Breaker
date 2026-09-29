with open("test_artisan_pairs_on_clocks.c") as f:
    code = f.read()

# Replace the inner loop logic to track best score per thread and globally
old_inner = """        #pragma omp parallel for schedule(dynamic)
        for (int i = 0; i < n_words; i++) {
            int mid[N], pt[N];
            col_decrypt(z, words[i].order, mid);

            for (int j = 0; j < n_words; j++) {
                col_decrypt(mid, words[j].order, pt);
                float sc = score_quads(pt);

                if (sc > local_best_sc) {
                    #pragma omp critical
                    {
                        if (sc > global_best_sc) {
                            global_best_sc = sc;
                            strcpy(global_w1, words[i].word);
                            strcpy(global_w2, words[j].word);
                            global_cand_idx = idx;
                            memcpy(global_best_pt, pt, sizeof(pt));

                            char pt_str[N+1];
                            for (int k = 0; k < N; k++) pt_str[k] = pt[k] + 'A';
                            pt_str[N] = 0;

                            printf(">>> NEW BEST: %.4f | Mode %d | Cand #%d | Pair: %s o %s <<<\\n",
                                   sc, c->mode, idx, words[i].word, words[j].word);
                            printf("  PT: %.100s...\\n\\n", pt_str);
                        }
                    }
                }
            }
        }"""

new_inner = """        #pragma omp parallel
        {
            float local_best = -999.0f;
            char local_w1[16], local_w2[16];
            int local_pt[N];

            #pragma omp for schedule(dynamic)
            for (int i = 0; i < n_words; i++) {
                int mid[N], pt[N];
                col_decrypt(z, words[i].order, mid);

                for (int j = 0; j < n_words; j++) {
                    col_decrypt(mid, words[j].order, pt);
                    float sc = score_quads(pt);

                    if (sc > local_best) {
                        local_best = sc;
                        strcpy(local_w1, words[i].word);
                        strcpy(local_w2, words[j].word);
                        memcpy(local_pt, pt, sizeof(pt));
                    }
                }
            }

            #pragma omp critical
            {
                if (local_best > global_best_sc) {
                    global_best_sc = local_best;
                    strcpy(global_w1, local_w1);
                    strcpy(global_w2, local_w2);
                    global_cand_idx = idx;
                    memcpy(global_best_pt, local_pt, sizeof(local_pt));

                    char pt_str[N+1];
                    for (int k = 0; k < N; k++) pt_str[k] = local_pt[k] + 'A';
                    pt_str[N] = 0;

                    printf(">>> NEW BEST: %.4f | Mode %d | Cand #%d | Pair: %s o %s <<<\\n",
                           local_best, c->mode, idx, local_w1, local_w2);
                    printf("  PT: %.100s...\\n\\n", pt_str);
                }
            }
        }"""

code = code.replace(old_inner, new_inner)
with open("test_artisan_pairs_on_clocks.c", "w") as f:
    f.write(code)
