import re

with open("test_pk9_craft_sweep.c") as f:
    code = f.read()

# Replace ANCHORS list with just METALWORKING and GOLDSMITHING
code = re.sub(r'static const char \*ANCHORS\[\] = \{[^}]+\};', 
              'static const char *ANCHORS[] = {"METALWORKING", "GOLDSMITHING"};', code)
code = re.sub(r'static const int NUM_ANCHORS = [0-9]+;', 'static const int NUM_ANCHORS = 2;', code)

with open("test_pk9_craft_sweep.c", "w") as f:
    f.write(code)

