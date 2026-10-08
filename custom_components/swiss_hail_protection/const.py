"""Constants for the Swiss Hail Protection (VKF) integration."""
DOMAIN = "swiss_hail_protection"

# Poll endpoint of the VKF hail-warning service ("Hagelschutz - einfach
# automatisch"), operated by NetITServices on behalf of the cantonal building
# insurers. The device serial is the only credential; the request goes over
# TLS so it cannot be read or altered in transit.
API_BASE_URL = "https://meteo.netitservices.com/api/v1/devices"
REQUEST_TIMEOUT_SECONDS = 15

# The service recalculates the hail forecast every five minutes and requires
# clients to poll every 120 seconds (the same cadence as the VKF signal box).
UPDATE_INTERVAL_SECONDS = 120

CONF_DEVICE_ID = "device_id"
CONF_HWTYPE_ID = "hwtype_id"

# currentState values as documented in the VKF API specification.
STATE_CODE_NO_HAIL = 0
STATE_CODE_HAIL = 1
STATE_CODE_TEST_ALARM = 2

STATUS_NO_HAIL = "no_hail"
STATUS_HAIL = "hail"
STATUS_TEST_ALARM = "test_alarm"
STATUS_OPTIONS = [STATUS_NO_HAIL, STATUS_HAIL, STATUS_TEST_ALARM]

STATE_CODE_TO_STATUS = {
    STATE_CODE_NO_HAIL: STATUS_NO_HAIL,
    STATE_CODE_HAIL: STATUS_HAIL,
    STATE_CODE_TEST_ALARM: STATUS_TEST_ALARM,
}

ATTRIBUTION = "Signal: VKF hail-warning service (Hagelschutz - einfach automatisch)"
