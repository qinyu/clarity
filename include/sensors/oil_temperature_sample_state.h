#pragma once

#include <cstdint>

// Header-only sample cache shared by OilTemperatureSensor::GetReading() and the host suite.
// Before the first sample the held reading stays the initial value.

struct OilTemperatureSampleState
{
    bool sampled = false;
    bool valid = false;
    int32_t value = 0;
    int32_t change_baseline = 0;
    bool change_baseline_set = false;
};

struct OilTemperatureHeld
{
    bool valid;
    int32_t value;
};

inline void AcceptOilTemperatureSample(OilTemperatureSampleState &state, bool adc_valid, int32_t converted)
{
    state.sampled = true;
    if (!adc_valid)
    {
        state.valid = false;
        return;
    }
    state.valid = true;
    state.value = converted;
}

inline OilTemperatureHeld HoldOilTemperatureReading(const OilTemperatureSampleState &state)
{
    if (!state.sampled || state.valid)
    {
        return OilTemperatureHeld{true, state.value};
    }
    return OilTemperatureHeld{false, 0};
}

inline bool OilTemperatureStateChanged(OilTemperatureSampleState &state)
{
    const OilTemperatureHeld held = HoldOilTemperatureReading(state);
    if (!held.valid)
    {
        return false;
    }
    if (!state.change_baseline_set)
    {
        state.change_baseline = held.value;
        state.change_baseline_set = true;
        return false;
    }
    const bool changed = held.value != state.change_baseline;
    state.change_baseline = held.value;
    return changed;
}
