cmake_minimum_required(VERSION 3.24)
project(blockcode_cuda_eval LANGUAGES CXX CUDA)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CUDA_STANDARD 17)
set(CMAKE_CUDA_STANDARD_REQUIRED ON)

# Change this if your GPU needs a specific architecture.
# Example: -DCMAKE_CUDA_ARCHITECTURES=86
if(NOT DEFINED CMAKE_CUDA_ARCHITECTURES)
  set(CMAKE_CUDA_ARCHITECTURES native)
endif()

add_executable(blockcode_cuda_eval blockcode_cuda_eval.cu)

target_compile_options(blockcode_cuda_eval PRIVATE
  $<$<COMPILE_LANGUAGE:CXX>:-O3 -Wall -Wextra>
  $<$<COMPILE_LANGUAGE:CUDA>:-O3>
)
