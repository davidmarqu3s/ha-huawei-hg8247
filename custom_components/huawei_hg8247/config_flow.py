"""Config flow for the Huawei HG8247 integration."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import callback
from homeassistant.helpers import selector

from . import create_client
from .api import HuaweiHG8247AuthError, HuaweiHG8247Error
from .const import CONF_CERTIFICATE_FINGERPRINT, CONF_TRACKED, DEFAULT_HOST, DOMAIN


async def _validate(hass, data: dict) -> str | None:
    try:
        await create_client(hass, data).async_get_devices()
    except HuaweiHG8247AuthError:
        return "invalid_auth"
    except HuaweiHG8247Error:
        return "cannot_connect"
    return None


class HuaweiHG8247ConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors = {}
        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_HOST])
            self._abort_if_unique_id_configured()
            if not (error := await _validate(self.hass, user_input)):
                return self.async_create_entry(title="Huawei HG8247", data=user_input)
            errors["base"] = error
        schema = vol.Schema({
            vol.Required(CONF_HOST, default=DEFAULT_HOST): str,
            vol.Optional(CONF_CERTIFICATE_FINGERPRINT): str,
            vol.Required(CONF_USERNAME): str,
            vol.Required(CONF_PASSWORD): selector.TextSelector(
                selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
            ),
        })
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> ConfigFlowResult:
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        entry = self._get_reauth_entry()
        errors = {}
        if user_input is not None:
            data = {**entry.data, **entry.options, **user_input}
            if not (error := await _validate(self.hass, data)):
                return self.async_update_reload_and_abort(entry, data=data)
            errors["base"] = error
        schema = vol.Schema({
            vol.Required(CONF_USERNAME, default=entry.data[CONF_USERNAME]): str,
            vol.Required(CONF_PASSWORD): selector.TextSelector(
                selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
            ),
        })
        return self.async_show_form(step_id="reauth_confirm", data_schema=schema, errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry) -> OptionsFlow:
        return HuaweiHG8247OptionsFlow()


class HuaweiHG8247OptionsFlow(OptionsFlow):
    """Choose which LAN devices get a device tracker."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        current: dict[str, str] = self.config_entry.options.get(CONF_TRACKED, {})
        runtime = getattr(self.config_entry, "runtime_data", None)
        devices = runtime.devices.data if runtime else {}

        def label(mac: str) -> str:
            dev = devices.get(mac)
            if not dev:
                return f"{current.get(mac, mac)} ({mac}, not seen)"
            state = "online" if dev.online else "offline"
            return f"{dev.hostname or 'unnamed'} – {dev.ip} – {mac} – {state}"

        macs = sorted(set(devices) | set(current), key=lambda m: (not (devices.get(m) and devices[m].online), label(m).lower()))
        pin = self.config_entry.options.get(CONF_CERTIFICATE_FINGERPRINT,
            self.config_entry.data.get(CONF_CERTIFICATE_FINGERPRINT, ""))
        schema = vol.Schema({
            vol.Optional(CONF_CERTIFICATE_FINGERPRINT, default=pin): str,
            vol.Optional(CONF_TRACKED, default=list(current)): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[selector.SelectOptionDict(value=m, label=label(m)) for m in macs],
                    multiple=True,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            )
        })
        if user_input is not None:
            tracked = {}
            for mac in user_input.get(CONF_TRACKED, current):
                dev = devices.get(mac)
                tracked[mac] = current.get(mac) or (dev.hostname if dev and dev.hostname else mac)
            pin = user_input.get(CONF_CERTIFICATE_FINGERPRINT, "").strip()
            try:
                # Validate syntax without logging in; next reload validates the peer.
                create_client(self.hass, {**self.config_entry.data,
                    CONF_CERTIFICATE_FINGERPRINT: pin})
            except HuaweiHG8247Error:
                return self.async_show_form(step_id="init", data_schema=schema,
                    errors={CONF_CERTIFICATE_FINGERPRINT: "invalid_fingerprint"})
            return self.async_create_entry(data={CONF_TRACKED: tracked,
                CONF_CERTIFICATE_FINGERPRINT: pin})

        return self.async_show_form(step_id="init", data_schema=schema)
