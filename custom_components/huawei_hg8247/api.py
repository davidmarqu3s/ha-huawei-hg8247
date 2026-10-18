"""Minimal client for the web interface of Huawei HG8247 ONTs."""

from __future__ import annotations

import asyncio
import base64
from dataclasses import dataclass
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
import re

import aiohttp
from yarl import URL

_DEVICE_RE = re.compile(r'new USERDevice\(((?:"(?:[^"\\]|\\.)*",?\s*)*)\)')
_ARG_RE = re.compile(r'"((?:[^"\\]|\\.)*)"')
_HEX_RE = re.compile(r"\\x([0-9a-fA-F]{2})")
_TOKEN_RE = re.compile(r'var token\s*=\s*"([0-9a-f]+)"')
_ONTTOKEN_RE = re.compile(r'name="onttoken" value="([0-9a-f]+)"')
_MODEL_RE = re.compile(r"\b(HG\w+(?:-\w+)?)")
_FIELDS = (
    "domain", "ip", "mac", "port", "ip_type", "dev_type", "status",
    "port_type", "time", "hostname",
)


class HuaweiHG8247Error(Exception):
    """The router could not be reached or returned something unexpected."""


class HuaweiHG8247AuthError(HuaweiHG8247Error):
    """The router rejected the credentials."""


@dataclass(frozen=True)
class LanDevice:
    mac: str
    ip: str
    hostname: str
    port: str
    online: bool


@dataclass(frozen=True)
class RouterStatus:
    model: str
    serial: str
    hardware_version: str
    software_version: str
    uptime: int | None
    cpu: int | None
    memory: int | None
    optic: dict[str, float | None]
    fibre_signal: bool | None


_OPTIC_FIELDS = ("tx_power", "rx_power", "voltage", "temperature", "bias_current")


def _number(value: str) -> float | None:
    try:
        return float(value.strip().rstrip("%"))
    except ValueError:
        return None


def _constructor_args(page: str, name: str) -> list[str]:
    match = re.search(rf'new {name}\(((?:"(?:[^"\\]|\\.)*",?\s*)*)\)', page)
    return [_unescape(a) for a in _ARG_RE.findall(match.group(1))] if match else []


def _quoted_var(page: str, name: str) -> str:
    match = re.search(rf"var {name}\s*=\s*'([^']*)'", page)
    return match.group(1) if match else ""


def parse_status(status_page: str, optic_page: str) -> RouterStatus:
    """Parse Status_ptvdf.asp and newvdfopticinfo.asp."""
    info = _constructor_args(status_page, "stDeviceInfo")
    if len(info) < 6:
        raise HuaweiHG8247Error("Router status could not be parsed")
    _, serial, hardware, software, description, uptime = info[:6]
    model = _MODEL_RE.search(description)
    # stOpticInfo(domain, tx, rx, voltage mV, temperature, bias mA, ..., LosStatus)
    optic = _constructor_args(optic_page, "stOpticInfo")
    values = [_number(v) for v in optic[1:6]] if len(optic) >= 6 else [None] * 5
    if values[2] is not None:
        values[2] /= 1000
    los = optic[14].strip() if len(optic) >= 15 else ""
    cpu = _number(_quoted_var(status_page, "cpuUsed"))
    memory = _number(_quoted_var(status_page, "memUsed"))
    return RouterStatus(
        model=model.group(1) if model else description,
        serial=serial,
        hardware_version=hardware,
        software_version=software,
        uptime=int(uptime) if uptime.isdigit() else None,
        cpu=int(cpu) if cpu is not None else None,
        memory=int(memory) if memory is not None else None,
        optic=dict(zip(_OPTIC_FIELDS, values)),
        fibre_signal=None if los == "" else los == "0",
    )


def _unescape(value: str) -> str:
    return _HEX_RE.sub(lambda m: chr(int(m.group(1), 16)), value)


def parse_devices(page: str) -> dict[str, LanDevice]:
    """Parse GetLanUserDevInfo.asp into devices keyed by lower-case MAC.

    The page lists some devices more than once; an online entry wins.
    """
    devices: dict[str, LanDevice] = {}
    for match in _DEVICE_RE.finditer(page):
        row = dict(zip(_FIELDS, (_unescape(a) for a in _ARG_RE.findall(match.group(1)))))
        mac = row.get("mac", "").lower()
        if not mac or (mac in devices and devices[mac].online):
            continue
        devices[mac] = LanDevice(
            mac=mac,
            ip=row.get("ip", ""),
            hostname=row.get("hostname", ""),
            port=row.get("port", ""),
            online=row.get("status", "").lower() == "online",
        )
    return devices


