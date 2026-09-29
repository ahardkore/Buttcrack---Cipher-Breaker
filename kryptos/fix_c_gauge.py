with open("test_crib_pk8_parallel.c") as f:
    code = f.read()

# Replace the c_gauge loop with c_gauge = 0
old_loop = """            for (int c_gauge = 0; c_gauge < 26; c_gauge++) {
                int A[32][16] = {0};"""

new_loop = """            {
                int c_gauge = 0;
                int A[32][16] = {0};"""

assert old_loop in code
code = code.replace(old_loop, new_loop)

# Also fix the closing brace
old_close = """                    if (avg_sc > -5.5f) {
                        #pragma omp critical
                        {
                            printf("\\nHIT! Score = %.2f | Crib: %s at pos %d (c=%d)\\n",
                                avg_sc, crib, t0_pos, c_gauge);
                            printf("PT: %s\\n", pt);
                        }
                    }
                }
            }
        }
    }"""

new_close = """                    if (avg_sc > -5.5f) {
                        #pragma omp critical
                        {
                            printf("\\nHIT! Score = %.2f | Crib: %s at pos %d\\n",
                                avg_sc, crib, t0_pos);
                            printf("PT: %s\\n", pt);
                        }
                    }
                }
            }
        }
    }"""

assert old_close in code
code = code.replace(old_close, new_close)

with open("test_crib_pk8_fast.c", "w") as f:
    f.write(code)

print("Created test_crib_pk8_fast.c successfully!")
