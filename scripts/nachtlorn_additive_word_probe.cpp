// Detect rows whose removal lowers the rank of a one-hot sample matrix.
// These are exactly the rows that can uniquely violate an additive checksum
// with an arbitrary letter-value function at every position.
#include <algorithm>
#include <cstdint>
#include <iostream>
#include <vector>

struct Basis {
    bool present = false;
    std::vector<int> value, coordinates;
};

template<int Q>
int search(const std::vector<std::vector<int>>& rows, int width) {
    const int columns = 26 * width;
    std::vector<Basis> basis(columns);
    std::vector<int> origins;
    std::vector<bool> eligible;
    int rank = 0;
    for (std::size_t index = 0; index < rows.size(); ++index) {
        std::vector<int> value(columns, 0), representation(columns, 0);
        for (int j = 0; j < width; ++j) value[26*j + rows[index][j]] = 1;
        bool independent = false;
        for (int pivot = 0; pivot < columns; ++pivot) {
            const int factor = value[pivot];
            if (!factor) continue;
            Basis& b = basis[pivot];
            if (b.present) {
                for (int j = pivot; j < columns; ++j)
                    value[j] = (value[j] + Q*Q - factor*b.value[j]) % Q;
                for (int j = 0; j < rank; ++j)
                    representation[j] = (representation[j] + factor*b.coordinates[j]) % Q;
            } else {
                int inverse = 1;
                while ((inverse * factor) % Q != 1) ++inverse;
                b.present = true;
                b.value.resize(columns);
                b.coordinates.assign(columns, 0);
                for (int j = pivot; j < columns; ++j) b.value[j] = value[j] * inverse % Q;
                for (int j = 0; j < rank; ++j)
                    b.coordinates[j] = (Q - representation[j]) * inverse % Q;
                b.coordinates[rank] = inverse;
                origins.push_back(int(index));
                eligible.push_back(true);
                ++rank;
                independent = true;
                break;
            }
        }
        if (!independent) {
            for (int j = 0; j < rank; ++j)
                if (representation[j]) eligible[j] = false;
        }
    }
    std::vector<int> coloop_basis_indices;
    for (int j = 0; j < rank; ++j) if (eligible[j]) coloop_basis_indices.push_back(j);
    std::cout << "{\"version\":1,\"mode\":\"onehot-additive\",\"q\":" << Q
              << ",\"width\":" << width << ",\"rows\":" << rows.size()
              << ",\"columns\":" << columns << ",\"rank\":" << rank
              << ",\"full_marginal_rank_limit\":" << 25*width + 1
              << ",\"coloops\":[";
    for (std::size_t j = 0; j < coloop_basis_indices.size(); ++j)
        std::cout << (j ? "," : "") << origins[coloop_basis_indices[j]];
    std::cout << "],\"witnesses\":[";
    // All coloop indices are retained; at most eight potentially large witnesses.
    const std::size_t count = std::min<std::size_t>(8, coloop_basis_indices.size());
    for (std::size_t k = 0; k < count; ++k) {
        const int which = coloop_basis_indices[k];
        std::vector<int> witness(columns, 0);
        for (int p = columns - 1; p >= 0; --p) {
            const Basis& b = basis[p];
            if (!b.present) continue;
            int rhs = b.coordinates[which];
            for (int j = p + 1; j < columns; ++j)
                rhs = (rhs + Q*Q - b.value[j]*witness[j]) % Q;
            witness[p] = rhs;
        }
        for (std::size_t i = 0; i < rows.size(); ++i) {
            int value = 0;
            for (int j = 0; j < width; ++j) value += witness[26*j + rows[i][j]];
            if (value % Q != (int(i) == origins[which] ? 1 : 0)) {
                std::cerr << "internal witness verification failed\n";
                return 3;
            }
        }
        std::cout << (k ? "," : "") << "{\"row\":" << origins[which] << ",\"letter_functions\":[";
        for (int j = 0; j < columns; ++j) std::cout << (j ? "," : "") << witness[j];
        std::cout << "]}";
    }
    std::cout << "]}\n";
    return 0;
}

int main() {
    int n = 0, q = 0, width = 0;
    if (!(std::cin >> n >> q >> width) || n < 2 || n > 16384 ||
        (q != 2 && q != 13) || width < 1 || width > 16) {
        std::cerr << "expected 2..16384 rows, modulus 2/13 and width 1..16\n";
        return 2;
    }
    std::vector<std::vector<int>> rows(n, std::vector<int>(width));
    for (auto& row : rows) {
        for (int& value : row) {
            if (!(std::cin >> value) || value < 0 || value >= 26) {
                std::cerr << "expected an alphabet index 0..25 for every cell\n";
                return 2;
            }
        }
    }
    std::string extra;
    if (std::cin >> extra) {
        std::cerr << "unexpected trailing input\n";
        return 2;
    }
    if (q == 2) return search<2>(rows, width);
    return search<13>(rows, width);
}
