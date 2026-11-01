// Exhaust all projective linear functionals on five columns over F_2/F_5/F_13.
// Only reads integer samples from stdin; no recovered content is executed.
#include <algorithm>
#include <array>
#include <cstdint>
#include <iomanip>
#include <iostream>
#include <vector>

using Row = std::array<int, 5>;
struct Candidate {
    Row coefficients{};
    std::array<int, 13> histogram{};
    std::int64_t squares = 0;
};

bool better(const Candidate& a, const Candidate& b) {
    if (a.squares != b.squares) return a.squares > b.squares;
    return a.coefficients < b.coefficients;
}

template<int Q>
int search(const std::vector<Row>& rows) {
    std::vector<Candidate> top;
    std::uint64_t directions = 0;
    for (int pivot = 0; pivot < 5; ++pivot) {
        int total = 1;
        for (int j = pivot + 1; j < 5; ++j) total *= Q;
        for (int code = 0; code < total; ++code) {
            Candidate c;
            c.coefficients[pivot] = 1;
            int digits = code;
            for (int j = 4; j > pivot; --j) {
                c.coefficients[j] = digits % Q;
                digits /= Q;
            }
            const Row& a = c.coefficients;
            for (const Row& x : rows) {
                const int residue = (a[0]*x[0] + a[1]*x[1] + a[2]*x[2] +
                                     a[3]*x[3] + a[4]*x[4]) % Q;
                ++c.histogram[residue];
            }
            for (int j = 0; j < Q; ++j) {
                c.squares += std::int64_t(c.histogram[j]) * c.histogram[j];
            }
            ++directions;
            if (top.size() < 8 || better(c, top.back())) {
                top.push_back(c);
                std::sort(top.begin(), top.end(), better);
                if (top.size() > 8) top.pop_back();
            }
        }
    }
    std::cout << std::setprecision(17)
              << "{\"version\":1,\"columns\":5,\"q\":" << Q
              << ",\"rows\":" << rows.size() << ",\"directions\":" << directions
              << ",\"top\":[";
    bool first = true;
    for (const Candidate& c : top) {
        if (!first) std::cout << ',';
        first = false;
        std::cout << "{\"coefficients\":[";
        for (int j = 0; j < 5; ++j) std::cout << (j ? "," : "") << c.coefficients[j];
        std::cout << "],\"histogram\":[";
        int dominant = 0;
        for (int j = 0; j < Q; ++j) {
            std::cout << (j ? "," : "") << c.histogram[j];
            if (c.histogram[j] > c.histogram[dominant]) dominant = j;
        }
        const double statistic = double(Q) * double(c.squares) / double(rows.size()) - double(rows.size());
        std::cout << "],\"sum_squares\":" << c.squares
                  << ",\"statistic\":" << statistic
                  << ",\"dominant_residue\":" << dominant
                  << ",\"dominant_count\":" << c.histogram[dominant]
                  << ",\"unique_exception_indices\":[";
        if (c.histogram[dominant] == int(rows.size()) - 1 &&
            std::count(c.histogram.begin(), c.histogram.begin() + Q, c.histogram[dominant]) == 1) {
            bool first_exception = true;
            for (std::size_t i = 0; i < rows.size(); ++i) {
                const Row& x = rows[i];
                const Row& a = c.coefficients;
                int residue = 0;
                for (int j = 0; j < 5; ++j) residue += a[j] * x[j];
                if (residue % Q != dominant) {
                    if (!first_exception) std::cout << ',';
                    first_exception = false;
                    std::cout << i;
                }
            }
        }
        std::cout << "]}";
    }
    std::cout << "]}\n";
    return 0;
}

int main() {
    int n = 0, q = 0;
    if (!(std::cin >> n >> q) || n < 2 || n > 16384 || (q != 2 && q != 5 && q != 13)) {
        std::cerr << "expected 2..16384 rows and modulus 2, 5 or 13\n";
        return 2;
    }
    std::vector<Row> rows(n);
    for (Row& row : rows) {
        for (int& value : row) {
            if (!(std::cin >> value) || value < 0 || value >= q) {
                std::cerr << "expected exactly five canonical field elements per row\n";
                return 2;
            }
        }
    }
    std::string extra;
    if (std::cin >> extra) {
        std::cerr << "unexpected trailing input\n";
        return 2;
    }
    if (q == 2) return search<2>(rows);
    if (q == 5) return search<5>(rows);
    return search<13>(rows);
}
