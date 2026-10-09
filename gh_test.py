"""
Guitar Hero dongle HID capture — etiketli kayıt.

Kullanım:
  py -m pip install hidapi
  py gh_test.py

Kontroller:
  Enter          → son report'u etikete kaydet (önce etiket yaz)
  q + Enter      → çık
  sadece Enter   → etiket sor (interaktif)

Örnek oturum:
  (gitar boşta) → BOŞ yaz → Enter
  Green basılı   → GREEN yaz → Enter
  ...
"""

from __future__ import annotations

import sys
import threading
import time
from datetime import datetime
from pathlib import Path

import hid

VID = 0x12BA
PID = 0x0100
REPORT_SIZE = 64
CAPTURE_FILE = Path(__file__).with_name("captures.txt")

# Son okunan report (thread-safe basit paylaşımlı)
_last_raw: list[int] | None = None
_last_hex: str = ""
_lock = threading.Lock()
_running = True


def fmt_hex(data: list[int] | bytes) -> str:
    return " ".join(f"{b:02X}" for b in data)


def save_capture(label: str, data: list[int], note: str = "") -> None:
    label = label.strip().upper() or "UNLABELED"
    line = f"{label}: {fmt_hex(data)}"
    if note:
        line += f"  # {note}"
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    block = f"[{stamp}]\n{line}\n\n"

    with CAPTURE_FILE.open("a", encoding="utf-8") as f:
        f.write(block)

    print(f"  ✓ kaydedildi → {CAPTURE_FILE.name}")
    print(f"    {line}")


def reader_loop(device: hid.device) -> None:
    global _last_raw, _last_hex, _running
    prev_print: list[int] | None = None

    while _running:
        data = device.read(REPORT_SIZE)
        if data:
            with _lock:
                _last_raw = list(data)
                _last_hex = fmt_hex(data)
                changed = data != prev_print
                snap = _last_hex
            if changed:
                print(f"  live: {snap}")
                prev_print = list(data)
        else:
            time.sleep(0.002)


def main() -> None:
    global _running

    print("Guitar Hero dongle aranıyor...")
    devices = hid.enumerate(VID, PID)
    for d in devices:
        print("Bulundu:")
        for k in ("path", "vendor_id", "product_id", "product_string", "serial_number", "interface_number"):
            if k in d:
                print(f"  {k}: {d[k]}")

    if not devices:
        raise SystemExit("Dongle bulunamadı. Takılı olduğundan emin ol.")

    device = hid.device()
    device.open(VID, PID)
    device.set_nonblocking(True)

    print("\nDongle açıldı.")
    print(f"Kayıt dosyası: {CAPTURE_FILE}")
    print("Gitarı eşleştir. Report değişince 'live:' satırları gelir.\n")
    print("Etiket kaydı:")
    print("  Etiket yazıp Enter  → o anki son report kaydedilir")
    print("  Örnekler: BOŞ, GREEN, RED, YELLOW, BLUE, ORANGE,")
    print("            STRUM_UP, STRUM_DOWN, WHAMMY_MIN, WHAMMY_MAX")
    print("  q                 → çık\n")

    t = threading.Thread(target=reader_loop, args=(device,), daemon=True)
    t.start()

    try:
        while True:
            try:
                label = input("etiket> ").strip()
            except EOFError:
                break

            if not label:
                continue
            if label.lower() in {"q", "quit", "exit"}:
                break

            with _lock:
                data = _last_raw
                hx = _last_hex

            if not data:
                print("  henüz report yok — gitarı bağla / bir tuşa bas, tekrar dene")
                continue

            print(f"  son report: {hx}")
            save_capture(label, data)

    except KeyboardInterrupt:
        print("\n(Ctrl+C)")
    finally:
        _running = False
        device.close()
        print("Kapandı.")


if __name__ == "__main__":
    main()
