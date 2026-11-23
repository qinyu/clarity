#include "sensors/oil_temperature_acceptance.h"

#if defined(WOKWI_EMULATOR) && defined(OIL_TEMP_ACCEPTANCE)

#include "hardware/gpio_pins.h"
#include "interfaces/i_gpio_provider.h"
#include "managers/error_manager.h"
#include "utilities/logging.h"

#include <Arduino.h>
#include <cstdlib>
#include <cstring>

namespace
{
char g_buffer[16];
size_t g_length = 0;
bool g_overflow = false;
char g_scenario[8] = "none";
unsigned g_input_seq = 0;
bool g_override = false;
bool g_override_invalid = false;
int32_t g_override_celsius = 0;
bool g_raw_armed = false;
bool g_raw_sampled = false;
bool g_gpio_pending = false;

bool ScenarioToken(const char *text)
{
    const size_t length = std::strlen(text);
    if (length < 1 || length > 6)
    {
        return false;
    }
    for (size_t i = 0; i < length; ++i)
    {
        const char c = text[i];
        const bool digit = c >= '0' && c <= '9';
        const bool upper = c >= 'A' && c <= 'Z';
        if (!digit && !upper)
        {
            return false;
        }
    }
    return true;
}

bool TemperatureToken(const char *text, int32_t *value)
{
    if (text[0] == '\0')
    {
        return false;
    }
    char *end = nullptr;
    const long parsed = std::strtol(text, &end, 10);
    if (end == text || *end != '\0' || parsed < 0 || parsed > 120)
    {
        return false;
    }
    *value = static_cast<int32_t>(parsed);
    return true;
}

void AcceptCommand(const char *command)
{
    ++g_input_seq;
    log_t("oil-temp input seq=%u scenario=%s cmd=%s", g_input_seq, g_scenario, command);
}

void HandleCommand(const char *line)
{
    if (std::strcmp(line, "INV") == 0)
    {
        g_override = true;
        g_override_invalid = true;
        g_raw_armed = false;
        g_gpio_pending = false;
        AcceptCommand(line);
        return;
    }
    if (std::strcmp(line, "CLR") == 0)
    {
        g_override = false;
        g_override_invalid = false;
        AcceptCommand(line);
        return;
    }
    if (std::strcmp(line, "RAW") == 0)
    {
        g_override = false;
        g_override_invalid = false;
        g_raw_armed = true;
        g_raw_sampled = false;
        g_gpio_pending = true;
        AcceptCommand(line);
        return;
    }
    if (std::strncmp(line, "S,", 2) == 0 && ScenarioToken(line + 2))
    {
        std::strncpy(g_scenario, line + 2, sizeof(g_scenario) - 1);
        g_scenario[sizeof(g_scenario) - 1] = '\0';
        AcceptCommand(line);
        return;
    }
    int32_t celsius = 0;
    if (std::strncmp(line, "T,", 2) == 0 && TemperatureToken(line + 2, &celsius))
    {
        g_override = true;
        g_override_invalid = false;
        g_override_celsius = celsius;
        g_raw_armed = false;
        g_gpio_pending = false;
        AcceptCommand(line);
        return;
    }
    log_t("oil-temp input reject");
}

class OilTempAcceptanceGpio : public IGpioProvider
{
  public:
    explicit OilTempAcceptanceGpio(std::unique_ptr<IGpioProvider> inner) : inner_(std::move(inner)) {}

    bool DigitalRead(int pin) override
    {
        return inner_->DigitalRead(pin);
    }

    uint16_t AnalogRead(int pin) override
    {
        if (pin == gpio_pins::OIL_TEMPERATURE && g_gpio_pending)
        {
            g_gpio_pending = false;
            return 4096;
        }
        return inner_->AnalogRead(pin);
    }

    void PinMode(int pin, int mode) override
    {
        inner_->PinMode(pin, mode);
    }

    void AttachInterrupt(int pin, void (*callback)(), int mode) override
    {
        inner_->AttachInterrupt(pin, callback, mode);
    }

    void DetachInterrupt(int pin) override
    {
        inner_->DetachInterrupt(pin);
    }

  private:
    std::unique_ptr<IGpioProvider> inner_;
};
} // namespace

OilTempOverride OilTempDisplayOverride()
{
    return OilTempOverride{g_override, g_override_invalid, g_override_celsius};
}

bool OilTempAcceptanceForceSample()
{
    return g_raw_armed && !g_raw_sampled;
}

bool OilTempRawPairActive()
{
    return g_raw_armed;
}

int OilTempAcceptanceErrorCount()
{
    int count = 0;
    for (const ErrorInfo &error : ErrorManager::Instance().GetErrorQueue())
    {
        if (error.level == ErrorLevel::ERROR && error.source != nullptr &&
            std::strcmp(error.source, "OilTemperatureSensor") == 0)
        {
            ++count;
        }
    }
    return count;
}

void OilTempAcceptanceNoteSample(bool did_sample, bool invalid, int report_delta, int32_t raw_value)
{
    if (!g_raw_armed)
    {
        return;
    }
    const char *value = invalid ? "invalid" : "valid";
    if (did_sample)
    {
        g_raw_sampled = true;
        log_t("oil-temp sample source=gpio39 sensor=OilTemperatureSensor raw=%ld value=%s report=+%d time=%lu",
              static_cast<long>(raw_value), value, report_delta, millis());
        return;
    }
    log_t("oil-temp sample source=cache value=%s report=+%d time=%lu", value, report_delta, millis());
    if (g_raw_sampled)
    {
        g_raw_armed = false;
        log_t("oil-temp raw probe clear");
    }
}

OilTempPanelTrace OilTempPanelTraceNow()
{
    return OilTempPanelTrace{g_override, g_scenario, g_input_seq};
}

void OilTempAcceptanceBegin()
{
    Serial.begin(115200, SERIAL_8N1, 17, 1, false, 0, 1);
    log_t("oil-temp acceptance rx=17 tx=1 display-input=on raw-probe=on");
}

void OilTempAcceptancePoll()
{
    while (Serial.available() > 0)
    {
        const int byte = Serial.read();
        if (byte < 0)
        {
            return;
        }
        if (byte == '\r')
        {
            continue;
        }
        if (byte != '\n')
        {
            if (g_length + 1 >= sizeof(g_buffer))
            {
                g_overflow = true;
                g_length = 0;
                log_t("oil-temp input reject");
            }
            else if (!g_overflow)
            {
                g_buffer[g_length++] = static_cast<char>(byte);
            }
            continue;
        }
        g_buffer[g_length] = '\0';
        if (!g_overflow)
        {
            HandleCommand(g_buffer);
        }
        g_overflow = false;
        g_length = 0;
    }
}

std::unique_ptr<IGpioProvider> OilTempWrapGpio(std::unique_ptr<IGpioProvider> inner)
{
    return std::make_unique<OilTempAcceptanceGpio>(std::move(inner));
}

#endif
