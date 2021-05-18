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
import fru.toml_format


sections = (
    'all',
    'empty',
    'board',
    'chassis',
    'internal-data',
    'internal-file',
    'product',
)


@pytest.mark.parametrize('name', sections)
def test_basic_ini_sections(name):
    path = os.path.join(os.path.dirname(__file__), 'basic-{}.ini'.format(name))
    config = fru.toml_format.load(path)
    actual = fru.fru_format.dump(config)

    path = os.path.join(os.path.dirname(__file__), 'basic-{}.bin'.format(name))
    with open(path, 'rb') as f:
        expected = f.read()

    assert actual == expected


@pytest.mark.parametrize('name', sections)
def test_identical_loading(name):
    path = os.path.join(os.path.dirname(__file__), 'basic-{}.ini'.format(name))
    toml_data = fru.toml_format.load(path)

    path = os.path.join(os.path.dirname(__file__), 'basic-{}.bin'.format(name))
    bin_data = fru.fru_format.load(path=path)

    assert len(toml_data) == len(bin_data)
    assert toml_data == bin_data


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


def test_skipped_section():
    path = os.path.join(os.path.dirname(__file__), 'skip-section.ini')
    data = fru.toml_format.load(path)
    assert 'internal' in data


def test_load_bad_calls():
    with pytest.raises(ValueError):
        fru.fru_format.load()
    with pytest.raises(ValueError):
        fru.fru_format.load(path='a', blob='a'.encode('ascii'))


def test_bad_header_checksum():
    blob = b"\x01\x00\x00\x00\x00\x00\x00\x00"
    with pytest.raises(ValueError):
        fru.fru_format.load(blob=blob)


def test_internal_fru_file_not_found():
    path = os.path.join(
        os.path.dirname(__file__),
        'internal-fru-file-not-found.ini'
    )
    with pytest.raises(ValueError) as error:
        fru.toml_format.load(path)
        assert 'not found' in error.msg


def test_internal_fru_requested_but_empty():
    path = os.path.join(os.path.dirname(__file__), 'internal-empty.ini')
    data = fru.toml_format.load(path)
    assert 'internal' in data


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
