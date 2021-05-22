# Unit tests for fru-tool
# Copyright 2018-2021 Kurt McKee <contactme@kurtmckee.org>
# Copyright 2017 Dell Technologies
#
# https://github.com/kurtmckee/fru-tool/
#
# Licensed under the terms of the MIT License:
# https://opensource.org/licenses/MIT


import os

# noinspection PyUnresolvedReferences,PyPackageRequirements
import pytest

import fru.fru_format


sections = (
    'all',
    'empty',
    'board',
    'chassis',
    'internal-data',
    'internal-file',
    'product',
)


def test_too_much_data():
    config = {
        'common': {'format_version': 1, 'size': 20},
        'chassis': {'part_number': 'a' * 250},
    }
    with pytest.raises(ValueError):
        fru.fru_format.dump(config)


def test_empty_everything():
    config = {
        'common': {
            'format_version': 1,
            'size': 256,
        },
        'internal': {}, 'chassis': {}, 'board': {}, 'product': {},
    }
    fru.fru_format.dump(config)


def test_missing_required_elements():
    with pytest.raises(ValueError):
        fru.fru_format.dump({})
    with pytest.raises(ValueError):
        fru.fru_format.dump({'common': {'size': 512}})
    with pytest.raises(ValueError):
        fru.fru_format.dump({'common': {'format_version': 1}})


def test_load_bad_calls():
    with pytest.raises(ValueError):
        fru.fru_format.load()
    with pytest.raises(ValueError):
        fru.fru_format.load(path='a', blob='a'.encode('ascii'))


def test_bad_header_checksum():
    blob = b"\x01\x00\x00\x00\x00\x00\x00\x00"
    with pytest.raises(ValueError):
        fru.fru_format.load(blob=blob)


def test_checksum_of_zero():
    path = os.path.join(
        os.path.dirname(__file__),
        'checksum-zero.bin'
    )
    fru.fru_format.load(path)


@pytest.mark.parametrize('section', ['board', 'chassis', 'product'])
@pytest.mark.parametrize('count', [i for i in range(10)])
def test_custom_fields(section, count):
    data = {
        'common': {'size': 64, 'format_version': 1},
        section: {'custom_fields': [f'{i:02}' for i in range(count)]}
    }
    symmetric_data = fru.fru_format.load(blob=fru.fru_format.dump(data))
    assert len(symmetric_data[section]['custom_fields']) == count
