"""Constants for the Swiss Hail Protection integration."""
DOMAIN = "swiss_hail_protection"

CONF_SOURCE = "source"
SOURCE_VKF = "vkf"
SOURCE_METEOSWISS = "meteoswiss"

# --- Source 1: VKF hail-warning signal -------------------------------------
# Poll endpoint of the VKF hail-warning service ("Hagelschutz - einfach
# automatisch"), operated by NetITServices on behalf of the cantonal building
# insurers. The device serial is the only credential; the request goes over
# TLS so it cannot be read or altered in transit.
VKF_API_BASE_URL = "https://meteo.netitservices.com/api/v1/devices"
VKF_REQUEST_TIMEOUT_SECONDS = 15

# The service recalculates the hail forecast every five minutes and requires
# clients to poll every 120 seconds (the same cadence as the VKF signal box).
VKF_UPDATE_INTERVAL_SECONDS = 120

CONF_DEVICE_ID = "device_id"
CONF_HWTYPE_ID = "hwtype_id"

# currentState values as documented in the VKF API specification.
STATE_CODE_NO_HAIL = 0
STATE_CODE_HAIL = 1
STATE_CODE_TEST_ALARM = 2

VKF_ATTRIBUTION = "Signal: VKF hail-warning service (Hagelschutz - einfach automatisch)"

# --- Source 2: MeteoSwiss hail radar products (Open Government Data) --------
# Probability of hail (POH, %) and maximum expected severe hail size (MESHS,
# mm) on the 1 km Swiss radar composite grid, published every five minutes
# through the Federal Spatial Data Infrastructure. One file covers all of
# Switzerland, so nothing about the configured location is ever sent out.
METEOSWISS_BASE_URL = "https://data.geo.admin.ch/ch.meteoschweiz.ogd-radar-hail"
METEOSWISS_STAC_ITEMS_URL = (
    "https://data.geo.admin.ch/api/stac/v1/collections/ch.meteoschweiz.ogd-radar-hail/items"
)
METEOSWISS_REQUEST_TIMEOUT_SECONDS = 30
METEOSWISS_UPDATE_INTERVAL_SECONDS = 300
# Products are published a minute or two after their nominal time; the
# coordinator starts at the newest slot that can realistically exist and
# walks back this many five-minute steps before giving up.
METEOSWISS_PUBLISH_DELAY_SECONDS = 90
METEOSWISS_MAX_SLOTS_BACK = 4
# File name parts of the two products (prodname and version suffix as
# published in October 2026). If the suffix changes, the coordinator
# discovers the current one from the day's STAC item.
METEOSWISS_POH_PREFIX = "bzc"
METEOSWISS_POH_SUFFIX = "vl.845.h5"
METEOSWISS_MESHS_PREFIX = "mzc"
METEOSWISS_MESHS_SUFFIX = "vl.850.h5"
# The hail products are only calculated from 1 April to 30 September.
METEOSWISS_SEASON_MONTHS = range(4, 10)

# Swiss radar composite grid: 710 x 640 cells of 1 km in LV95 (EPSG:2056),
# upper-left corner at E 2 255 000 / N 1 480 000.
GRID_COLS = 710
GRID_ROWS = 640
GRID_WEST_E = 2_255_000.0
GRID_NORTH_N = 1_480_000.0
GRID_CELL_M = 1000.0

CONF_LATITUDE = "latitude"
CONF_LONGITUDE = "longitude"
CONF_RADIUS_KM = "radius_km"
CONF_POH_THRESHOLD = "poh_threshold"

DEFAULT_RADIUS_KM = 10
DEFAULT_POH_THRESHOLD = 80
MAX_RADIUS_KM = 50

METEOSWISS_ATTRIBUTION = "Source: MeteoSwiss"

# --- Shared --------------------------------------------------------------------
STATUS_NO_HAIL = "no_hail"
STATUS_HAIL = "hail"
STATUS_TEST_ALARM = "test_alarm"
STATUS_OFF_SEASON = "off_season"
STATUS_OPTIONS = [STATUS_NO_HAIL, STATUS_HAIL, STATUS_TEST_ALARM, STATUS_OFF_SEASON]

STATE_CODE_TO_STATUS = {
    STATE_CODE_NO_HAIL: STATUS_NO_HAIL,
    STATE_CODE_HAIL: STATUS_HAIL,
    STATE_CODE_TEST_ALARM: STATUS_TEST_ALARM,
}
