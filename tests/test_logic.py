"""Pure logic: the VKF state code, the MeteoSwiss status for a radar
evaluation, the radar grid position and the product slot names."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from custom_components.swiss_hail_protection import meteoswiss
from custom_components.swiss_hail_protection.const import (
    STATUS_HAIL,
    STATUS_NO_HAIL,
    STATUS_OFF_SEASON,
    STATUS_TEST_ALARM,
)
from custom_components.swiss_hail_protection.coordinator import _status_for, parse_state_code
from custom_components.swiss_hail_protection.meteoswiss import RadarEvaluation


def test_vkf_state_codes():
    assert parse_state_code(0) == parse_state_code(0)
    assert parse_state_code(0).alarm is False and parse_state_code(0).status == STATUS_NO_HAIL
    hail = parse_state_code(1)
    assert hail.alarm is True and hail.status == STATUS_HAIL and hail.test_alarm is False
    test = parse_state_code(2)
    assert test.alarm is True and test.status == STATUS_TEST_ALARM and test.test_alarm is True
    unknown = parse_state_code(7)
    assert unknown.alarm is True and unknown.status is None and unknown.state_code == 7


def _evaluation(poh_max, poh_home=10.0, cells=0, nearest=None):
    return RadarEvaluation(poh_home=poh_home, poh_max=poh_max, meshs_max=25.0 if cells else None,
                           hail_cells=cells, nearest_hail_km=nearest, home_covered=True)


def test_meteoswiss_status():
    july = datetime(2026, 7, 15, 14, 0, tzinfo=timezone.utc)
    hail = _status_for(_evaluation(92.0, cells=3, nearest=4.2), july, 80)
    assert hail.alarm is True and hail.status == STATUS_HAIL
    assert hail.hail_cells == 3 and hail.nearest_hail_km == 4.2 and hail.meshs_max == 25.0
    calm = _status_for(_evaluation(40.0), july, 80)
    assert calm.alarm is False and calm.status == STATUS_NO_HAIL
    assert _status_for(_evaluation(80.0), july, 80).alarm is True  # the threshold itself counts
    january = datetime(2026, 1, 15, 14, 0, tzinfo=timezone.utc)
    assert _status_for(_evaluation(0.0), january, 80).status == STATUS_OFF_SEASON
    assert _status_for(_evaluation(0.0), july, 80).status == STATUS_NO_HAIL  # an empty summer product is simply calm
    nodata = _status_for(_evaluation(None, poh_home=None), july, 80)
    assert nodata.alarm is False and nodata.status is None


def test_grid_position_of_bern_and_outside():
    # The LV95 origin (Bern, old observatory) is E 2 600 000 / N 1 200 000; the
    # approximate formulas are good to about a hundred metres here, well below the 1 km cell.
    east, north = meteoswiss.wgs84_to_lv95(46.95240, 7.43958)
    assert abs(east - 2_600_000) < 200 and abs(north - 1_200_000) < 200
    col, row = meteoswiss.grid_position(46.95240, 7.43958)
    assert meteoswiss.inside_grid(col, row)
    assert abs(col - 345.0) < 0.3 and abs(row - 280.0) < 0.3
    assert meteoswiss.inside_grid(*meteoswiss.grid_position(52.52, 13.40)) is False  # Berlin


def test_slot_names():
    slot = datetime(2026, 7, 15, 14, 35, tzinfo=timezone.utc)
    assert meteoswiss.slot_filename("bzc", "rl.845.h5", slot) == "bzc261961435rl.845.h5"
    assert meteoswiss.slot_url("bzc", "rl.845.h5", slot).endswith("/20260715-ch/bzc261961435rl.845.h5")
    now = datetime(2026, 7, 15, 14, 38, 20, tzinfo=timezone.utc)
    assert meteoswiss.latest_slot(now, timedelta(seconds=90)) == datetime(2026, 7, 15, 14, 35, tzinfo=timezone.utc)
    assert meteoswiss.latest_slot(now, timedelta(seconds=240)) == datetime(2026, 7, 15, 14, 30, tzinfo=timezone.utc)
    local = datetime(2026, 7, 15, 16, 38, tzinfo=timezone(timedelta(hours=2)))
    assert meteoswiss.latest_slot(local, timedelta(seconds=90)) == datetime(2026, 7, 15, 14, 35, tzinfo=timezone.utc)
