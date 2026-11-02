// R29: exact integer upper-score scans of the other two modular signs.
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
    std::array<std::array<std::array<int, 26>, 26>, 2> table{};
    for (int c = 0; c < 26; ++c)
        for (int k = 0; k < 26; ++k) {
            table[0][c][k] = weights[(k - c + 26) % 26];
            table[1][c][k] = weights[(c + k) % 26];
        }
    const std::size_t windows = book.size() - full + 1;
    std::array<std::int64_t, 2> best{std::numeric_limits<std::int64_t>::min(), std::numeric_limits<std::int64_t>::min()};
    std::array<std::size_t, 2> first{}, ties{};
    for (std::size_t start = 0; start < windows; ++start) {
        std::int64_t minus = 0, plus = 0;
        for (std::size_t j = 0; j < cipher.size(); ++j) {
            minus += table[0][cipher[j]][book[start + j]];
            plus += table[1][cipher[j]][book[start + j]];
        }
        if (all) std::cout << minus << ' ' << plus << '\n';
        const std::array<std::int64_t, 2> values{minus, plus};
        for (int mode = 0; mode < 2; ++mode) {
            if (values[mode] > best[mode]) { best[mode] = values[mode]; first[mode] = start; ties[mode] = 1; }
            else if (values[mode] == best[mode]) ++ties[mode];
        }
    }
    if (!all) {
        std::cout << "{\"windows\":" << windows << ",\"models\":[";
        for (int mode = 0; mode < 2; ++mode) {
            if (mode) std::cout << ',';
            std::cout << "{\"operation\":\"" << (mode == 0 ? "K-C" : "C+K")
                      << "\",\"maximum_integer_upper_sum\":" << best[mode]
                      << ",\"first_maximum_offset\":" << first[mode] << ",\"maximizing_offsets\":" << ties[mode] << '}';
        }
        std::cout << "]}\n";
    }
    return 0;
}
