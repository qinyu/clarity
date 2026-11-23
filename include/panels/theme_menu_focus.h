#pragma once

#include <algorithm>
#include <cstddef>
#include <string>
#include <vector>

// Keep the first option as the fallback for unrelated menus or an unknown saved value.
inline std::size_t InitialOptionsFocusIndex(bool focusSavedValue,
                                            const std::vector<std::string>& options,
                                            const std::string& savedValue)
{
    if (!focusSavedValue) {
        return 0;
    }

    const auto savedOption = std::find(options.begin(), options.end(), savedValue);
    return savedOption == options.end()
        ? 0
        : static_cast<std::size_t>(savedOption - options.begin());
}
