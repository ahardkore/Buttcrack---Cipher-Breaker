#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

// Let's verify the 4 classic Fleissner conventions:
// Convention 1: PT -> write through grille (4 turns) -> read grid by rows -> CT
// Decrypt: CT -> fill grid by rows -> read through grille (4 turns) -> PT
// (This is what polish_fleissner implemented)

// Convention 2: PT -> write grid by rows -> read through grille (4 turns) -> CT
// Decrypt: CT -> write through grille (4 turns) -> read grid by rows -> PT

// Convention 3: Counter-clockwise turns

// Convention 4: Read grid by columns instead of rows

