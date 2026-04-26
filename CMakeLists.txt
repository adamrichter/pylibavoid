cmake_minimum_required(VERSION 3.18)
project(libavoid_py LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

set(ADAPTAGRAMS_DIR ${CMAKE_CURRENT_SOURCE_DIR}/vendor/adaptagrams)
set(LIBAVOID_DIR    ${ADAPTAGRAMS_DIR}/cola/libavoid)

if(NOT EXISTS ${LIBAVOID_DIR}/router.cpp)
    message(FATAL_ERROR
        "libavoid sources not found under ${LIBAVOID_DIR}. "
        "If you are building from a git clone, run "
        "`git submodule update --init --recursive`. If you are building "
        "from an sdist, this is a bug — please open an issue.")
endif()

# Resolve the libavoid commit we are building against. Prefer a live
# git query inside the submodule; fall back to LIBAVOID_COMMIT.txt,
# which is shipped in the sdist for installs that have no .git.
set(LIBAVOID_COMMIT_HASH "")
find_package(Git QUIET)
if(Git_FOUND)
    execute_process(
        COMMAND ${GIT_EXECUTABLE} -C ${ADAPTAGRAMS_DIR} rev-parse HEAD
        OUTPUT_VARIABLE _git_hash
        OUTPUT_STRIP_TRAILING_WHITESPACE
        RESULT_VARIABLE _git_result
        ERROR_QUIET
    )
    if(_git_result EQUAL 0)
        set(LIBAVOID_COMMIT_HASH "${_git_hash}")
    endif()
endif()
if(NOT LIBAVOID_COMMIT_HASH AND EXISTS ${CMAKE_CURRENT_SOURCE_DIR}/LIBAVOID_COMMIT.txt)
    file(READ ${CMAKE_CURRENT_SOURCE_DIR}/LIBAVOID_COMMIT.txt LIBAVOID_COMMIT_HASH)
    string(STRIP "${LIBAVOID_COMMIT_HASH}" LIBAVOID_COMMIT_HASH)
endif()
if(NOT LIBAVOID_COMMIT_HASH)
    message(FATAL_ERROR
        "Could not determine the libavoid commit hash: neither "
        "`git -C ${ADAPTAGRAMS_DIR} rev-parse HEAD` nor LIBAVOID_COMMIT.txt "
        "produced a value.")
endif()
message(STATUS "Building against libavoid commit: ${LIBAVOID_COMMIT_HASH}")

# Enumerate the 23 .cpp files that compose libavoid. Kept explicit (not
# globbed) so a commit bump that adds or removes sources is a visible
# diff to this file — see docs/research/build-notes.md §"Sources to compile".
add_library(libavoid_static STATIC
    ${LIBAVOID_DIR}/actioninfo.cpp
    ${LIBAVOID_DIR}/connectionpin.cpp
    ${LIBAVOID_DIR}/connector.cpp
    ${LIBAVOID_DIR}/connend.cpp
    ${LIBAVOID_DIR}/geometry.cpp
    ${LIBAVOID_DIR}/geomtypes.cpp
    ${LIBAVOID_DIR}/graph.cpp
    ${LIBAVOID_DIR}/hyperedge.cpp
    ${LIBAVOID_DIR}/hyperedgeimprover.cpp
    ${LIBAVOID_DIR}/hyperedgetree.cpp
    ${LIBAVOID_DIR}/junction.cpp
    ${LIBAVOID_DIR}/makepath.cpp
    ${LIBAVOID_DIR}/mtst.cpp
    ${LIBAVOID_DIR}/obstacle.cpp
    ${LIBAVOID_DIR}/orthogonal.cpp
    ${LIBAVOID_DIR}/router.cpp
    ${LIBAVOID_DIR}/scanline.cpp
    ${LIBAVOID_DIR}/shape.cpp
    ${LIBAVOID_DIR}/timer.cpp
    ${LIBAVOID_DIR}/vertices.cpp
    ${LIBAVOID_DIR}/viscluster.cpp
    ${LIBAVOID_DIR}/visibility.cpp
    ${LIBAVOID_DIR}/vpsc.cpp
)

target_include_directories(libavoid_static PUBLIC ${ADAPTAGRAMS_DIR}/cola)

set_target_properties(libavoid_static PROPERTIES
    POSITION_INDEPENDENT_CODE ON
)

if(MSVC)
    # Flatten AVOID_EXPORT to empty when statically linking, and keep
    # assertions.h out of <afx.h> — see build-notes.md.
    target_compile_definitions(libavoid_static PUBLIC LIBAVOID_NO_DLL NDEBUG)
    target_compile_options(libavoid_static PRIVATE /EHsc /W3)
else()
    target_compile_options(libavoid_static PRIVATE -Wno-unused-parameter)
endif()

# pybind11 is provided by the build environment (pyproject.toml lists
# it in build-system.requires, and cibuildwheel pins a version).
find_package(Python 3.11 COMPONENTS Interpreter Development.Module REQUIRED)
find_package(pybind11 CONFIG REQUIRED)

pybind11_add_module(_core MODULE
    src/bindings/module.cpp
    src/bindings/geometry.cpp
    src/bindings/router.cpp
    src/bindings/shape.cpp
    src/bindings/connector.cpp
    src/bindings/junction.cpp
)

target_include_directories(_core PRIVATE src/bindings)

target_link_libraries(_core PRIVATE libavoid_static)

target_compile_definitions(_core PRIVATE
    LIBAVOID_COMMIT_HASH="${LIBAVOID_COMMIT_HASH}"
)

install(TARGETS _core LIBRARY DESTINATION libavoid_py)
