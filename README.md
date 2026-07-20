# Ventilation Assistant

Ventilation Assistant is a Home Assistant custom integration for HACS. It creates virtual ventilation devices from existing indoor sensors, outdoor sensors, and door/window contacts.

## Model

The integration is fully configurable from the Home Assistant UI. Configuration is stored by Home Assistant as config entries in `.storage/core.config_entries`; it does not create Home Assistant Helpers.

Use the config flow to create:

- one global defaults entry for the shared comfort temperature, relative-humidity, and carbon-dioxide bands, plus decision priority
- one or more ventilation device subentries under that entry

`priority` can be `TEMPERATURE`, `HUMIDITY`, or `CO2`. Each device can override any global default, or leave that field empty to inherit the global setting. Overall advice uses the selected component first, followed by the configured fallback order when that component is unavailable.

Each ventilation device creates a Home Assistant device containing:

- Temperature:
    - Indoor temperature average
    - Indoor projected temperature difference
    - Outdoor temperature average
- Humidity:
    - Indoor relative humidity average
    - Indoor absolute humidity
    - Indoor projected absolute humidity
    - Indoor projected relative humidity
    - Indoor projected relative-humidity difference
    - Outdoor relative humidity average
    - Outdoor absolute humidity
- Carbon Dioxide:
    - Indoor carbon dioxide average
    - Indoor projected carbon dioxide difference
    - Outdoor carbon dioxide average, using a per-device override when configured and otherwise the global Outdoor value
- Doors/Windows:
    - Any doors/windows open
    - Door/window open percentage
- Advice:
    - Temperature advice: `KEEP_CLOSED`, `OPEN`, `KEEP_OPEN`, or `CLOSE`
    - Humidity advice: `KEEP_CLOSED`, `OPEN`, `KEEP_OPEN`, or `CLOSE`
    - Carbon dioxide advice: `KEEP_CLOSED`, `OPEN`, `KEEP_OPEN`, or `CLOSE`
    - Advice: `KEEP_CLOSED`, `OPEN`, `KEEP_OPEN`, or `CLOSE`

## Availability

Calculated entities return unavailable when their required inputs are missing or unavailable:

- General
    - Averages require at least one available source entity.
- Carbon Dioxide
    - Global outdoor carbon dioxide defaults to 400 ppm only when no global outdoor carbon-dioxide sensors are configured. A device with no outdoor CO₂ override inherits that global value. If a configured global or per-device sensor list has no usable values, its result is unavailable.
    - Carbon-dioxide averages ignore unknown, unavailable, and non-numeric source values and are rounded to whole ppm.
- Humidity
    - Absolute humidity requires temperature and relative humidity.
    - Indoor projected absolute humidity requires indoor temperature and outdoor absolute humidity.
    - Indoor projected relative humidity requires indoor temperature and projected absolute humidity.
- Doors/Windows:
    - Door/window sensors require at least one available contact sensor.
    - Advice requires either available indoor/outdoor temperature values or available indoor/projected relative-humidity values.
    - Without an available contact sensor, advice is limited to `OPEN` or `CLOSE`.

## HACS installation during development

Copy or symlink this repository into Home Assistant, or add it as a HACS custom repository with category `Integration`. After installing, restart Home Assistant and add **Ventilation Assistant** from **Settings > Devices & services**.

Complete the global defaults form during first setup. After that, use **Add device** to add each ventilation device directly. Use the gear icon on the **Ventilation Assistant** integration entry to change the global defaults later. Use the configure action on a ventilation device subentry to change the input entities for that virtual device.

## Local testing and verification

Install `uv` first if it is not already available:

```sh
python3 -m pip install uv
```

Run the Python checks individually with the same dependency groups used by CI:

```sh
uv run --locked --no-dev python -m compileall custom_components tests
uv run --locked --group lint ruff check .
uv run --locked --group typecheck ty check
uv run --locked --group test pytest
```

Run the GitHub Action backed checks locally with Docker running:

```sh
sh scripts/hacs-validate
sh scripts/hassfest
```

Run the full local verification sequence with:

```sh
sh scripts/local-ci.sh
```
