[app]
title = Jarvis AI
package.name = jarvis
package.domain = org.celik.jarvis
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json

version = 2.0

# Gerekli Python kütüphaneleri
requirements = python3,kivy,requests,urllib3,charset-normalizer,idna,certifi,pyjnius

orientation = portrait
fullscreen = 0

# Android Yetkileri ve Paket Erişimi
android.permissions = INTERNET,ACCESS_NETWORK_STATE,QUERY_ALL_PACKAGES

# Android SDK / API
android.api = 33
android.minapi = 21
android.ndk = 25b
android.archs = arm64-v8a
android.accept_sdk_license = True

[buildozer]
log_level = 2
warn_on_root = 1
