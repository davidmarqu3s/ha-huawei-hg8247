"""Router reboot."""

from __future__ import annotations

from homeassistant.components.button import ButtonDeviceClass, ButtonEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import HuaweiHG8247ConfigEntry
from .api import HuaweiHG8247Error
from .entity import HuaweiHG8247Entity


async def async_setup_entry(
    hass: HomeAssistant, entry: HuaweiHG8247ConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    async_add_entities([RebootButton(entry.runtime_data.status, entry, "reboot")])


class RebootButton(HuaweiHG8247Entity, ButtonEntity):
    _attr_device_class = ButtonDeviceClass.RESTART
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator, entry: HuaweiHG8247ConfigEntry, key: str) -> None:
        super().__init__(coordinator, entry, key)
        self._client = entry.runtime_data.client

    async def async_press(self) -> None:
        try:
            await self._client.async_reboot()
        except HuaweiHG8247Error as err:
            raise HomeAssistantError(f"Reboot failed: {err}") from err
