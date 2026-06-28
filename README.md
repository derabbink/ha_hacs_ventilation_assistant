# Ventilation Assistant

Ventilation Assistant is a Home Assistant custom integration for HACS. It creates virtual ventilation devices from existing indoor sensors, outdoor sensors, and door/window contacts.

## Model

The integration is fully configurable from the Home Assistant UI. Configuration is stored by Home Assistant as config entries in `.storage/core.config_entries`; it does not create Home Assistant Helpers.

Use the config flow to create:

- one global defaults entry for the shared comfort temperature band, comfort relative-humidity band, and decision priority
- one ventilation device entry per room/area/device

`priority` can be `TEMPERATURE` or `HUMIDITY`. Each device can override any global default, or leave that field empty to inherit the global setting.

Each ventilation device creates a Home Assistant device containing:

- Indoor temperature average
- Indoor relative humidity average
- Indoor absolute humidity
- Indoor projected absolute humidity
- Indoor projected relative humidity
- Indoor projected relative-humidity difference
- Indoor projected temperature difference
- Outdoor temperature average
- Outdoor relative humidity average
- Outdoor absolute humidity
- Any doors/windows open
- Door/window open percentage
- Temperature advice: `KEEP_CLOSED`, `OPEN`, `KEEP_OPEN`, or `CLOSE`
- Humidity advice: `KEEP_CLOSED`, `OPEN`, `KEEP_OPEN`, or `CLOSE`
- Advice: `KEEP_CLOSED`, `OPEN`, `KEEP_OPEN`, or `CLOSE`

## Availability

Calculated entities return unavailable when their required inputs are missing or unavailable:

- Averages require at least one available source entity.
- Absolute humidity requires temperature and relative humidity.
- Projected indoor absolute humidity requires indoor temperature and outdoor absolute humidity.
- Projected indoor relative humidity requires indoor temperature and projected absolute humidity.
- Door/window sensors require at least one available contact sensor.
- Advice requires either available indoor/outdoor temperature values or available
  indoor/projected relative-humidity values. Without an available contact sensor,
  advice is limited to `OPEN` or `CLOSE`.

## HACS installation during development

Copy or symlink this repository into Home Assistant, or add it as a HACS custom repository with category `Integration`. After installing, restart Home Assistant and add **Ventilation Assistant** from **Settings > Devices & services**.

Create the global defaults entry first, then create one ventilation device per room.
