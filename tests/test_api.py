"""Parser tests built from (anonymised) HG8247B7-8N V5R024C00S114 page snippets."""

import importlib.util
from pathlib import Path
import sys

_PATH = Path(__file__).parents[1] / "custom_components/huawei_hg8247/api.py"
_spec = importlib.util.spec_from_file_location("huawei_hg8247_api", _PATH)
api = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = api
_spec.loader.exec_module(api)

DEVICES = (
    'var UserDevinfo = new Array('
    'new USERDevice("InternetGatewayDevice.LANDevice.1.X_HW_UserDev.1","192\\x2e168\\x2e1\\x2e101",'
    '"02:00:00:00:00:01","SSID1","DHCP","","Offline","WIFI","844:3","iPhone","1","0","","iPhone","","0",""),'
    'new USERDevice("InternetGatewayDevice.LANDevice.1.X_HW_UserDev.2","192\\x2e168\\x2e1\\x2e100",'
    '"02:00:00:AA:00:02","LAN1","DHCP","","Online","ETH","3:26","desktop","1","0","","desktop","","0",""),'
    'new USERDevice("InternetGatewayDevice.LANDevice.1.X_HW_UserDev.3","192\\x2e168\\x2e1\\x2e101",'
    '"02:00:00:00:00:01","SSID1","DHCP","","Online","WIFI","0:01","iPhone","1","0","","iPhone","","0",""),'
    'null);'
)
STATUS = (
    'var deviceInfos = new Array(new stDeviceInfo("InternetGatewayDevice.DeviceInfo","SN0001","3F80\\x2eA",'
    '"V5R024C00S114","OptiXstar\\x20HG8247B7\\x2d8N\\x20GPON\\x20Terminal","3040471"),null);\n'
    "var cpuUsed = '22%'\nvar memUsed = '12%'\n"
)
OPTIC = (
    'var opticInfos = new Array(new stOpticInfo("InternetGatewayDevice.X_HW_DEBUG.AMP.Optic","2\\x2e33\\x20",'
    '"\\x2d18\\x2e57","3312","44","11","\\x2d3\\x2e68","\\x2d\\x2d","HUAWEI","SN","241015","1310","1490","20","0"),null);'
)


def test_devices_dedupe_prefers_online_and_lowercases_mac():
    devices = api.parse_devices(DEVICES)
    assert set(devices) == {"02:00:00:00:00:01", "02:00:00:aa:00:02"}
    assert devices["02:00:00:00:00:01"].online
    assert devices["02:00:00:aa:00:02"].ip == "192.168.1.100"
    assert devices["02:00:00:aa:00:02"].hostname == "desktop"


def test_status_and_optics():
    status = api.parse_status(STATUS, OPTIC)
    assert status.model == "HG8247B7-8N"
    assert status.software_version == "V5R024C00S114"
    assert status.uptime == 3040471
    assert (status.cpu, status.memory) == (22, 12)
    assert status.optic == {
        "tx_power": 2.33, "rx_power": -18.57, "voltage": 3.312, "temperature": 44.0, "bias_current": 11.0,
    }
    assert status.fibre_signal is True


def test_missing_optics_are_unknown():
    status = api.parse_status(STATUS, "")
    assert status.optic["rx_power"] is None
    assert status.fibre_signal is None
