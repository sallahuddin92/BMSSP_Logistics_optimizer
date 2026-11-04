// SPDX-License-Identifier: Apache-2.0
#pragma once
#include "bmssp/symbolic_label.hpp"
#include <list>
#include <map>
#include <unordered_map>
namespace bmssp {
struct FrontierCounters {
    std::size_t initializations = 0, discards = 0, inserts = 0, pulls = 0, batches = 0, splits = 0,
                selection_work = 0, pulled_keys = 0, peak_keys = 0;
};
struct FrontierEntry {
    VertexIndex key;
    SymbolicLabel value;
};
struct FrontierPull {
    SymbolicLabel bound;
    std::vector<FrontierEntry> entries;
};
// Lemma 3.3 strategy: two ordered block sequences, unsorted items within blocks.
class BoundedFrontier {
  public:
    BoundedFrontier(std::size_t block_size, SymbolicLabel bound, FrontierCounters &counters,
                    bool validate_operations = false);
    BoundedFrontier(const BoundedFrontier &) = delete;
    BoundedFrontier &operator=(const BoundedFrontier &) = delete;
    void initialize(std::size_t block_size, SymbolicLabel bound);
    // Internal Delete operation from Lemma 3.3, used to retire settled stale records.
    void discard(VertexIndex key);
    void insert(VertexIndex key, const SymbolicLabel &value);
    void batch_prepend(std::vector<FrontierEntry> batch);
    [[nodiscard]] FrontierPull pull();
    [[nodiscard]] bool empty() const noexcept {
        return locations_.empty();
    }
    [[nodiscard]] std::size_t size() const noexcept {
        return locations_.size();
    }
    void validate() const;

  private:
    struct Block {
        std::list<FrontierEntry> entries;
        SymbolicLabel fence;
    };
    using Blocks = std::list<Block>;
    struct Location {
        bool prepend;
        Blocks::iterator block;
        std::list<FrontierEntry>::iterator entry;
    };
    std::size_t m_;
    SymbolicLabel bound_;
    FrontierCounters &counters_;
    bool checks_;
    Blocks d0_, d1_;
    std::map<SymbolicLabel, Blocks::iterator, LabelLess> fences_;
    std::unordered_map<VertexIndex, Location> locations_;
    void erase(VertexIndex key);
    void fill(Blocks::iterator block, bool prepend, std::vector<FrontierEntry> entries);
    void split(Blocks::iterator block);
    void prepend_partition(std::vector<FrontierEntry> entries, std::size_t limit);
    [[nodiscard]] SymbolicLabel minimum() const;
    void select(std::vector<FrontierEntry> &entries, std::size_t nth);
};
} // namespace bmssp
