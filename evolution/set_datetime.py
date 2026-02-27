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


def pack(hi, lo):
    return (hi << 8) | lo


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


def main():
    label, tz = pick_timezone()
    now = datetime.now(ZoneInfo(tz))

    # align to the top of the minute (seconds = 0), like genmon
    while now.second != 0:
        import time
        time.sleep(60 - now.second)
        now = datetime.now(ZoneInfo(tz))

    print(f"
Using timezone: {label} ({tz})")
    print(f"Target datetime: {now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    confirm = input("Write this time to controller? (yes/no): ").strip().lower()
    if confirm not in ("y", "yes"):
        print("Cancelled.")
        return

    reg14 = pack(now.hour, now.minute)            # 0x000E
    reg15 = pack(now.month, now.day)              # 0x000F
    reg16 = pack(0, now.year % 100)               # 0x0010 (dow=0 per genmon)

    instrument = minimalmodbus.Instrument(PORT, SLAVE_ID)
    instrument.serial.baudrate = BAUD
    instrument.serial.parity = PARITY
    instrument.serial.stopbits = STOPBITS
    instrument.serial.timeout = 2

    # Write all three registers at once (FC16)
    instrument.write_registers(14, [reg14, reg15, reg16])

    # Read back after a short delay
    import time
    time.sleep(10)
    r14 = instrument.read_register(14)
    r15 = instrument.read_register(15)
    r16 = instrument.read_register(16)

    if r14 == reg14 and r15 == reg15 and r16 == reg16:
        print(f"Set time to {now} (reg14={reg14}, reg15={reg15}, reg16={reg16})")
    else:
        print("Write may not have taken effect.")
        print(f"Read back: reg14={r14}, reg15={r15}, reg16={r16}")


if __name__ == "__main__":
    main()
