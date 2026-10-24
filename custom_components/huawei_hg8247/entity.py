"""Base entity for the router itself."""

from __future__ import annotations

from homeassistant.const import CONF_HOST
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity, DataUpdateCoordinator

from . import HuaweiHG8247ConfigEntry
from .const import DOMAIN


class HuaweiHG8247Entity(CoordinatorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator: DataUpdateCoordinator, entry: HuaweiHG8247ConfigEntry, key: str) -> None:
        super().__init__(coordinator)
        status = entry.runtime_data.status.data
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_translation_key = key
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Huawei HG8247",
            manufacturer="Huawei",
            model=status.model,
            serial_number=status.serial,
            hw_version=status.hardware_version,
            sw_version=status.software_version,
            configuration_url=f"https://{entry.data[CONF_HOST]}",
        )
