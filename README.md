# Ventilation Assistant

Ventilation Assistant is a Home Assistant custom integration for HACS. It creates virtual ventilation devices from existing indoor sensors, outdoor sensors, and door/window contacts.

## Model

The integration uses two config-entry types:

- **Global defaults**: one singleton entry with the shared comfort temperature band, comfort relative-humidity band, and decision priority.
- **Ventilation devices**: one entry per room/area/device. Each device can override any global default, or leave that field empty to inherit the global setting.

Each ventilation device creates a Home Assistant device containing:

- Indoor temperature average
- Indoor relative humidity average
- Indoor absolute humidity
- Indoor projected absolute humidity
- Indoor projected relative humidity
- Indoor projected relative-humidity difference
- Indoor/outdoor temperature difference
- Outdoor temperature average
- Outdoor relative humidity average
- Outdoor absolute humidity
- Any door/window open
- Door/window open percentage
- Advice: `KEEP_CLOSED`, `OPEN`, `KEEP_OPEN`, or `CLOSE`

## Availability

Calculated entities return unavailable when their required inputs are missing or unavailable:

- Averages require at least one available source entity.
- Absolute humidity requires temperature and relative humidity.
- Projected indoor absolute humidity requires indoor temperature and outdoor absolute humidity.
- Projected indoor relative humidity requires indoor temperature and projected absolute humidity.
- Door/window sensors and advice require at least one available contact sensor.

## HACS installation during development

Copy or symlink this repository into Home Assistant, or add it as a HACS custom repository with category `Integration`. After installing, restart Home Assistant and add **Ventilation Assistant** from **Settings > Devices & services**.

Create the global defaults entry first, then create one ventilation device per room.
