// SPDX-License-Identifier: Apache-2.0
#pragma once
#include "bmssp/reference_dijkstra.hpp"
#include <functional>
#include <iostream>
#include <stdexcept>
#include <string>
#include <utility>

#define CHECK(...)                                                                                 \
    do {                                                                                           \
        if (!(__VA_ARGS__))                                                                        \
            throw std::runtime_error(std::string(__FILE__) + ":" + std::to_string(__LINE__) +      \
                                     " check failed: " #__VA_ARGS__);                              \
    } while (false)
namespace test {
inline int failures = 0;
inline int cases = 0;
template <class Exception, class Fn> void throws(Fn &&fn) {
    try {
        fn();
    } catch (const Exception &) {
        return;
    }
    throw std::runtime_error("expected exception was not thrown");
}
template <class Fn> void run(const char *name, Fn &&fn) {
    ++cases;
    try {
        fn();
        std::cout << "PASS " << name << '\n';
    } catch (const std::exception &e) {
        ++failures;
        std::cerr << "FAIL " << name << ": " << e.what() << '\n';
    }
}
inline int finish() {
    std::cout << "cases=" << cases << " passed=" << cases - failures << " failed=" << failures
              << '\n';
    return failures == 0 ? 0 : 1;
}
inline bmssp::Graph fixture() {
    return {{0, 1, 2, 3, 4},
            {{10, 0, 1, 9}, {11, 0, 2, 2}, {12, 2, 1, 1}, {13, 1, 3, 4}, {14, 2, 3, 20}}};
}
} // namespace test
