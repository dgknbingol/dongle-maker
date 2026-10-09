from pathlib import Path
import re
from collections import Counter

path = Path(__file__).with_name("tilt_capture.txt")
text = path.read_text(encoding="utf-8", errors="replace")

# Format: [ts] +00000.007s 00 00 0F ... | comment
pat = re.compile(
    r"\+(\d+\.\d+)s\s+((?:[0-9A-Fa-f]{2}\s+)+)\|?\s*(.*)$"
)

rows = []
for line in text.splitlines():
    m = pat.search(line)
    if not m:
        continue
    t = float(m.group(1))
    hexes = m.group(2).split()
    note = m.group(3).strip()
    rows.append((t, [int(x, 16) for x in hexes], note))

print("parsed:", len(rows))
if not rows:
    raise SystemExit("no rows")

lens = Counter(len(r[1]) for r in rows)
print("report lengths:", lens.most_common())
L = lens.most_common(1)[0][0]
rows = [(t, r[:L], n) for t, r, n in rows if len(r) >= L]

print("\nChanging bytes across full capture:")
for i in range(L):
    vals = [r[i] for _, r, _ in rows]
    uniq = sorted(set(vals))
    if len(uniq) == 1:
        continue
    print(
        f"  [{i:2d}] range={min(vals):02X}-{max(vals):02X} "
        f"unique={len(uniq):4d}  sample={['%02X'%v for v in uniq[:12]]}"
    )

# Classic analog bytes 3-6 around 0x80
print("\nAnalog-ish bytes (3-6) over time:")
N = max(1, len(rows) // 40)
for i in range(0, len(rows), N):
    t, r, n = rows[i]
    print(
        f"  t={t:7.2f}s  "
        f"b0={r[0]:02X} b1={r[1]:02X} b2={r[2]:02X} "
        f"b3={r[3]:02X} b4={r[4]:02X} b5={r[5]:02X} b6={r[6]:02X} "
        f"b19={r[19]:02X} b20={r[20]:02X}  {n[:40]}"
    )

# Find when byte 3-6 leave 0x80
print("\nEvents where b3/b4/b5/b6 != 0x80:")
count = 0
for t, r, n in rows:
    if any(r[i] != 0x80 for i in (3, 4, 5, 6)):
        print(
            f"  t={t:7.2f}s  "
            f"{' '.join(f'{b:02X}' for b in r)}  | {n}"
        )
        count += 1
        if count >= 30:
            print("  ... (truncated)")
            break
print(f"total non-0x80 analog events: "
      f"{sum(1 for _,r,_ in rows if any(r[i]!=0x80 for i in (3,4,5,6)))}")

# b19/b20 pattern
print("\nb19/b20 unique pairs (top):")
pairs = Counter((r[19], r[20]) for _, r, _ in rows)
for (a, b), c in pairs.most_common(10):
    print(f"  {a:02X} {b:02X}  count={c}")

# Notes mentioning B3-B6
print("\nNotes that mention B3/B4/B5/B6:")
for t, r, n in rows:
    if re.search(r"B[3456]\[", n):
        print(f"  t={t:7.2f}s {n} -> {' '.join(f'{b:02X}' for b in r[:7])}")
