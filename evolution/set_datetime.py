#!/usr/bin/env python3
from datetime import datetime
try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo
try:
    from pymodbus.client import ModbusSerialClient
except ImportError:
    from pymodbus.client.sync import ModbusSerialClient

PORT = "/dev/USB232"
SLAVE_ID = 157
BAUD = 9600
PARITY = "N"
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


def dow_sun0(dt):
    # Python: Monday=0..Sunday=6; we need Sunday=0..Saturday=6
    return (dt.weekday() + 1) % 7


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

    print(f"\nUsing timezone: {label} ({tz})")
    print(f"Target datetime: {now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    confirm = input("Write this time to controller? (yes/no): ").strip().lower()
    if confirm not in ("y", "yes"):
        print("Cancelled.")
        return

    reg14 = pack(now.hour, now.minute)            # 0x000E
    reg15 = pack(now.month, now.day)              # 0x000F
    reg16 = pack(dow_sun0(now), now.year % 100)   # 0x0010

    client = ModbusSerialClient(
        port=PORT,
        baudrate=BAUD,
        parity=PARITY,
        stopbits=STOPBITS,
        bytesize=8,
        timeout=2
    )

    if not client.connect():
        print("Failed to connect to serial port")
        return

    result = client.write_registers(address=14, values=[reg14, reg15, reg16], unit=SLAVE_ID)
    if result.isError():
        print("Write error:", result)
    else:
        print(f"Set time to {now} (reg14={reg14}, reg15={reg15}, reg16={reg16})")

    client.close()


if __name__ == "__main__":
    main()
