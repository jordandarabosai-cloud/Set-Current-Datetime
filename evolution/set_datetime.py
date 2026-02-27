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

    reg14 = pack(now.hour, now.minute)            # 0x000E
    reg15 = pack(now.month, now.day)              # 0x000F
    # genmon sets day-of-week to 0 when writing time
    reg16 = pack(0, now.year % 100)   # 0x0010

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

    # Write three registers at once (matches genmon behavior)
    try:
        result = client.write_registers(address=14, values=[reg14, reg15, reg16], unit=SLAVE_ID)
        if result.isError():
            print("Write error (no response). Will verify by reading back...")
    except Exception as exc:
        print("Write exception (no response). Will verify by reading back...", exc)

    # Read back to verify
    import time
    time.sleep(1.5)

    # Reconnect before readback (some adapters get stuck after write)
    client.close()
    time.sleep(0.2)
    client = ModbusSerialClient(
        port=PORT,
        baudrate=BAUD,
        parity=PARITY,
        stopbits=STOPBITS,
        bytesize=8,
        timeout=2
    )
    client.connect()

    try:
        r14 = r15 = r16 = None
        last_err = None
        for attempt in range(3):
            rr14 = client.read_holding_registers(14, 1, unit=SLAVE_ID)
            rr15 = client.read_holding_registers(15, 1, unit=SLAVE_ID)
            rr16 = client.read_holding_registers(16, 1, unit=SLAVE_ID)

            if rr14.isError() or rr15.isError() or rr16.isError():
                last_err = (rr14, rr15, rr16)
                time.sleep(0.5)
                continue

            r14 = rr14.registers[0]
            r15 = rr15.registers[0]
            r16 = rr16.registers[0]
            last_err = None
            break

        if last_err is not None:
            print("Readback failed:", *last_err)
        elif r14 == reg14 and r15 == reg15 and r16 == reg16:
            print(f"Set time to {now} (reg14={reg14}, reg15={reg15}, reg16={reg16})")
        else:
            print("Write did not take effect.")
            print(f"Read back: reg14={r14}, reg15={r15}, reg16={r16}")
    except Exception as exc:
        print("Readback failed:", exc)

    client.close()


if __name__ == "__main__":
    main()
