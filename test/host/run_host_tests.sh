#!/usr/bin/env bash
# Clarity host unit-test runner: system C++17 compiler only (no PlatformIO native).
# Compile and run failures propagate as non-zero exit; stderr is not swallowed.

HOST_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${HOST_DIR}/../.." && pwd)"
BUILD_DIR="${HOST_DIR}/.build"
STD_CXX=17

resolve_cxx()
{
    if [[ -n "${CXX:-}" ]]; then
        command -v "${CXX}"
        return
    fi
    for candidate in clang++ g++ c++; do
        if command -v "${candidate}" >/dev/null 2>&1; then
            echo "${candidate}"
            return 0
        fi
    done
    return 1
}

run_one_suite()
{
    local suite_dir="$1"
    local suite_name
    suite_name="$(basename "${suite_dir}")"

    shopt -s nullglob
    local sources=("${suite_dir}"/*.cpp)
    shopt -u nullglob

    if [[ ${#sources[@]} -eq 0 ]]; then
        return 0
    fi

    local out="${BUILD_DIR}/${suite_name}"
    local cxx="$2"

    echo "== compile: ${suite_name} (${#sources[@]} source(s))"
    if ! "${cxx}" -std=c++"${STD_CXX}" -Wall -Wextra -pedantic \
        "${sources[@]}" -o "${out}" 2>&1; then
        echo "host tests: COMPILE FAILED (${suite_name})" >&2
        return 1
    fi

    echo "== run: ${suite_name}"
    local run_rc=0
    "${out}" 2>&1 || run_rc=$?
    if [[ "${run_rc}" -ne 0 ]]; then
        echo "host tests: RUN FAILED (${suite_name}, exit ${run_rc})" >&2
        return 1
    fi

    return 0
}

main()
{
    local cxx
    if ! cxx="$(resolve_cxx)"; then
        echo "host tests: C++ compiler not found (${CXX:-clang++/g++/c++})" >&2
        exit 1
    fi

    echo "Clarity host tests"
    echo "  project root: ${PROJECT_ROOT}"
    echo "  compiler:     ${cxx} ($("${cxx}" --version 2>/dev/null | head -n 1))"
    echo "  standard:     C++${STD_CXX}"

    if [[ ! -f "${HOST_DIR}/smoke/toolchain_smoke.cpp" ]]; then
        echo "host tests: toolchain smoke source is missing" >&2
        exit 1
    fi
    mkdir -p "${BUILD_DIR}" || exit 1

    local failed=0

    if ! run_one_suite "${HOST_DIR}/smoke" "${cxx}"; then
        failed=1
    fi

    # Develop-phase suites (theme, oil-temperature): add sources under test/host/cases/<name>/
    if [[ -d "${HOST_DIR}/cases" ]]; then
        for case_dir in "${HOST_DIR}"/cases/*/; do
            [[ -d "${case_dir}" ]] || continue
            if ! run_one_suite "${case_dir}" "${cxx}"; then
                failed=1
            fi
        done
    fi

    if [[ "${failed}" -ne 0 ]]; then
        echo "host tests: FAILED" >&2
        exit 1
    fi

    echo "host tests: PASS"
    exit 0
}

main "$@"
