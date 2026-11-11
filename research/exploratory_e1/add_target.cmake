# SPDX-License-Identifier: Apache-2.0
# Explicit external project hook; ordinary native builds are unchanged.
add_executable(e1_native "${CMAKE_CURRENT_LIST_DIR}/native_driver.cpp")
target_link_libraries(e1_native PRIVATE bmssp_foundation)
