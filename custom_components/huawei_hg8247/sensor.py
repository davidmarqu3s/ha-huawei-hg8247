"""Router status sensors."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    EntityCategory,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from . import HuaweiHG8247ConfigEntry
from .api import RouterStatus
from .entity import HuaweiHG8247Entity


@dataclass(frozen=True, kw_only=True)
class StatusSensorDescription(SensorEntityDescription):
    value: Callable[[RouterStatus], float | int | datetime | None]


def _boot_time(status: RouterStatus) -> datetime | None:
    if status.uptime is None:
        return None
    # Rounded so the state doesn't change on every poll.
    boot = dt_util.utcnow() - timedelta(seconds=status.uptime)
    return boot.replace(second=0, microsecond=0)


STATUS_SENSORS = (
    StatusSensorDescription(
        key="rx_power", native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        device_class=SensorDeviceClass.SIGNAL_STRENGTH, state_class=SensorStateClass.MEASUREMENT,
        value=lambda s: s.optic["rx_power"],
    ),
    StatusSensorDescription(
        key="tx_power", native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        device_class=SensorDeviceClass.SIGNAL_STRENGTH, state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC, value=lambda s: s.optic["tx_power"],
    ),
    StatusSensorDescription(
        key="optic_temperature", native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE, state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC, value=lambda s: s.optic["temperature"],
    ),
    StatusSensorDescription(
        key="optic_voltage", native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE, state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC, entity_registry_enabled_default=False,
        value=lambda s: s.optic["voltage"],
    ),
    StatusSensorDescription(
        key="optic_bias_current", native_unit_of_measurement=UnitOfElectricCurrent.MILLIAMPERE,
        device_class=SensorDeviceClass.CURRENT, state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC, entity_registry_enabled_default=False,
        value=lambda s: s.optic["bias_current"],
    ),
    StatusSensorDescription(
        key="cpu", native_unit_of_measurement=PERCENTAGE, state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC, value=lambda s: s.cpu,
    ),
    StatusSensorDescription(
        key="memory", native_unit_of_measurement=PERCENTAGE, state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC, value=lambda s: s.memory,
    ),
    StatusSensorDescription(
        key="last_boot", device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC, value=_boot_time,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: HuaweiHG8247ConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    data = entry.runtime_data
    async_add_entities(
        [StatusSensor(data.status, entry, d) for d in STATUS_SENSORS]
        + [ConnectedDevicesSensor(data.devices, entry, "connected_devices")]
    )


class StatusSensor(HuaweiHG8247Entity, SensorEntity):
    entity_description: StatusSensorDescription

    def __init__(self, coordinator, entry, description: StatusSensorDescription) -> None:
        super().__init__(coordinator, entry, description.key)
        self.entity_description = description

    @property
    def native_value(self):
        return self.entity_description.value(self.coordinator.data)


class ConnectedDevicesSensor(HuaweiHG8247Entity, SensorEntity):
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "devices"

    @property
    def native_value(self) -> int:
        return sum(d.online for d in self.coordinator.data.values())
