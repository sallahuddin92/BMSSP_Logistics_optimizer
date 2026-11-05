// SPDX-License-Identifier: Apache-2.0
#pragma once
#include "bmssp/symbolic_label.hpp"
#include <list>
#include <map>
#include <memory_resource>
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
        std::pmr::list<FrontierEntry> entries;
        SymbolicLabel fence;
        explicit Block(std::pmr::memory_resource *memory, SymbolicLabel boundary = {})
            : entries(memory), fence(std::move(boundary)) {}
    };
    using Blocks = std::pmr::list<Block>;
    struct Location {
        bool prepend;
        Blocks::iterator block;
        std::pmr::list<FrontierEntry>::iterator entry;
    };
    std::size_t m_;
    SymbolicLabel bound_;
    FrontierCounters &counters_;
    bool checks_;
    // A frontier is confined to one recursion frame/thread. Container nodes are
    // recycled locally, preserving list iterators, insertion order and map fences.
    // Declared first so the resource outlives every container using its storage.
    std::pmr::unsynchronized_pool_resource memory_{std::pmr::new_delete_resource()};
    Blocks d0_{&memory_}, d1_{&memory_};
    std::pmr::map<SymbolicLabel, Blocks::iterator, LabelLess> fences_{LabelLess{}, &memory_};
    std::pmr::unordered_map<VertexIndex, Location> locations_{&memory_};
    void erase(VertexIndex key);
    void fill(Blocks::iterator block, bool prepend, std::vector<FrontierEntry> entries);
    void split(Blocks::iterator block);
    void prepend_partition(std::vector<FrontierEntry> entries, std::size_t limit);
    [[nodiscard]] SymbolicLabel minimum() const;
    void select(std::vector<FrontierEntry> &entries, std::size_t nth);
};
} // namespace bmssp
