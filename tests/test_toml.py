# Unit tests for fru-tool
# Copyright 2018-2021 Kurt McKee <contactme@kurtmckee.org>
# Copyright 2017 Dell Technologies
#
# https://github.com/kurtmckee/fru-tool/
#
# Licensed under the terms of the MIT License:
# https://opensource.org/licenses/MIT


import datetime

# noinspection PyUnresolvedReferences,PyPackageRequirements
import pytest

import fru.exceptions
import fru.toml_format


sections = [
    'all',
    'empty',
    'board',
    'chassis',
    'internal-data',
    'internal-file',
    'product',
]


@pytest.mark.parametrize(
    'stamp, minutes, date',
    (
            ('1996-01-01 00:00', 0x00_00_00, datetime.datetime(1996, 1, 1, 0, 0)),
            ('2017-05-29 00:15', 0xab_cd_ef, datetime.datetime(2017, 5, 29, 0, 15)),
            ('2027-11-24 20:15', 0xff_ff_ff, datetime.datetime(2027, 11, 24, 20, 15)),
    ),
)
def test_convert_valid_dates(stamp, minutes, date):
    """Confirm valid datetime conversions."""

    assert fru.toml_format.convert_datetime_to_minutes(date) == minutes
    assert fru.toml_format.convert_str_to_minutes(stamp) == minutes
    assert fru.toml_format.convert_minutes_to_str(minutes) == stamp


@pytest.mark.parametrize(
    'date, exception',
    (
            (datetime.datetime(1990, 1, 1, 0, 0), fru.exceptions.DateTimeTooLow),
            (datetime.datetime(2030, 1, 1, 0, 0), fru.exceptions.DateTimeTooHigh),
            (datetime.datetime(2000, 1, 1, 0, 0, 55), fru.exceptions.DateTimeIncludesSeconds),
    ),
)
def test_convert_datetime_to_minutes_invalid(date, exception):
    """Confirm invalid datetime conversions raise expected errors."""

    with pytest.raises(exception):
        fru.toml_format.convert_datetime_to_minutes(date)


def test_convert_str_to_minutes_invalid():
    """Confirm invalid datetime stamps raise expected errors."""

    with pytest.raises(fru.exceptions.DateTimeIncorrectFormat):
        fru.toml_format.convert_str_to_minutes('')


@pytest.mark.parametrize(
    'minutes, exception',
    (
            (-1, fru.exceptions.DateTimeTooLow),
            (0x1_00_00_00, fru.exceptions.DateTimeTooHigh),
    ),
)
def test_convert_minutes_to_str_invalid(minutes, exception):
    """Confirm invalid minutes values raise expected errors."""

    with pytest.raises(exception):
        fru.toml_format.convert_minutes_to_str(minutes)


@pytest.mark.parametrize(
    'value, expected',
    (
            (False, 'false'),
            (True, 'true'),
            (0, '0'),
            (1, '1'),
            ('', '""'),
            ('aa', '"aa"'),
            ('"', '"\\""'),
            ('\\', '"\\\\"'),
            ([], '[]'),
            (['aa', 'bb', '00'], '["aa", "bb", "00"]'),
    ),
)
def test_repr_(value, expected):
    """Confirm value types are represented correctly in the TOML output."""

    assert fru.toml_format.repr_(value) == expected


def test_dump_empty():
    """Confirm that an empty dump raises no errors."""

    assert isinstance(fru.toml_format.dump(), str)


@pytest.mark.parametrize('section', ('board', 'chassis', 'product', 'internal'))
def test_roundtrip_dict_toml_dict(section):
    """Confirm that dict -> TOML -> dict roundtrips work."""

    original_data = {
        'common': {'format_version': 1, 'size': 1024},
        section: {'format_version': 2},
    }
    roundtrip_data = fru.toml_format.load(text=fru.toml_format.dump(original_data))

    for section in original_data:
        for key in original_data[section]:
            assert original_data[section][key] == roundtrip_data[section][key]


@pytest.mark.parametrize('section', ('board', 'chassis', 'product'))
def test_roundtrip_fru_toml_fru(section):
    """Confirm FRU -> TOML -> FRU roundtrips work."""

    with open(f'tests/basic-{section}.bin', 'rb') as file:
        original_blob = file.read()
    fru_data = fru.fru_format.load(blob=original_blob)
    toml_text = fru.toml_format.dump(fru_data)
    toml_data = fru.toml_format.load(text=toml_text)
    fru_blob = fru.fru_format.dump(toml_data)

    assert original_blob == fru_blob
