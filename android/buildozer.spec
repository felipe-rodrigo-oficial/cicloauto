[app]
title = CicloAuto
package.name = cicloauto
package.domain = org.cicloauto
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,ttf
version = 0.1
requirements = python3,kivy==2.3.0,plyer,pyjnius
orientation = landscape
fullscreen = 1

android.permissions = ACCESS_FINE_LOCATION,ACCESS_COARSE_LOCATION,WAKE_LOCK
android.api = 34
android.minapi = 24
android.archs = arm64-v8a, armeabi-v7a
android.accept_sdk_license = True

[buildozer]
log_level = 2
warn_on_root = 1
