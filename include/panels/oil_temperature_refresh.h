#pragma once

#include <cstdint>

// Header-only refresh decision shared by OemOilPanel::UpdateOilTemperature() and the host suite.
// Validity is applied before the temperature deadband. Recovery sets the needle and style together.

struct OilTemperatureRefreshRequest
{
    bool reading_valid = false;
    int32_t mapped_value = 0;
    int32_t last_shown = -1;
    int32_t deadband = 1;
    bool was_unavailable = false;
};

struct OilTemperatureRefreshDecision
{
    bool show_unavailable = false;
    bool set_position = false;
    bool refresh_style = false;
    bool use_deadband = false;
    int32_t display_value = 0;
};

inline OilTemperatureRefreshDecision DecideOilTemperatureRefresh(const OilTemperatureRefreshRequest &request)
{
    OilTemperatureRefreshDecision decision;
    decision.display_value = request.mapped_value;
    if (!request.reading_valid)
    {
        decision.show_unavailable = true;
        return decision;
    }
    if (request.was_unavailable)
    {
        decision.set_position = true;
        decision.refresh_style = true;
        return decision;
    }

    decision.use_deadband = true;
    const bool first = request.last_shown < 0;
    int32_t delta = request.deadband;
    if (!first)
    {
        delta = request.mapped_value >= request.last_shown
                    ? request.mapped_value - request.last_shown
                    : request.last_shown - request.mapped_value;
    }
    if (first || delta >= request.deadband)
    {
        decision.refresh_style = true;
    }
    return decision;
}
