// Host toolchain smoke: C++17 only, no firmware or third-party deps.
#include <cassert>
#include <cstdlib>
#include <iostream>
#include <optional>
#include <string_view>

int main()
{
    constexpr std::string_view tag = "clarity-host-smoke";
    std::optional<int> v = 17;
    assert(v.has_value());
    assert(*v == 17);
    std::cout << tag << ": PASS (C++17)\n";
    return EXIT_SUCCESS;
}