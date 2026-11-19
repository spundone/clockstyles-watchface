#!/bin/sh
# Builds and signs the Clock Styles watch face APK into out/clockstyles.apk
set -e
cd "$(dirname "$0")"
SDK="${ANDROID_HOME:-$HOME/Library/Android/sdk}"
BT="$SDK/build-tools/34.0.0"
JAR="$SDK/platforms/android-34/android.jar"
mkdir -p out && rm -f out/*.apk out/*.idsig out/res.zip
"$BT/aapt2" compile --dir res -o out/res.zip
"$BT/aapt2" link -o out/unsigned.apk -I "$JAR" --manifest AndroidManifest.xml \
  --min-sdk-version 33 --target-sdk-version 34 --version-code "${VERSION_CODE:-1}" --version-name "${VERSION_NAME:-1.0}" out/res.zip
"$BT/zipalign" -p -f 4 out/unsigned.apk out/aligned.apk
[ -f clockstyles.jks ] || keytool -genkeypair -keystore clockstyles.jks -alias clockstyles -keyalg RSA -keysize 2048 -validity 10000 \
  -storepass clockstyles -keypass clockstyles -dname "CN=Clock Styles watch face"
"$BT/apksigner" sign --ks clockstyles.jks --ks-pass pass:clockstyles --ks-key-alias clockstyles --out out/clockstyles.apk out/aligned.apk
echo "built out/clockstyles.apk"
