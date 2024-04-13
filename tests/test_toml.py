# Unit tests for fru-tool
# Copyright 2018-2024 Kurt McKee <contactme@kurtmckee.org>
# Copyright 2017 Dell Technologies
#
# https://github.com/kurtmckee/fru-tool/
#
# Licensed under the terms of the MIT License:
# https://opensource.org/licenses/MIT


import os

import pytest

import fru.exceptions
import fru.fru_format
import fru.toml_format

sections = [
    "all",
    "empty",
    "board",
    "chassis",
    "internal-data",
    "internal-file",
    "product",
]


@pytest.mark.parametrize(
    "stamp, minutes",
    (
        ("1996-01-01 00:00", 0x00_00_00),
        ("2017-05-29 00:15", 0xAB_CD_EF),
        ("2027-11-24 20:15", 0xFF_FF_FF),
    ),
)
def test_convert_valid_dates(stamp, minutes):
    """Confirm valid datetime conversions."""

    assert fru.toml_format.convert_str_to_minutes(stamp) == minutes
    assert fru.toml_format.convert_minutes_to_str(minutes) == stamp


@pytest.mark.parametrize(
    "date",
    (
        "1900-01-01 00:00",  # too low
        "3000-01-01 00:00",  # too high
        "tomorrow morning",  # bad format
    ),
)
def test_convert_str_to_minutes_invalid(date):
    """Confirm invalid datetime conversions raise expected errors."""

    with pytest.raises(fru.exceptions.DateTimeException):
        fru.toml_format.convert_str_to_minutes(date)


@pytest.mark.parametrize("minutes", (-1, 0x1_00_00_00))
def test_convert_minutes_to_str_invalid(minutes):
    """Confirm invalid minutes values raise expected errors."""

    with pytest.raises(fru.exceptions.DateTimeException):
        fru.toml_format.convert_minutes_to_str(minutes)


@pytest.mark.parametrize(
    "value, expected",
    (
        (False, "false"),
        (True, "true"),
        (0, "0"),
        (1, "1"),
        ("", '""'),
        ("aa", '"aa"'),
        ('"', '"\\""'),
        ("\\", '"\\\\"'),
        ([], "[]"),
        (["aa", "bb", "00"], '["aa", "bb", "00"]'),
    ),
)
def test_repr_(value, expected):
    """Confirm value types are represented correctly in the TOML output."""

    assert fru.toml_format.repr_(value) == expected


def test_repr_bad_value():
    with pytest.raises(fru.exceptions.TOMLException):
        # noinspection PyTypeChecker
        fru.toml_format.repr_(None)


def test_dump_empty():
    """Confirm that an empty dump raises no errors."""

    assert isinstance(fru.toml_format.dump(), str)


@pytest.mark.parametrize("section", ("board", "chassis", "product", "internal"))
def test_roundtrip_dict_toml_dict(section):
    """Confirm that dict -> TOML -> dict roundtrips work."""

    original_data = {
        "common": {"format_version": 1, "size": 1024},
        section: {"format_version": 2},
    }
    roundtrip_data = fru.toml_format.load(text=fru.toml_format.dump(original_data))

    for section in original_data:
        for key in original_data[section]:
            assert original_data[section][key] == roundtrip_data[section][key]


@pytest.mark.parametrize("section", ("board", "chassis", "product"))
def test_roundtrip_fru_toml_fru(section):
    """Confirm FRU -> TOML -> FRU roundtrips work."""

    with open(f"tests/basic-{section}.bin", "rb") as file:
        original_blob = file.read()
    fru_data = fru.fru_format.load(blob=original_blob)
    toml_text = fru.toml_format.dump(fru_data)
    toml_data = fru.toml_format.load(text=toml_text)
    fru_blob = fru.fru_format.dump(toml_data)

    assert original_blob == fru_blob


@pytest.mark.parametrize("name", sections)
def test_basic_toml_sections(name):
    path = os.path.join(os.path.dirname(__file__), f"basic-{name}.toml")
    config = fru.toml_format.load(path)
    actual = fru.fru_format.dump(config)

    path = os.path.join(os.path.dirname(__file__), f"basic-{name}.bin")
    with open(path, "rb") as f:
        expected = f.read()

    assert actual == expected


@pytest.mark.parametrize("name", sections)
def test_identical_loading(name):
    path = os.path.join(os.path.dirname(__file__), f"basic-{name}.toml")
    toml_data = fru.toml_format.load(path)

    path = os.path.join(os.path.dirname(__file__), f"basic-{name}.bin")
    bin_data = fru.fru_format.load(path=path)

    assert len(toml_data) == len(bin_data)
    assert toml_data == bin_data


def test_skipped_section():
    path = os.path.join(os.path.dirname(__file__), "skip-section.toml")
    data = fru.toml_format.load(path)
    assert "internal" in data


def test_internal_fru_file_not_found():
    path = os.path.join(os.path.dirname(__file__), "internal-fru-file-not-found.toml")
    with pytest.raises(ValueError) as error:
        fru.toml_format.load(path)
        assert "not found" in error.msg


def test_internal_fru_requested_but_empty():
    path = os.path.join(os.path.dirname(__file__), "internal-empty.toml")
    data = fru.toml_format.load(path)
    assert "internal" in data


def test_repr_internal_empty():
    assert fru.toml_format.repr_internal(b"") == "[]"


def test_repr_internal():
    expected = "[\n    0x31, 0x32, 0x33,\n]"
    assert fru.toml_format.repr_internal(b"123") == expected
