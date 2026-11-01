// Synthetic controls only. Compile against the separately pinned, reviewed
// gavinandresen/IBLT_Cplusplus sources; no puzzle input is read.
#include <iostream>
#include <sstream>
#include <string>
#include <vector>
#include "iblt.h"
#include "murmurhash3.h"

int main() {
    const std::vector<uint64_t> keys = {0, 1, 0x0123456789abcdefULL, UINT64_MAX};
    for (uint64_t key : keys) {
        std::vector<unsigned char> bytes(8);
        for (unsigned i = 0; i < 8; ++i) bytes[i] = (key >> (8 * i)) & 255;
        for (uint32_t seed : {0U, 1U, 2U, 3U, 11U})
            std::cout << "HASH " << key << " " << seed << " " << MurmurHash3(seed, bytes) << "\n";
    }
    IBLT table(16, 0); // Reference constructor produces 24 cells.
    for (uint64_t key : std::vector<uint64_t>{0, 1, 2, UINT64_MAX}) table.insert(key, {});
    for (uint64_t key : std::vector<uint64_t>{7, 0x0123456789abcdefULL}) table.erase(key, {});
    table.insert(11, {});
    table.erase(11, {}); // Exact cancellation control.
    std::istringstream dump(table.DumpTable());
    std::string line;
    std::getline(dump, line);
    size_t index = 0;
    while (std::getline(dump, line)) std::cout << "CELL " << index++ << " " << line << "\n";
    std::set<std::pair<uint64_t, std::vector<uint8_t>>> positive, negative;
    const bool complete = table.listEntries(positive, negative);
    std::cout << "COMPLETE " << complete << "\n";
    for (const auto& item : positive) std::cout << "ITEM 1 " << item.first << "\n";
    for (const auto& item : negative) std::cout << "ITEM -1 " << item.first << "\n";
    return complete ? 0 : 1;
}
