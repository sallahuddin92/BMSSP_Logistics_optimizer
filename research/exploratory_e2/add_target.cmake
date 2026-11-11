# SPDX-License-Identifier: Apache-2.0
add_executable(e2_worker "${CMAKE_CURRENT_LIST_DIR}/worker.cpp")
add_executable(e2_correctness "${CMAKE_CURRENT_LIST_DIR}/correctness.cpp")
foreach(target e2_worker e2_correctness)
  target_link_libraries(${target} PRIVATE bmssp_foundation)
  set_target_properties(${target} PROPERTIES CXX_EXTENSIONS OFF)
endforeach()
