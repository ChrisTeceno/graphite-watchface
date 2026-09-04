#!/usr/bin/env bash
# Capture the running watch face and write it to src/res/drawable/preview.png.
#
# The picker and Play both show this image, so it should be the real face
# rather than a mockup. Set the face as active first, then:
#
#   tools/grab_preview.sh                    first device adb finds
#   tools/grab_preview.sh emulator-5554      a specific one
#
# Pin the serial whenever anything else is adb-connected: a Google TV Streamer
# on the network shares the adb server and will happily answer instead.
set -euo pipefail

cd "$(dirname "$0")/.."

SERIAL="${1:-}"
ADB=(adb)
[ -n "$SERIAL" ] && ADB=(adb -s "$SERIAL")

OUT="src/res/drawable/preview.png"
RAW="$(mktemp -t wfpreview).png"
trap 'rm -f "$RAW"' EXIT

"${ADB[@]}" exec-out screencap -p > "$RAW"

# The virtual canvas is 450x450; devices are 384 (41mm) or 454/456 (45mm).
python3 - "$RAW" "$OUT" <<'PY'
import sys

from PIL import Image, ImageDraw

src, dst = sys.argv[1], sys.argv[2]
img = Image.open(src).convert("RGB")
w, h = img.size
side = min(w, h)
img = img.crop(((w - side) // 2, (h - side) // 2,
                (w - side) // 2 + side, (h - side) // 2 + side))
img = img.resize((450, 450), Image.LANCZOS)

# Wear OS paints its own unread-notification indicator low and centred, over
# the top of the face. It is system chrome, not part of the design, so it does
# not belong in the preview the picker shows. The face itself draws nothing
# below y=388, so blanking this strip is safe; revisit if that ever changes.
ImageDraw.Draw(img).rectangle((205, 408, 245, 440), fill=(0, 0, 0))

img.save(dst)
print(f"wrote {dst} from a {w}x{h} capture")
PY
