"""Unit tests for src.ingestion.tle_parser (Owner: Anas)."""

import pytest

from src.ingestion.models import TLEParseError
from src.ingestion.tle_parser import classify_object_type, parse_tle_file, parse_tle_lines, verify_checksum
from src.shared.interfaces.contracts import ObjectType

ISS_NAME = "ISS (ZARYA)"
ISS_LINE1 = "1 25544U 98067A   26233.79112499  .00009217  00000+0  17182-3 0  9998"
ISS_LINE2 = "2 25544  51.6329 335.3940 0007698  70.3743 289.8075 15.49557549581927"

DEBRIS_NAME = "COSMOS 2251 DEB"
DEBRIS_LINE1 = "1 34427U 93036SX  26233.50000000  .00001234  00000+0  12345-3 0  9999"
DEBRIS_LINE2 = "2 34427  74.0300 100.0000 0010000 100.0000 260.0000 14.20000000123459"


class TestChecksum:
    def test_valid_checksums_pass(self):
        assert verify_checksum(ISS_LINE1)
        assert verify_checksum(ISS_LINE2)

    def test_corrupted_line_fails_checksum(self):
        corrupted = ISS_LINE1[:-1] + ("0" if ISS_LINE1[-1] != "0" else "1")
        assert not verify_checksum(corrupted)

    def test_non_digit_terminator_is_invalid(self):
        assert not verify_checksum(ISS_LINE1[:-1] + "X")


class TestParseTleLines:
    def test_parses_iss_fields_correctly(self):
        parsed = parse_tle_lines(ISS_LINE1, ISS_LINE2, name=ISS_NAME)

        assert parsed.norad_id == 25544
        assert parsed.classification == "U"
        assert parsed.intl_designator == "98067A"
        assert parsed.inclination_deg == pytest.approx(51.6329)
        assert parsed.raan_deg == pytest.approx(335.3940)
        assert parsed.eccentricity == pytest.approx(0.0007698)
        assert parsed.arg_perigee_deg == pytest.approx(70.3743)
        assert parsed.mean_anomaly_deg == pytest.approx(289.8075)
        assert parsed.mean_motion_rev_per_day == pytest.approx(15.49557549)
        assert parsed.rev_number_at_epoch == 58192
        assert parsed.bstar == pytest.approx(0.00017182)
        assert parsed.checksum_valid is True
        assert parsed.object_type == ObjectType.PAYLOAD
        assert parsed.epoch.tzinfo is not None

    def test_epoch_decodes_to_correct_calendar_date(self):
        parsed = parse_tle_lines(ISS_LINE1, ISS_LINE2, name=ISS_NAME)
        # epoch_day 233.791... of year 2026 -> day-of-year 233 is Aug 21
        assert parsed.epoch.year == 2026
        assert parsed.epoch.month == 8
        assert parsed.epoch.day == 21

    def test_debris_name_classified_as_debris(self):
        parsed = parse_tle_lines(DEBRIS_LINE1, DEBRIS_LINE2, name=DEBRIS_NAME)
        assert parsed.object_type == ObjectType.DEBRIS
        assert parsed.checksum_valid is True

    def test_derived_altitude_helpers_are_physically_sane(self):
        parsed = parse_tle_lines(ISS_LINE1, ISS_LINE2, name=ISS_NAME)
        # ISS orbits at roughly 400-430 km altitude.
        assert 380 < parsed.perigee_altitude_km() < 450
        assert 380 < parsed.apogee_altitude_km() < 450
        assert parsed.apogee_altitude_km() >= parsed.perigee_altitude_km()

    def test_wrong_length_line_raises(self):
        with pytest.raises(TLEParseError):
            parse_tle_lines(ISS_LINE1[:-1], ISS_LINE2, name=ISS_NAME)

    def test_wrong_prefix_raises(self):
        bad_line1 = "9" + ISS_LINE1[1:]
        with pytest.raises(TLEParseError):
            parse_tle_lines(bad_line1, ISS_LINE2, name=ISS_NAME)

    def test_mismatched_norad_id_raises(self):
        other_line2 = "2 99999" + ISS_LINE2[7:]
        with pytest.raises(TLEParseError):
            parse_tle_lines(ISS_LINE1, other_line2, name=ISS_NAME)

    def test_bad_checksum_raises_by_default(self):
        corrupted = ISS_LINE1[:-1] + ("0" if ISS_LINE1[-1] != "0" else "1")
        with pytest.raises(TLEParseError):
            parse_tle_lines(corrupted, ISS_LINE2, name=ISS_NAME)

    def test_bad_checksum_allowed_when_validation_disabled(self):
        corrupted = ISS_LINE1[:-1] + ("0" if ISS_LINE1[-1] != "0" else "1")
        parsed = parse_tle_lines(corrupted, ISS_LINE2, name=ISS_NAME, validate_checksum=False)
        assert parsed.checksum_valid is False


class TestClassifyObjectType:
    @pytest.mark.parametrize("name,expected", [
        ("ISS (ZARYA)", ObjectType.PAYLOAD),
        ("COSMOS 2251 DEB", ObjectType.DEBRIS),
        ("FENGYUN 1C DEBRIS", ObjectType.DEBRIS),
        ("SL-16 R/B", ObjectType.ROCKET_BODY),
        ("ARIANE 5 ROCKET BODY", ObjectType.ROCKET_BODY),
        ("", ObjectType.UNKNOWN),
        # Celestrak's own literal placeholder name for its "analyst" group
        # (uncatalogued fragments) -- not an empty string, so this used to
        # fall through to the PAYLOAD default instead of UNKNOWN.
        ("UNKNOWN", ObjectType.UNKNOWN),
        ("unknown", ObjectType.UNKNOWN),
    ])
    def test_classification(self, name, expected):
        assert classify_object_type(name) == expected


class TestParseTleFile:
    def test_parses_three_line_records(self):
        text = "\n".join([ISS_NAME, ISS_LINE1, ISS_LINE2, DEBRIS_NAME, DEBRIS_LINE1, DEBRIS_LINE2])
        results = parse_tle_file(text)
        assert len(results) == 2
        assert {r.norad_id for r in results} == {25544, 34427}

    def test_parses_two_line_records_without_name(self):
        text = "\n".join([ISS_LINE1, ISS_LINE2])
        results = parse_tle_file(text)
        assert len(results) == 1
        assert results[0].name == ""

    def test_skips_invalid_records_when_requested(self):
        text = "\n".join(["GARBAGE ENTRY", "not a tle line", ISS_NAME, ISS_LINE1, ISS_LINE2])
        results = parse_tle_file(text, skip_invalid=True)
        assert len(results) == 1
        assert results[0].norad_id == 25544

    def test_empty_text_returns_empty_list(self):
        assert parse_tle_file("") == []
