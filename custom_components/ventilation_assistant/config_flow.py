"""Config flow for Ventilation Assistant."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.core import callback
from homeassistant.helpers import selector

if TYPE_CHECKING:
    from collections.abc import Mapping

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
    MINOR_VERSION = 2

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Set up global defaults."""

        if self._async_current_entries():
            return self.async_abort(reason="already_configured")

        return await self.async_step_global(user_input)

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

    @staticmethod
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Return the options flow."""

        return VentilationAssistantOptionsFlow(config_entry)

    @classmethod
    @callback
    def async_get_supported_subentry_types(
        cls, config_entry: config_entries.ConfigEntry
    ) -> dict[str, type[config_entries.ConfigSubentryFlow]]:
        """Return subentry flows supported by this config entry."""

        if config_entry.data[CONF_KIND] != CONF_GLOBAL:
            return {}
        return {CONF_DEVICE: VentilationDeviceSubentryFlow}


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


class VentilationDeviceSubentryFlow(config_entries.ConfigSubentryFlow):
    """Handle virtual ventilation device subentries."""

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.SubentryFlowResult:
        """Create one virtual ventilation device."""

        if user_input is not None:
            name = user_input[CONF_NAME]
            if self._name_exists(name):
                return self.async_abort(reason="already_configured")

            return self.async_create_entry(
                title=name,
                data=_device_options(user_input),
            )

        return self.async_show_form(
            step_id="user",
            data_schema=_device_schema(),
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.SubentryFlowResult:
        """Reconfigure one virtual ventilation device."""

        subentry = self._get_reconfigure_subentry()
        if user_input is not None:
            return self.async_update_and_abort(
                self._get_entry(),
                subentry,
                data=_device_options(user_input),
                title=subentry.title,
            )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=_device_schema(
                {
                    **subentry.data,
                    CONF_NAME: subentry.title,
                }
            ),
        )

    def _name_exists(self, name: str) -> bool:
        """Return whether another device subentry already uses this name."""

        return any(
            subentry.title.casefold() == name.casefold()
            for subentry in self._get_entry().get_subentries_of_type(CONF_DEVICE)
        )


def _global_schema(defaults: Mapping[str, Any] | None = None) -> vol.Schema:
    defaults = defaults or {}
    return vol.Schema(
        {
            vol.Optional(
                CONF_OUTDOOR_TEMP_ENTITIES,
                default=defaults.get(CONF_OUTDOOR_TEMP_ENTITIES, []),
            ): _entity_selector("sensor", "temperature"),
            vol.Optional(
                CONF_OUTDOOR_HUMIDITY_ENTITIES,
                default=defaults.get(CONF_OUTDOOR_HUMIDITY_ENTITIES, []),
            ): _entity_selector("sensor", "humidity"),
            vol.Required(
                CONF_COMFORT_TEMP_MIN,
                default=defaults.get(CONF_COMFORT_TEMP_MIN, DEFAULT_COMFORT_TEMP_MIN),
            ): _temperature_number_selector(),
            vol.Required(
                CONF_COMFORT_TEMP_MAX,
                default=defaults.get(CONF_COMFORT_TEMP_MAX, DEFAULT_COMFORT_TEMP_MAX),
            ): _temperature_number_selector(),
            vol.Required(
                CONF_COMFORT_RH_MIN,
                default=defaults.get(CONF_COMFORT_RH_MIN, DEFAULT_COMFORT_RH_MIN),
            ): _humidity_number_selector(),
            vol.Required(
                CONF_COMFORT_RH_MAX,
                default=defaults.get(CONF_COMFORT_RH_MAX, DEFAULT_COMFORT_RH_MAX),
            ): _humidity_number_selector(),
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
            ): _entity_selector("sensor", "temperature"),
            vol.Optional(
                CONF_INDOOR_HUMIDITY_ENTITIES,
                default=defaults.get(CONF_INDOOR_HUMIDITY_ENTITIES, []),
            ): _entity_selector("sensor", "humidity"),
            vol.Optional(
                CONF_OUTDOOR_TEMP_ENTITIES,
                default=defaults.get(CONF_OUTDOOR_TEMP_ENTITIES, []),
            ): _entity_selector("sensor", "temperature"),
            vol.Optional(
                CONF_OUTDOOR_HUMIDITY_ENTITIES,
                default=defaults.get(CONF_OUTDOOR_HUMIDITY_ENTITIES, []),
            ): _entity_selector("sensor", "humidity"),
            vol.Optional(
                CONF_DOOR_WINDOW_ENTITIES,
                default=defaults.get(CONF_DOOR_WINDOW_ENTITIES, []),
            ): _entity_selector("binary_sensor", ["door", "opening", "window"]),
            vol.Optional(
                CONF_COMFORT_TEMP_MIN, default=defaults.get(CONF_COMFORT_TEMP_MIN)
            ): _temperature_number_selector(),
            vol.Optional(
                CONF_COMFORT_TEMP_MAX, default=defaults.get(CONF_COMFORT_TEMP_MAX)
            ): _temperature_number_selector(),
            vol.Optional(
                CONF_COMFORT_RH_MIN, default=defaults.get(CONF_COMFORT_RH_MIN)
            ): _humidity_number_selector(),
            vol.Optional(
                CONF_COMFORT_RH_MAX, default=defaults.get(CONF_COMFORT_RH_MAX)
            ): _humidity_number_selector(),
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


def _entity_selector(
    domain: str, device_class: str | list[str]
) -> selector.EntitySelector:
    return selector.EntitySelector(
        selector.EntitySelectorConfig(
            domain=domain,
            device_class=device_class,
            multiple=True,
        )
    )


def _temperature_number_selector() -> selector.NumberSelector:
    return selector.NumberSelector(
        selector.NumberSelectorConfig(
            min=-30,
            max=50,
            step=0.5,
            mode=selector.NumberSelectorMode.BOX,
            unit_of_measurement="°C",
        )
    )


def _humidity_number_selector() -> selector.NumberSelector:
    return selector.NumberSelector(
        selector.NumberSelectorConfig(
            min=0,
            max=100,
            step=1,
            mode=selector.NumberSelectorMode.BOX,
            unit_of_measurement="%",
        )
    )


def _global_options(user_input: Mapping[str, Any]) -> dict[str, Any]:
    return {
        CONF_OUTDOOR_TEMP_ENTITIES: _entity_ids(
            user_input.get(CONF_OUTDOOR_TEMP_ENTITIES)
        ),
        CONF_OUTDOOR_HUMIDITY_ENTITIES: _entity_ids(
            user_input.get(CONF_OUTDOOR_HUMIDITY_ENTITIES)
        ),
        CONF_COMFORT_TEMP_MIN: user_input[CONF_COMFORT_TEMP_MIN],
        CONF_COMFORT_TEMP_MAX: user_input[CONF_COMFORT_TEMP_MAX],
        CONF_COMFORT_RH_MIN: user_input[CONF_COMFORT_RH_MIN],
        CONF_COMFORT_RH_MAX: user_input[CONF_COMFORT_RH_MAX],
        CONF_PRIORITY: user_input[CONF_PRIORITY],
    }


def _device_options(user_input: Mapping[str, Any]) -> dict[str, Any]:
    options = {
        CONF_INDOOR_TEMP_ENTITIES: _entity_ids(
            user_input.get(CONF_INDOOR_TEMP_ENTITIES)
        ),
        CONF_INDOOR_HUMIDITY_ENTITIES: _entity_ids(
            user_input.get(CONF_INDOOR_HUMIDITY_ENTITIES)
        ),
        CONF_OUTDOOR_TEMP_ENTITIES: _entity_ids(
            user_input.get(CONF_OUTDOOR_TEMP_ENTITIES)
        ),
        CONF_OUTDOOR_HUMIDITY_ENTITIES: _entity_ids(
            user_input.get(CONF_OUTDOOR_HUMIDITY_ENTITIES)
        ),
        CONF_DOOR_WINDOW_ENTITIES: _entity_ids(
            user_input.get(CONF_DOOR_WINDOW_ENTITIES)
        ),
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


def _entity_ids(value: Any) -> list[str]:
    """Return selector entity ids as a list."""

    if value is None:
        return []
    if isinstance(value, str):
        return [value] if value else []
    return list(value)
