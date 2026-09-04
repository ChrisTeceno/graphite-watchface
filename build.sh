#!/usr/bin/env bash
# Build, sign and (optionally) install the Graphite watch face.
#
# A Watch Face Format bundle is resources only (hasCode=false), so there is
# nothing for Gradle or AGP to do. aapt2 + apksigner from the SDK build-tools
# is the whole toolchain, which keeps the build fast and free of AGP version
# pinning.
#
#   ./build.sh              build only
#   ./build.sh install      build, then install on the running emulator/watch
#   ./build.sh install -s emulator-5556
set -euo pipefail

cd "$(dirname "$0")"

SDK="${ANDROID_HOME:-$HOME/Library/Android/sdk}"
BUILD_TOOLS="$SDK/build-tools/36.0.0"
ANDROID_JAR="$SDK/platforms/android-36/android.jar"
KEYSTORE="$HOME/.android/debug.keystore"

MIN_SDK=34      # WFF v2, so Wear OS 5 and up
TARGET_SDK=36

OUT="build"
APK="$OUT/graphite.apk"
PACKAGE="com.teceno.watchface.graphite"

for f in "$BUILD_TOOLS/aapt2" "$BUILD_TOOLS/zipalign" "$BUILD_TOOLS/apksigner" "$ANDROID_JAR"; do
  [ -e "$f" ] || { echo "missing: $f" >&2; exit 1; }
done

if [ ! -f "$KEYSTORE" ]; then
  echo "==> creating debug keystore"
  mkdir -p "$(dirname "$KEYSTORE")"
  keytool -genkeypair -v -keystore "$KEYSTORE" -storepass android -keypass android \
    -alias androiddebugkey -keyalg RSA -keysize 2048 -validity 10950 \
    -dname "CN=Android Debug,O=Android,C=US" >/dev/null
fi

rm -rf "$OUT"
mkdir -p "$OUT"

echo "==> compiling resources"
"$BUILD_TOOLS/aapt2" compile --dir src/res -o "$OUT/res.zip"

echo "==> linking"
"$BUILD_TOOLS/aapt2" link \
  -o "$OUT/unsigned.apk" \
  --manifest src/AndroidManifest.xml \
  -I "$ANDROID_JAR" \
  --min-sdk-version "$MIN_SDK" \
  --target-sdk-version "$TARGET_SDK" \
  --auto-add-overlay \
  "$OUT/res.zip"

echo "==> aligning and signing"
"$BUILD_TOOLS/zipalign" -f -p 4 "$OUT/unsigned.apk" "$OUT/aligned.apk"
"$BUILD_TOOLS/apksigner" sign \
  --ks "$KEYSTORE" --ks-pass pass:android --key-pass pass:android \
  --ks-key-alias androiddebugkey \
  --out "$APK" "$OUT/aligned.apk"

# The WFF runtime reads res/raw/watchface.xml with openRawResource(), so it has
# to survive packaging as plain text. Fail loudly if aapt2 ever binary-encodes it.
packaged_xml=$(unzip -p "$APK" res/raw/watchface.xml)
case "$packaged_xml" in
  '<?xml'*"<WatchFace"*) ;;
  *) echo "ERROR: res/raw/watchface.xml is not plain XML in the APK" >&2; exit 1 ;;
esac

echo "==> built $APK ($(du -h "$APK" | cut -f1))"

if [ "${1:-}" = "install" ]; then
  shift
  echo "==> installing"
  adb "$@" install -r "$APK"
  echo "==> installed. Pick it from the watch face carousel, or run:"
  # --es watchFaceId, not --ecn component: a WFF face declares no service of its
  # own, so naming one fails with "Watch face package is not installed".
  echo "    adb $* shell am broadcast -a com.google.android.wearable.app.DEBUG_SURFACE --es operation set-watchface --es watchFaceId $PACKAGE"
fi
