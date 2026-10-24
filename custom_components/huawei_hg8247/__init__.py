"""The Huawei HG8247 integration."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import timedelta
import logging

import aiohttp

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import HuaweiHG8247AuthError, HuaweiHG8247Client, HuaweiHG8247Error, LanDevice, RouterStatus
from .const import CONF_CERTIFICATE_FINGERPRINT, DOMAIN, SCAN_INTERVAL, STATUS_INTERVAL

_LOGGER = logging.getLogger(__name__)
PLATFORMS = [Platform.BINARY_SENSOR, Platform.BUTTON, Platform.DEVICE_TRACKER, Platform.SENSOR]


@dataclass
class HuaweiHG8247Data:
    client: HuaweiHG8247Client
    devices: DataUpdateCoordinator[dict[str, LanDevice]]
    status: DataUpdateCoordinator[RouterStatus]


type HuaweiHG8247ConfigEntry = ConfigEntry[HuaweiHG8247Data]


def create_client(hass: HomeAssistant, data: dict) -> HuaweiHG8247Client:
    session = async_create_clientsession(hass, cookie_jar=aiohttp.DummyCookieJar())
    return HuaweiHG8247Client(session, data[CONF_HOST], data[CONF_USERNAME], data[CONF_PASSWORD], data.get(CONF_CERTIFICATE_FINGERPRINT))


def _coordinator(
    hass: HomeAssistant, entry: ConfigEntry, name: str, fetch: Callable[[], Awaitable], interval: timedelta
) -> DataUpdateCoordinator:
    async def _update():
        try:
            return await fetch()
        except HuaweiHG8247AuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except HuaweiHG8247Error as err:
            raise UpdateFailed(str(err)) from err

    return DataUpdateCoordinator(
        hass, _LOGGER, config_entry=entry, name=f"{DOMAIN} {name}",
        update_method=_update, update_interval=interval,
    )


async def async_setup_entry(hass: HomeAssistant, entry: HuaweiHG8247ConfigEntry) -> bool:
    client = create_client(hass, {**entry.data, **entry.options})
    # Both coordinators share the client, whose lock serialises the router's
    # single admin session.
    data = HuaweiHG8247Data(
        client=client,
        devices=_coordinator(hass, entry, "devices", client.async_get_devices, SCAN_INTERVAL),
        status=_coordinator(hass, entry, "status", client.async_get_status, STATUS_INTERVAL),
    )
    await data.devices.async_config_entry_first_refresh()
    await data.status.async_config_entry_first_refresh()
    entry.runtime_data = data
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_reload))
    return True


async def _reload(hass: HomeAssistant, entry: HuaweiHG8247ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: HuaweiHG8247ConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
