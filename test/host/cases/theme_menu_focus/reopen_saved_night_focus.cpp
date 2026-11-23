#include "panels/theme_menu_focus.h"

#include <cstdlib>
#include <iostream>
#include <string>
#include <vector>

static bool ExpectFocus(const char* scenario, std::size_t actual, std::size_t expected)
{
    if (actual != expected) {
        std::cerr << "theme_menu_focus: " << scenario << " expected focus index "
                  << expected << ", got " << actual << '\n';
        return false;
    }

    std::cout << "theme_menu_focus: PASS (" << scenario << ")\n";
    return true;
}

int main()
{
    const std::vector<std::string> themes{"Day", "Night"};
    const bool savedNight = ExpectFocus("saved Night reopen", InitialOptionsFocusIndex(true, themes, "Night"), 1);
    const bool savedDay = ExpectFocus("saved Day reopen", InitialOptionsFocusIndex(true, themes, "Day"), 0);
    const bool otherMenu = ExpectFocus("unrelated menu", InitialOptionsFocusIndex(false, themes, "Night"), 0);
    const bool missing = ExpectFocus("unknown saved value", InitialOptionsFocusIndex(true, themes, "Error"), 0);
    return savedNight && savedDay && otherMenu && missing ? EXIT_SUCCESS : EXIT_FAILURE;
}
