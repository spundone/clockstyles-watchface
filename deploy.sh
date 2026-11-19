#!/bin/sh
# Installs out/clockstyles.apk on the watch, makes it the active face, and saves a screenshot to out/shot.png.
# Finds the watch by model, since its wireless-debugging port changes.
set -e
cd "$(dirname "$0")"
S=$(adb devices -l | awk '/ device .*model:SM_R96/{print $1; exit}')
[ -n "$S" ] || { echo "watch not connected: open Wireless debugging on it" >&2; exit 1; }
adb -s "$S" install -r out/clockstyles.apk | tail -1
adb -s "$S" shell am broadcast -a com.google.android.wearable.app.DEBUG_SURFACE \
  --es operation set-watchface --es watchFaceId dev.spundone.watchface.clockstyles | tail -1
sleep 10
adb -s "$S" shell input keyevent KEYCODE_WAKEUP
adb -s "$S" shell input keyevent KEYCODE_HOME
sleep 3
adb -s "$S" exec-out screencap -p > "out/${SHOT:-shot}.png"
echo "screenshot: out/${SHOT:-shot}.png"
