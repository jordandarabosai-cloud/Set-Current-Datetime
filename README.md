# Evo - Set Current Datetime

Sets the current date/time on a Generac Evolution controller over Modbus RTU.

## Requirements
- Python 3.9+
- `pymodbus`

```bash
pip install pymodbus
pip install backports.zoneinfo  # for Python <3.9
```

## Usage
```bash
python3 set_datetime.py
```

The script prompts for timezone (Eastern/Central/Mountain/Pacific), confirms the target datetime, then writes registers:
- 0x000E (14): hour/minute
- 0x000F (15): month/day
- 0x0010 (16): day-of-week/year

Defaults:
- Port: `/dev/USB232`
- Slave ID: `157`
- Baud: `9600` (8N1)
