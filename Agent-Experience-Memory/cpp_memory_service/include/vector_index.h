#pragma once

#include <cstddef>
#include <mutex>
#include <vector>

struct SearchResult {
    long long memory_id;
    float score;
};

struct MemoryVector {
    long long memory_id;
    std::vector<float> vector;
};

class VectorIndex {
public:
    void clear();
    void add(long long memory_id, const std::vector<float>& vector);
    std::vector<SearchResult> search(const std::vector<float>& query, int top_k);
    size_t size() const;

private:
    static float cosine_similarity(const std::vector<float>& a, const std::vector<float>& b);

    std::vector<MemoryVector> memories_;
    mutable std::mutex mutex_;
};
