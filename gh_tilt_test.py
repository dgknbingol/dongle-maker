"""
Guitar Hero GH5 PS3 dongle - continuous HID / tilt capture.

Amaç:
- Gelen her DEĞİŞEN HID reportunu kaydetmek
- Gitar hareket ettirilirken hangi byte'ların değiştiğini bulmak

Kullanım:
    py -m pip install hidapi
    py gh_tilt_test.py

Test:
1. Gitarı masaya bırak.
2. Programı çalıştır.
3. 10 saniye hiç dokunma.
4. Green'e bas/bırak (gitarı hareket ettirme).
5. 5 saniye bekle.
6. Gitarı yavaşça kaldır:
      yatay -> 30° -> 60° -> 90°
7. Tekrar masaya bırak.
8. Enter'a basarak programı bitir.

Çıktı:
    tilt_capture.txt
"""

from __future__ import annotations

import threading
import time
from datetime import datetime
from pathlib import Path

import hid


VID = 0x12BA
PID = 0x0100
REPORT_SIZE = 64

CAPTURE_FILE = Path(__file__).with_name("tilt_capture.txt")

_running = True
_start_time = 0.0

_last_report: list[int] | None = None
_previous_report: list[int] | None = None

_lock = threading.Lock()


def fmt_hex(data: list[int] | bytes) -> str:
    return " ".join(f"{b:02X}" for b in data)


def changed_bytes(
    previous: list[int] | None,
    current: list[int],
) -> str:

    if previous is None:
        return "INITIAL"

    changes = []

    max_len = max(len(previous), len(current))

    for i in range(max_len):

        old = previous[i] if i < len(previous) else None
        new = current[i] if i < len(current) else None

        if old != new:

            old_text = "--" if old is None else f"{old:02X}"
            new_text = "--" if new is None else f"{new:02X}"

            changes.append(
                f"B{i}[{old_text}->{new_text}]"
            )

    if not changes:
        return "-"

    return " ".join(changes)


def save_report(
    elapsed: float,
    report: list[int],
    changes: str,
) -> None:

    timestamp = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S.%f"
    )[:-3]

    line = (
        f"[{timestamp}] "
        f"+{elapsed:09.3f}s "
        f"{fmt_hex(report)} "
        f"| {changes}"
    )

    with CAPTURE_FILE.open(
        "a",
        encoding="utf-8"
    ) as f:
        f.write(line + "\n")

    print(line)


def reader_loop(device: hid.device) -> None:

    global _running
    global _last_report
    global _previous_report

    while _running:

        data = device.read(REPORT_SIZE)

        if not data:
            time.sleep(0.001)
            continue

        current = list(data)

        with _lock:

            _last_report = current

            # Aynı report tekrar tekrar geliyorsa yazma
            if (
                _previous_report is not None
                and current == _previous_report
            ):
                continue

            changes = changed_bytes(
                _previous_report,
                current,
            )

            elapsed = time.perf_counter() - _start_time

            save_report(
                elapsed,
                current,
                changes,
            )

            _previous_report = current


def main() -> None:

    global _running
    global _start_time

    print()
    print("========================================")
    print(" Guitar Hero GH5 - TILT CAPTURE")
    print("========================================")
    print()

    devices = hid.enumerate(VID, PID)

    if not devices:
        raise SystemExit(
            "Dongle bulunamadı."
        )

    print(
        f"Dongle bulundu: "
        f"VID={VID:04X} PID={PID:04X}"
    )

    for d in devices:

        print(
            "Product:",
            d.get("product_string")
        )

        print(
            "Path:",
            d.get("path")
        )

    device = hid.device()

    device.open(
        VID,
        PID
    )

    device.set_nonblocking(True)

    # Eski capture dosyasını temizle
    CAPTURE_FILE.write_text(
        "",
        encoding="utf-8"
    )

    print()
    print(
        f"Capture dosyası: {CAPTURE_FILE}"
    )

    print()
    print("TEST SIRASI:")
    print()
    print("  0-10 sn : MASADA, DOKUNMA")
    print(" 10-15 sn : GREEN BAS / BIRAK")
    print(" 15-20 sn : DOKUNMA")
    print(" 20+ sn   : GITARI YAVASCA KALDIR")
    print()
    print("             0°")
    print("             30°")
    print("             60°")
    print("             90°")
    print()
    print("Sonra tekrar masaya bırak.")
    print()
    print("Bitirmek için ENTER.")
    print()

    _start_time = time.perf_counter()

    thread = threading.Thread(
        target=reader_loop,
        args=(device,),
        daemon=True,
    )

    thread.start()

    try:

        input()

    except KeyboardInterrupt:

        pass

    finally:

        _running = False

        thread.join(
            timeout=1.0
        )

        device.close()

    print()
    print("========================================")
    print(" CAPTURE TAMAMLANDI")
    print("========================================")
    print()

    print(
        f"Dosya: {CAPTURE_FILE}"
    )


if __name__ == "__main__":
    main()