cmake_minimum_required(VERSION 3.20)
project(blockcode_eval_cpp LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

add_executable(blockcode_eval evaluator_skeleton.cpp)
