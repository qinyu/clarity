// Host behavior for the oil-temperature sample cache and panel refresh decision.
// Expectations come from the confirmed A1–A4 cases and the 100 °C alarm threshold, not from the production bodies.
#include "../../../../include/panels/oil_temperature_refresh.h"
#include "../../../../include/sensors/oil_temperature_sample_state.h"

#include <cstdint>
#include <iostream>

namespace
{
int g_failures = 0;

void Fail(const char *message)
{
    std::cout << "FAIL " << message << "\n";
    ++g_failures;
}

void Ok(const char *message)
{
    std::cout << "ok " << message << "\n";
}

void CheckCache()
{
    OilTemperatureSampleState state;
    const OilTemperatureHeld before = HoldOilTemperatureReading(state);
    if (!before.valid || before.value != 0)
    {
        Fail("before first sample did not keep the initial value");
    }
    else
    {
        Ok("before first sample keeps initial value");
    }

    AcceptOilTemperatureSample(state, true, 80);
    const OilTemperatureHeld valid = HoldOilTemperatureReading(state);
    if (!valid.valid || valid.value != 80)
    {
        Fail("valid sample 80 was not held");
    }
    else
    {
        Ok("valid sample 80 held");
    }

    AcceptOilTemperatureSample(state, false, 0);
    const OilTemperatureHeld after_invalid = HoldOilTemperatureReading(state);
    const OilTemperatureHeld still_invalid = HoldOilTemperatureReading(state);
    if (after_invalid.valid || still_invalid.valid)
    {
        const int32_t cached = after_invalid.valid ? after_invalid.value : still_invalid.value;
        std::cout << "FAIL oil-temp cache: after invalid sample held cached " << cached << "\n";
        ++g_failures;
        return;
    }
    Ok("invalid sample stays invalid inside the interval");

    AcceptOilTemperatureSample(state, true, 80);
    if (OilTemperatureStateChanged(state) || state.change_baseline != 80)
    {
        Fail("first valid reading did not establish the change baseline");
    }
    AcceptOilTemperatureSample(state, false, 0);
    if (OilTemperatureStateChanged(state) || state.change_baseline != 80)
    {
        Fail("invalid reading moved the change baseline");
    }
    else
    {
        Ok("invalid reading keeps the change baseline");
    }
    AcceptOilTemperatureSample(state, true, 90);
    if (!OilTemperatureStateChanged(state) || state.change_baseline != 90)
    {
        Fail("restored different value did not report a change");
    }
    else
    {
        Ok("restored different value reports a change");
    }

    AcceptOilTemperatureSample(state, true, 80);
    if (!HoldOilTemperatureReading(state).valid || HoldOilTemperatureReading(state).value != 80)
    {
        Fail("same-value sample 80 was not held");
    }
    else
    {
        Ok("same-value sample 80 held");
    }

    AcceptOilTemperatureSample(state, true, 90);
    const OilTemperatureHeld different = HoldOilTemperatureReading(state);
    if (!different.valid || different.value != 90)
    {
        Fail("different-value sample 90 was not held");
    }
    else
    {
        Ok("different-value sample 90 held");
    }
}

OilTemperatureRefreshDecision Decide(bool valid, int32_t mapped, int32_t last_shown, int32_t deadband, bool was_unavailable)
{
    OilTemperatureRefreshRequest request;
    request.reading_valid = valid;
    request.mapped_value = mapped;
    request.last_shown = last_shown;
    request.deadband = deadband;
    request.was_unavailable = was_unavailable;
    return DecideOilTemperatureRefresh(request);
}

void CheckRefresh()
{
    constexpr int32_t k_deadband = 5;
    constexpr int32_t k_alarm_celsius = 100;

    const OilTemperatureRefreshDecision same = Decide(true, 80, 80, k_deadband, true);
    if (!same.set_position || !same.refresh_style || same.use_deadband)
    {
        Fail("oil-temp recovery: same-value 80 skipped position and style");
    }
    else
    {
        Ok("same-value recovery requests position and style");
    }

    const OilTemperatureRefreshDecision different = Decide(true, 90, 80, k_deadband, true);
    if (!different.set_position || !different.refresh_style || different.display_value != 90)
    {
        Fail("oil-temp recovery: different-value 90 skipped position and style");
    }
    else
    {
        Ok("different-value recovery requests position and style");
    }

    const OilTemperatureRefreshDecision hot = Decide(true, 110, 80, k_deadband, true);
    if (!hot.set_position || !hot.refresh_style || hot.display_value != 110)
    {
        Fail("oil-temp recovery: 110 skipped immediate position and style");
    }
    else if (!(80 < k_alarm_celsius && 110 >= k_alarm_celsius))
    {
        Fail("110 was not on the documented high-temperature side of 100");
    }
    else
    {
        Ok("cross-threshold recovery requests position and style");
    }

    const OilTemperatureRefreshDecision within = Decide(true, 82, 80, k_deadband, false);
    if (within.set_position || within.refresh_style || !within.use_deadband)
    {
        Fail("normal valid value inside deadband was not left on the deadband path");
    }
    else
    {
        Ok("normal valid value inside deadband");
    }

    const OilTemperatureRefreshDecision outside = Decide(true, 90, 80, k_deadband, false);
    if (outside.set_position || !outside.use_deadband || !outside.refresh_style)
    {
        Fail("normal valid value outside deadband left the deadband path");
    }
    else
    {
        Ok("normal valid value outside deadband still refreshes style");
    }

    const OilTemperatureRefreshDecision unavailable = Decide(false, 80, 80, k_deadband, false);
    if (!unavailable.show_unavailable || unavailable.set_position || unavailable.refresh_style)
    {
        Fail("invalid reading did not request the unavailable prompt");
    }
    else
    {
        Ok("invalid reading requests unavailable prompt");
    }
}
} // namespace

int main()
{
    std::cout << "oil-temperature behavior\n";
    CheckCache();
    CheckRefresh();
    if (g_failures != 0)
    {
        std::cout << "oil-temperature behavior: FAIL " << g_failures << "\n";
        return 1;
    }
    std::cout << "oil-temperature behavior: PASS\n";
    return 0;
}
