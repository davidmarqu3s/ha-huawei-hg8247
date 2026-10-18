# Huawei HG8247 for Home Assistant

Local presence detection, fibre signal and router health for Huawei HG8247 fibre routers, read from the router's own web interface.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

## Features

- **Presence without phone battery**: device trackers for the phones you pick, home while the router sees them online, refreshed every 30 s.
- **Fibre line health**: receive and transmit power (dBm), optical module temperature and a loss-of-signal sensor, so a degrading line shows up before it drops.
- **Router status**: CPU and memory usage, last boot time, firmware and hardware version, and a count of connected devices.
- **Remote reboot**: a restart button for automations or the dashboard.
- **Lockout-safe login**: polling stops and Home Assistant asks for the password again after a rejected login, instead of retrying into the router's lockout.

Internet status, public IP and traffic come from Home Assistant's built-in [UPnP/IGD](https://www.home-assistant.io/integrations/upnp/) integration, which discovers these routers automatically.

## Install

**HACS:** add this repository as a custom repository (type *Integration*), install **Huawei HG8247**, then restart Home Assistant.

**Manual:** copy `custom_components/huawei_hg8247` into your Home Assistant `config/custom_components/` folder and restart.

## Use

1. Settings → Devices & services → Add integration → **Huawei HG8247**.
2. Enter the router address (usually `192.168.1.1`) and the admin login from the label on the router.
3. Open **Configure** and pick the devices to track, then add each tracker to its person.

Phones need a fixed Wi-Fi address for tracking to stay matched: on iPhone, Settings → Wi-Fi → your network → Private Wi-Fi Address → **Fixed**.

## Limitations

- The router allows one admin session at a time, so opening its web page while the integration polls can log you out. Disable the integration while you work in the router's web interface.
- Tested on the HG8247B7-8N with Vodafone Portugal firmware (V5R024C00S114). Other firmware may use different pages.
- A phone that sleeps off Wi-Fi shows as away on the router; Home Assistant then falls back to the person's other trackers, such as the Companion app.

## Development

```sh
pip install aiohttp pytest
pytest tests
```

## Licence

[MIT](LICENSE)
