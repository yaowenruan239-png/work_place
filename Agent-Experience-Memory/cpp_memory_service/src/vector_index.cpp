#include "vector_index.h"

#include <algorithm>
#include <cmath>
#include <stdexcept>

void VectorIndex::clear() {
    std::lock_guard<std::mutex> lock(mutex_);
    memories_.clear();
}

void VectorIndex::add(long long memory_id, const std::vector<float>& vector) {
    if (vector.empty()) {
        throw std::invalid_argument("vector must not be empty");
    }

    std::lock_guard<std::mutex> lock(mutex_);
    memories_.push_back(MemoryVector{memory_id, vector});
}

std::vector<SearchResult> VectorIndex::search(const std::vector<float>& query, int top_k) {
    if (query.empty()) {
        throw std::invalid_argument("query vector must not be empty");
    }

    std::vector<SearchResult> results;
    {
        std::lock_guard<std::mutex> lock(mutex_);
        results.reserve(memories_.size());
        for (const auto& memory : memories_) {
            if (memory.vector.size() != query.size()) {
                continue;
            }
            results.push_back(SearchResult{
                memory.memory_id,
                cosine_similarity(query, memory.vector),
            });
        }
    }

    std::sort(results.begin(), results.end(), [](const SearchResult& lhs, const SearchResult& rhs) {
        return lhs.score > rhs.score;
    });

    if (top_k > 0 && static_cast<size_t>(top_k) < results.size()) {
        results.resize(static_cast<size_t>(top_k));
    }

    return results;
}

size_t VectorIndex::size() const {
    std::lock_guard<std::mutex> lock(mutex_);
    return memories_.size();
}

float VectorIndex::cosine_similarity(const std::vector<float>& a, const std::vector<float>& b) {
    if (a.empty() || b.empty()) {
        throw std::invalid_argument("vectors must not be empty");
    }
    if (a.size() != b.size()) {
        throw std::invalid_argument("vectors must have the same dimension");
    }

    double dot = 0.0;
    double norm_a = 0.0;
    double norm_b = 0.0;

    for (size_t i = 0; i < a.size(); ++i) {
        dot += static_cast<double>(a[i]) * static_cast<double>(b[i]);
        norm_a += static_cast<double>(a[i]) * static_cast<double>(a[i]);
        norm_b += static_cast<double>(b[i]) * static_cast<double>(b[i]);
    }

    if (norm_a == 0.0 || norm_b == 0.0) {
        return 0.0F;
    }

    return static_cast<float>(dot / (std::sqrt(norm_a) * std::sqrt(norm_b)));
}
