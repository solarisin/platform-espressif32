# pioarduino (p)eople (i)nitiated (o)ptimized (arduino)

[![Build Status](https://github.com/pioarduino/platform-espressif32/actions/workflows/examples.yml/badge.svg)](https://github.com/pioarduino/platform-espressif32/actions)
[![Discord](https://img.shields.io/discord/1263397951829708871.svg?logo=discord&logoColor=white&color=5865F2&label=Discord)](https://discord.gg/Nutz9crnZr)
[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/pioarduino/platform-espressif32)
[![GitHub Releases](https://img.shields.io/github/downloads/pioarduino/platform-espressif32/total?label=downloads)](https://github.com/pioarduino/platform-espressif32/releases/latest)

Espressif Systems is a privately held, fabless semiconductor company renowned for delivering cost-effective wireless communication microcontrollers. Their innovative solutions are widely adopted in mobile devices and Internet of Things (IoT) applications around the globe.

## General
* Issues with boards (wrong / missing). All issues caused from boards will not be fixed from the maintainer(s). A PR needs to be provided against branch `develop` to solve.
* No support for the Arduino Nora Nano board, issues needs to be solved by the community
## IDE Preparation
Prerequisites:
-	Python >= 3.10 is required for pioarduino to function properly.

## Installation
- [Download and install Microsoft Visual Studio Code](https://code.visualstudio.com/). pioarduino IDE is on top of it.
- Open the extension manager.
- Search for the `pioarduino ide` extension.
- Install pioarduino IDE extension.

## Usage
1. Setup new VSCode pioarduino project.
1. Configure a platform option in platformio.ini file:

## Documentation
[pioarduino Wiki](https://deepwiki.com/pioarduino/platform-espressif32)
The Wiki is AI generated and insane detailed and accurate.

### Stable Arduino
currently espressif Arduino 3.3.0 and IDF 5.5.0

```ini
[env:stable]
platform = https://github.com/pioarduino/platform-espressif32/releases/download/stable/platform-espressif32.zip
board = ...
...
```

### Development Arduino
espressif Arduino repo branch master and latest compiled Arduino libs

```ini
[env:development]
platform = https://github.com/pioarduino/platform-espressif32.git#develop
board = ...
...
```

### ESP32-solo1 and ESP32-C2 Arduino support (with pioarduino only feature: *Hybrid compile*)
Example configuration:

```ini
[env:esp32solo1]
platform = https://github.com/pioarduino/platform-espressif32/releases/download/stable/platform-espressif32.zip
framework = arduino
board = esp32-solo1
monitor_speed = 115200

[env:esp32-c2-devkitm-1]
platform = https://github.com/pioarduino/platform-espressif32/releases/download/stable/platform-espressif32.zip
framework = arduino
board = esp32-c2-devkitm-1
monitor_speed = 115200
```

Looking for sponsor button? There is none. If you want to donate, please spend a litte to a charity organization.
