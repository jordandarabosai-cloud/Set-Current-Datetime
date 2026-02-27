#!/usr/bin/env python3
from datetime import datetime
try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo

import minimalmodbus

PORT = "/dev/USB232"
SLAVE_ID = 157
BAUD = 9600
PARITY = minimalmodbus.serial.PARITY_NONE
STOPBITS = 1

TZ_OPTIONS = {
    "1": ("Eastern", "America/New_York"),
    "2": ("Central", "America/Chicago"),
    "3": ("Mountain", "America/Denver"),
    "4": ("Pacific", "America/Los_Angeles"),  # California
}
DEFAULT_CHOICE = "2"

# HPanel time registers
REG_TIME_HR_MIN = 0x00E0
REG_TIME_SEC_DOW = 0x00E1
REG_TIME_MONTH_DAY = 0x00E2
REG_TIME_YEAR = 0x00E3

# Set to True to write all 4 registers in one transaction (matches genmon AltTimeSet)
ALT_TIME_SET = True


def pick_timezone():
    print("Select timezone:")
    for key, (label, tz) in TZ_OPTIONS.items():
        print(f"  {key}) {label} ({tz})")
    choice = input(f"Choice [{DEFAULT_CHOICE}=Central]: ").strip()
    if not choice:
        choice = DEFAULT_CHOICE
    if choice not in TZ_OPTIONS:
        print("Invalid choice. Using Central.")
        choice = DEFAULT_CHOICE
    return TZ_OPTIONS[choice]


def map_dow(dt):
    # Python: Monday=0..Sunday=6
    # HPanel expects Sunday=1, Saturday=7
    dow = dt.weekday()
    if dow == 6:
        return 1
    return dow + 2


def main():
    label, tz = pick_timezone()
    now = datetime.now(ZoneInfo(tz))

    # align to the top of the minute (seconds = 0), like genmon
    while now.second != 0:
        import time
        time.sleep(60 - now.second)
        now = datetime.now(ZoneInfo(tz))

    print(f"\nUsing timezone: {label} ({tz})")
    print(f"Target datetime: {now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    confirm = input("Write this time to controller? (yes/no): ").strip().lower()
    if confirm not in ("y", "yes"):
        print("Cancelled.")
        return

    instrument = minimalmodbus.Instrument(PORT, SLAVE_ID)
    instrument.serial.baudrate = BAUD
    instrument.serial.parity = PARITY
    instrument.serial.stopbits = STOPBITS
    instrument.serial.timeout = 2

    dow = map_dow(now)

    if ALT_TIME_SET:
        # Write 4 registers at once: E0..E3
        data = [
            (now.hour << 8) | now.minute,  # E0
            (now.second << 8) | dow,        # E1
            (now.month << 8) | now.day,     # E2
            ((now.year - 2000) << 8) | 0,   # E3 (low byte unknown)
        ]
        instrument.write_registers(REG_TIME_HR_MIN, data)
    else:
        instrument.write_register(REG_TIME_HR_MIN, (now.hour << 8) | now.minute)
        instrument.write_register(REG_TIME_SEC_DOW, (now.second << 8) | dow)
        instrument.write_register(REG_TIME_MONTH_DAY, (now.month << 8) | now.day)
        instrument.write_register(REG_TIME_YEAR, ((now.year - 2000) << 8) | 0)

    # Read back after a short delay
    import time
    time.sleep(10)
    r_hrmin = instrument.read_register(REG_TIME_HR_MIN)
    r_secdow = instrument.read_register(REG_TIME_SEC_DOW)
    r_monthday = instrument.read_register(REG_TIME_MONTH_DAY)
    r_year = instrument.read_register(REG_TIME_YEAR)

    print(f"Read back: E0={r_hrmin}, E1={r_secdow}, E2={r_monthday}, E3={r_year}")
    print("Done.")


if __name__ == "__main__":
    main()
