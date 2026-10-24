"""Constants for the Huawei HG8247 integration."""

from datetime import timedelta

DOMAIN = "huawei_hg8247"
DEFAULT_HOST = "192.168.1.1"
CONF_CERTIFICATE_FINGERPRINT = "certificate_fingerprint"
CONF_TRACKED = "tracked_devices"
SCAN_INTERVAL = timedelta(seconds=30)
STATUS_INTERVAL = timedelta(minutes=5)
