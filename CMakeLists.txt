cmake_minimum_required(VERSION 3.16)

project(MiniNeutron)

find_package(Geant4 REQUIRED ui_all vis_all)

include(${Geant4_USE_FILE})

include_directories(${PROJECT_SOURCE_DIR}/include)

file(GLOB sources ${PROJECT_SOURCE_DIR}/src/*.cc)
file(GLOB headers ${PROJECT_SOURCE_DIR}/include/*.hh)

add_executable(minineutron
    miniNeutron.cc
    ${sources}
    ${headers}
)

target_link_libraries(minineutron ${Geant4_LIBRARIES})

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)