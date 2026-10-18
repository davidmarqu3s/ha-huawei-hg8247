"""Router-based presence for selected devices."""

from __future__ import annotations

from homeassistant.components.device_tracker import ScannerEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import HuaweiHG8247ConfigEntry
from .const import CONF_TRACKED


async def async_setup_entry(
    hass: HomeAssistant, entry: HuaweiHG8247ConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    coordinator = entry.runtime_data.devices
    names = entry.options.get(CONF_TRACKED, {})
    async_add_entities(HuaweiHG8247Tracker(coordinator, mac, name) for mac, name in names.items())


class HuaweiHG8247Tracker(CoordinatorEntity, ScannerEntity):
    """A device on the router's LAN table, home while the router reports it online."""

    def __init__(self, coordinator, mac: str, name: str) -> None:
        super().__init__(coordinator)
        self._mac = mac
        self._attr_name = name
        self._attr_unique_id = f"huawei_hg8247_{mac}"

    @property
    def _device(self):
        return self.coordinator.data.get(self._mac)

    @property
    def is_connected(self) -> bool:
        return bool(self._device and self._device.online)

    @property
    def mac_address(self) -> str:
        return self._mac

    @property
    def ip_address(self) -> str | None:
        return self._device.ip if self._device else None

    @property
    def hostname(self) -> str | None:
        return self._device.hostname if self._device else None
