// R26: exhaustive integer upper-score scan; no plaintext or language model inference.
#include <array>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <limits>
#include <string>
#include <vector>

static bool read_letters(const char* path, std::vector<unsigned char>& values) {
    std::ifstream input(path, std::ios::binary);
    if (!input) return false;
    char c;
    while (input.get(c)) {
        if (c < 'A' || c > 'Z') return false;
        values.push_back(static_cast<unsigned char>(c - 'A'));
    }
    return !input.bad() && !values.empty();
}

int main(int argc, char** argv) {
    if (argc != 3 && argc != 4) return 2;
    const bool all = argc == 4 && std::string(argv[3]) == "--all";
    if (argc == 4 && !all) return 2;
    std::vector<unsigned char> book, cipher;
    if (!read_letters(argv[1], book) || !read_letters(argv[2], cipher)) return 2;
    std::size_t full;
    std::array<int, 26> weights{};
    if (!(std::cin >> full) || full < cipher.size() || full > book.size()) return 2;
    for (auto& weight : weights) if (!(std::cin >> weight) || weight < -100000 || weight > 100000) return 2;
    std::array<std::array<int, 26>, 26> table{};
    for (int c = 0; c < 26; ++c)
        for (int k = 0; k < 26; ++k)
            table[c][k] = weights[(c - k + 26) % 26];
    const std::size_t windows = book.size() - full + 1;
    std::int64_t best = std::numeric_limits<std::int64_t>::min();
    std::size_t first = 0, ties = 0;
    for (std::size_t start = 0; start < windows; ++start) {
        std::int64_t score = 0;
        for (std::size_t j = 0; j < cipher.size(); ++j)
            score += table[cipher[j]][book[start + j]];
        if (all) std::cout << score << '\n';
        if (score > best) { best = score; first = start; ties = 1; }
        else if (score == best) ++ties;
    }
    if (!all) std::cout << "{\"windows\":" << windows << ",\"maximum_integer_upper_sum\":" << best
                        << ",\"first_maximum_offset\":" << first << ",\"maximizing_offsets\":" << ties << "}\n";
    return 0;
}