class HuaweiHG8247Client:
    """Logs in, reads the LAN device table and logs out on every poll.

    The router allows few failed logins before locking the account, so an
    authentication failure is raised as HuaweiHG8247AuthError and never retried here.
    """

    def __init__(self, session: aiohttp.ClientSession, host: str, username: str, password: str) -> None:
        self._session = session
        self._base = URL(f"http://{host}")
        self._username = username
        self._password = password
        self._lock = asyncio.Lock()
        # The session cookie is literally named "Cookie" and holds ":" and "=";
        # aiohttp's cookie jar re-quotes it and the router then answers 403,
        # so it is sent by hand instead.
        self._cookie = ""

    async def _request(self, path: str, data: dict | None = None, method: str = "POST") -> tuple[str, list[str]]:
        try:
            async with self._session.request(
                method, self._base.join(URL(path)), data=data if method == "POST" else None,
                headers={"Cookie": self._cookie} if self._cookie else None,
                allow_redirects=False, timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                resp.raise_for_status()
                body = (await resp.read()).decode("utf-8-sig", "replace")
                return body, resp.headers.getall("Set-Cookie", [])
        except (aiohttp.ClientError, TimeoutError) as err:
            raise HuaweiHG8247Error(f"{path}: {err}") from err

    async def _post(self, path: str, data: dict | None = None, method: str = "POST") -> str:
        return (await self._request(path, data, method))[0]

    async def _login(self) -> None:
        self._cookie = ""
        token = (await self._post("/asp/GetRandCount.asp")).strip()
        self._cookie = "Cookie=body:Language:portuguese:id=-1"
        _, set_cookies = await self._request("/login.cgi", {
            "UserName": self._username,
            "PassWord": base64.b64encode(self._password.encode()).decode(),
            "Language": "portuguese",
            "x.X_HW_Token": token,
        })
        self._cookie = ""
        for header in set_cookies:
            cookie = header.split(";", 1)[0]
            if cookie.startswith("Cookie=sid="):
                self._cookie = cookie
                return
        page = await self._post("/", method="GET")
        if re.search(r"var FailStat = '1'|var LockLeftTime = '[1-9]", page):
            raise HuaweiHG8247AuthError("Login rejected")
        raise HuaweiHG8247Error("Login did not return a session (another admin session may be open)")

    @asynccontextmanager
    async def _logged_in(self, logout: bool = True) -> AsyncIterator[None]:
        """Hold the router's single admin session for one batch of requests."""
        async with self._lock:
            await self._login()
            try:
                yield
            finally:
                if logout:
                    try:
                        await self._post("/logout.cgi?RequestFile=html/logout.html")
                    except HuaweiHG8247Error:
                        pass
                self._cookie = ""

    async def async_get_devices(self) -> dict[str, LanDevice]:
        async with self._logged_in():
            # The web UI asks the router to ARP-probe hosts before reading
            # the table, which keeps online/offline status current.
            script = await self._post("/html/bbsp/common/lanuserinfo.asp", method="GET")
            if token := _TOKEN_RE.search(script):
                await self._post("/html/bbsp/common/userDevSendArp.cgi", {"x.X_HW_Token": token.group(1)})
                await asyncio.sleep(1)
            page = await self._post("/html/bbsp/common/GetLanUserDevInfo.asp")
        devices = parse_devices(page)
        if not devices:
            raise HuaweiHG8247Error("Device table was empty or could not be parsed")
        return devices

    async def async_get_status(self) -> RouterStatus:
        async with self._logged_in():
            status_page = await self._post("/html/bbsp/status/Status_ptvdf.asp", method="GET")
            optic_page = await self._post("/html/amp/opticinfo/newvdfopticinfo.asp", method="GET")
        return parse_status(status_page, optic_page)

    async def async_reboot(self) -> None:
        # The router drops the session as it goes down, so there is no logout.
        async with self._logged_in(logout=False):
            page = await self._post("/html/ssmp/reset/resetptvdf.asp", method="GET")
            if not (token := _ONTTOKEN_RE.search(page)):
                raise HuaweiHG8247Error("Reboot token not found")
            try:
                await self._post(
                    "/html/ssmp/reset/set.cgi?x=InternetGatewayDevice.X_HW_DEBUG.SMP.DM.ResetBoard"
                    "&RequestFile=html/ssmp/reset/resetptvdf.asp",
                    {"x.X_HW_Token": token.group(1)},
                )
            except HuaweiHG8247Error:
                # A reboot that starts before the reply arrives looks like a dropped connection.
                pass
