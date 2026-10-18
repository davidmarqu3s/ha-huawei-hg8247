"""Fibre signal status."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import HuaweiHG8247ConfigEntry
from .entity import HuaweiHG8247Entity


async def async_setup_entry(
    hass: HomeAssistant, entry: HuaweiHG8247ConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    async_add_entities([FibreSignalSensor(entry.runtime_data.status, entry, "fibre_signal")])


class FibreSignalSensor(HuaweiHG8247Entity, BinarySensorEntity):
    """On while the ONT receives light from the fibre (no loss of signal)."""

    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

    @property
    def is_on(self) -> bool | None:
        return self.coordinator.data.fibre_signal
