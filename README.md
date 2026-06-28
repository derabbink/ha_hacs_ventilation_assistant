# Ventilation Assistant

Ventilation Assistant is a Home Assistant custom integration for HACS. It creates virtual ventilation devices from existing indoor sensors, outdoor sensors, and door/window contacts.

## Model

The integration does not create Home Assistant helpers or visible configuration entries. Everything is configured from YAML, and the integration only creates the resulting entities/devices.

Add this to `/config/configuration.yaml`:

```yaml
ventilation_assistant:
```

Global defaults and ventilation devices are loaded behind the scenes from `/config/ventilation_assistant.yaml`. If that file does not exist, the built-in defaults are used and no devices are created:

```yaml
comfort_temp_min: 19.0
comfort_temp_max: 24.0
comfort_rh_min: 40.0
comfort_rh_max: 60.0
priority: TEMPERATURE

devices:
  - id: living_room
    name: Living room
    indoor_temp_entities:
      - sensor.living_room_temperature
    indoor_humidity_entities:
      - sensor.living_room_humidity
    outdoor_temp_entities:
      - sensor.outdoor_temperature
    outdoor_humidity_entities:
      - sensor.outdoor_humidity
    door_window_entities:
      - binary_sensor.living_room_window
```

`priority` can be `TEMPERATURE` or `HUMIDITY`. Each device can override any global default, or leave that field absent to inherit the global setting. Restart Home Assistant after changing this file.

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

Copy or symlink this repository into Home Assistant, or add it as a HACS custom repository with category `Integration`. After installing, add `ventilation_assistant:` to `/config/configuration.yaml`, create `/config/ventilation_assistant.yaml`, and restart Home Assistant.

Create one YAML device per room. To change global defaults or devices, edit `/config/ventilation_assistant.yaml` and restart Home Assistant.
