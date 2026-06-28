"""Config flow for Ventilation Assistant."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.helpers import selector

from .const import (
    CONF_COMFORT_RH_MAX,
    CONF_COMFORT_RH_MIN,
    CONF_COMFORT_TEMP_MAX,
    CONF_COMFORT_TEMP_MIN,
    CONF_DEVICE,
    CONF_DOOR_WINDOW_ENTITIES,
    CONF_GLOBAL,
    CONF_INDOOR_HUMIDITY_ENTITIES,
    CONF_INDOOR_TEMP_ENTITIES,
    CONF_KIND,
    CONF_OUTDOOR_HUMIDITY_ENTITIES,
    CONF_OUTDOOR_TEMP_ENTITIES,
    CONF_PRIORITY,
    DEFAULT_COMFORT_RH_MAX,
    DEFAULT_COMFORT_RH_MIN,
    DEFAULT_COMFORT_TEMP_MAX,
    DEFAULT_COMFORT_TEMP_MIN,
    DOMAIN,
    Priority,
)


class VentilationAssistantConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Ventilation Assistant."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Route the user to global settings or virtual device creation."""

        if user_input is not None:
            if user_input[CONF_KIND] == CONF_GLOBAL:
                return await self.async_step_global()
            return await self.async_step_device()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_KIND): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=[
                                selector.SelectOptionDict(
                                    value=CONF_GLOBAL, label="Configure global defaults"
                                ),
                                selector.SelectOptionDict(
                                    value=CONF_DEVICE, label="Create ventilation device"
                                ),
                            ],
                            mode=selector.SelectSelectorMode.DROPDOWN,
                        )
                    )
                }
            ),
        )

    async def async_step_global(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Create the singleton global defaults entry."""

        await self.async_set_unique_id(CONF_GLOBAL)
        self._abort_if_unique_id_configured()

        if user_input is not None:
            return self.async_create_entry(
                title="Ventilation Assistant",
                data={CONF_KIND: CONF_GLOBAL},
                options=_global_options(user_input),
            )

        return self.async_show_form(
            step_id="global",
            data_schema=_global_schema(),
        )

    async def async_step_device(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Create one virtual ventilation device."""

        if user_input is not None:
            name = user_input[CONF_NAME]
            await self.async_set_unique_id(f"{CONF_DEVICE}:{name.casefold()}")
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=name,
                data={CONF_KIND: CONF_DEVICE, CONF_NAME: name},
                options=_device_options(user_input),
            )

        return self.async_show_form(
            step_id="device",
            data_schema=_device_schema(),
        )

    @staticmethod
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Return the options flow."""

        return VentilationAssistantOptionsFlow(config_entry)


class VentilationAssistantOptionsFlow(config_entries.OptionsFlow):
    """Handle options for Ventilation Assistant entries."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""

        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Edit global defaults or one virtual device."""

        kind = self._config_entry.data[CONF_KIND]
        if user_input is not None:
            options = (
                _global_options(user_input)
                if kind == CONF_GLOBAL
                else _device_options(user_input)
            )
            return self.async_create_entry(title="", data=options)

        if kind == CONF_GLOBAL:
            return self.async_show_form(
                step_id="init",
                data_schema=_global_schema(self._config_entry.options),
            )

        return self.async_show_form(
            step_id="init",
            data_schema=_device_schema(
                {
                    **self._config_entry.options,
                    CONF_NAME: self._config_entry.data[CONF_NAME],
                }
            ),
        )


def _global_schema(defaults: Mapping[str, Any] | None = None) -> vol.Schema:
    defaults = defaults or {}
    return vol.Schema(
        {
            vol.Required(
                CONF_COMFORT_TEMP_MIN,
                default=defaults.get(CONF_COMFORT_TEMP_MIN, DEFAULT_COMFORT_TEMP_MIN),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=-30,
                    max=50,
                    step=0.5,
                    mode=selector.NumberSelectorMode.BOX,
                    unit_of_measurement="°C",
                )
            ),
            vol.Required(
                CONF_COMFORT_TEMP_MAX,
                default=defaults.get(CONF_COMFORT_TEMP_MAX, DEFAULT_COMFORT_TEMP_MAX),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=-30,
                    max=50,
                    step=0.5,
                    mode=selector.NumberSelectorMode.BOX,
                    unit_of_measurement="°C",
                )
            ),
            vol.Required(
                CONF_COMFORT_RH_MIN,
                default=defaults.get(CONF_COMFORT_RH_MIN, DEFAULT_COMFORT_RH_MIN),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0,
                    max=100,
                    step=1,
                    mode=selector.NumberSelectorMode.BOX,
                    unit_of_measurement="%",
                )
            ),
            vol.Required(
                CONF_COMFORT_RH_MAX,
                default=defaults.get(CONF_COMFORT_RH_MAX, DEFAULT_COMFORT_RH_MAX),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0,
                    max=100,
                    step=1,
                    mode=selector.NumberSelectorMode.BOX,
                    unit_of_measurement="%",
                )
            ),
            vol.Required(
                CONF_PRIORITY,
                default=defaults.get(CONF_PRIORITY, Priority.TEMPERATURE.value),
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[priority.value for priority in Priority],
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            ),
        }
    )


def _device_schema(defaults: Mapping[str, Any] | None = None) -> vol.Schema:
    defaults = defaults or {}
    schema: dict[Any, Any] = {}
    if CONF_NAME not in defaults:
        schema[vol.Required(CONF_NAME)] = str

    schema.update(
        {
            vol.Optional(
                CONF_INDOOR_TEMP_ENTITIES,
                default=defaults.get(CONF_INDOOR_TEMP_ENTITIES, []),
            ): _entity_selector("sensor"),
            vol.Optional(
                CONF_INDOOR_HUMIDITY_ENTITIES,
                default=defaults.get(CONF_INDOOR_HUMIDITY_ENTITIES, []),
            ): _entity_selector("sensor"),
            vol.Optional(
                CONF_OUTDOOR_TEMP_ENTITIES,
                default=defaults.get(CONF_OUTDOOR_TEMP_ENTITIES, []),
            ): _entity_selector("sensor"),
            vol.Optional(
                CONF_OUTDOOR_HUMIDITY_ENTITIES,
                default=defaults.get(CONF_OUTDOOR_HUMIDITY_ENTITIES, []),
            ): _entity_selector("sensor"),
            vol.Optional(
                CONF_DOOR_WINDOW_ENTITIES,
                default=defaults.get(CONF_DOOR_WINDOW_ENTITIES, []),
            ): _entity_selector("binary_sensor"),
            vol.Optional(
                CONF_COMFORT_TEMP_MIN, default=defaults.get(CONF_COMFORT_TEMP_MIN)
            ): vol.Any(None, float),
            vol.Optional(
                CONF_COMFORT_TEMP_MAX, default=defaults.get(CONF_COMFORT_TEMP_MAX)
            ): vol.Any(None, float),
            vol.Optional(
                CONF_COMFORT_RH_MIN, default=defaults.get(CONF_COMFORT_RH_MIN)
            ): vol.Any(None, float),
            vol.Optional(
                CONF_COMFORT_RH_MAX, default=defaults.get(CONF_COMFORT_RH_MAX)
            ): vol.Any(None, float),
            vol.Optional(
                CONF_PRIORITY, default=defaults.get(CONF_PRIORITY, "")
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[
                        selector.SelectOptionDict(value="", label="Use global default"),
                        *[
                            selector.SelectOptionDict(
                                value=priority.value, label=priority.value
                            )
                            for priority in Priority
                        ],
                    ],
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            ),
        }
    )
    return vol.Schema(schema)


def _entity_selector(domain: str) -> selector.EntitySelector:
    return selector.EntitySelector(
        selector.EntitySelectorConfig(domain=domain, multiple=True)
    )


def _global_options(user_input: Mapping[str, Any]) -> dict[str, Any]:
    return {
        CONF_COMFORT_TEMP_MIN: user_input[CONF_COMFORT_TEMP_MIN],
        CONF_COMFORT_TEMP_MAX: user_input[CONF_COMFORT_TEMP_MAX],
        CONF_COMFORT_RH_MIN: user_input[CONF_COMFORT_RH_MIN],
        CONF_COMFORT_RH_MAX: user_input[CONF_COMFORT_RH_MAX],
        CONF_PRIORITY: user_input[CONF_PRIORITY],
    }


def _device_options(user_input: Mapping[str, Any]) -> dict[str, Any]:
    options = {
        CONF_INDOOR_TEMP_ENTITIES: user_input.get(CONF_INDOOR_TEMP_ENTITIES, []),
        CONF_INDOOR_HUMIDITY_ENTITIES: user_input.get(CONF_INDOOR_HUMIDITY_ENTITIES, []),
        CONF_OUTDOOR_TEMP_ENTITIES: user_input.get(CONF_OUTDOOR_TEMP_ENTITIES, []),
        CONF_OUTDOOR_HUMIDITY_ENTITIES: user_input.get(CONF_OUTDOOR_HUMIDITY_ENTITIES, []),
        CONF_DOOR_WINDOW_ENTITIES: user_input.get(CONF_DOOR_WINDOW_ENTITIES, []),
    }

    for key in (
        CONF_COMFORT_TEMP_MIN,
        CONF_COMFORT_TEMP_MAX,
        CONF_COMFORT_RH_MIN,
        CONF_COMFORT_RH_MAX,
        CONF_PRIORITY,
    ):
        value = user_input.get(key)
        if value not in (None, ""):
            options[key] = value

    return options
