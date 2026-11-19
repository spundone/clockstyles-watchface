#!/bin/sh
# Screenshots each style to out/styleN.png: builds the face with only that style (gen.py --only N),
# installs it, keeps the screen awake while the face loads, and refuses to shoot if the watch is locked.
# Usage: [GENARGS=--amb SUFFIX=_amb] tools/shoot_styles.sh [N ...]   (default: all styles). Restores the full build at the end.
set -e
cd "$(dirname "$0")/.."
S=$(adb devices -l | awk '/ device .*model:SM_R96/{print $1; exit}')
[ -n "$S" ] || { echo "watch not connected" >&2; exit 1; }
awake() { i=0; while [ $i -lt "$1" ]; do adb -s "$S" shell input keyevent KEYCODE_WAKEUP; sleep 2; i=$((i + 1)); done; }
locked() { adb -s "$S" shell dumpsys window | grep -q 'isKeyguardShowing=true'; }
for n in ${@:-0 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16}; do
  locked && { echo "watch is locked; unlock it and rerun" >&2; exit 2; }
  ./gen.py --only "$n" $GENARGS >/dev/null
  VERSION_CODE=$(date +%s) ./build.sh >/dev/null 2>&1
  adb -s "$S" install -r out/clockstyles.apk | tail -1
  sleep 3
  adb -s "$S" shell am broadcast -a com.google.android.wearable.app.DEBUG_SURFACE \
    --es operation set-watchface --es watchFaceId dev.spundone.watchface.clockstyles >/dev/null \
    || { sleep 3; adb -s "$S" shell am broadcast -a com.google.android.wearable.app.DEBUG_SURFACE \
    --es operation set-watchface --es watchFaceId dev.spundone.watchface.clockstyles >/dev/null; }
  awake 5
  adb -s "$S" shell input keyevent KEYCODE_HOME
  awake 1
  locked && { echo "watch locked during style $n" >&2; exit 2; }
  adb -s "$S" exec-out screencap -p > "out/style$n$SUFFIX.png"
  echo "out/style$n$SUFFIX.png"
done
./gen.py >/dev/null
