#pragma once

#include <cstdint>
#include <memory>

class IGpioProvider;

struct OilTempOverride
{
    bool present;
    bool invalid;
    int32_t celsius;
};

struct OilTempPanelTrace
{
    bool enabled;
    const char *scenario;
    unsigned input_seq;
};

#if defined(WOKWI_EMULATOR) && defined(OIL_TEMP_ACCEPTANCE)
OilTempOverride OilTempDisplayOverride();
bool OilTempAcceptanceForceSample();
bool OilTempRawPairActive();
int OilTempAcceptanceErrorCount();
void OilTempAcceptanceNoteSample(bool did_sample, bool invalid, int report_delta, int32_t raw_value = 0);
OilTempPanelTrace OilTempPanelTraceNow();
void OilTempAcceptanceBegin();
void OilTempAcceptancePoll();
std::unique_ptr<IGpioProvider> OilTempWrapGpio(std::unique_ptr<IGpioProvider> inner);
#else
inline OilTempOverride OilTempDisplayOverride()
{
    return OilTempOverride{false, false, 0};
}
inline bool OilTempAcceptanceForceSample()
{
    return false;
}
inline bool OilTempRawPairActive()
{
    return false;
}
inline int OilTempAcceptanceErrorCount()
{
    return 0;
}
inline void OilTempAcceptanceNoteSample(bool, bool, int, int32_t = 0) {}
inline OilTempPanelTrace OilTempPanelTraceNow()
{
    return OilTempPanelTrace{false, "", 0};
}
inline void OilTempAcceptanceBegin() {}
inline void OilTempAcceptancePoll() {}
#endif
