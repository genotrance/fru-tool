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

# noinspection PyUnresolvedReferences
import fru.api


sections = [
    'all',
    'empty',
    'board',
    'chassis',
    'internal-data',
    'internal-file',
    'product',
]


@pytest.mark.parametrize('name', sections)
def test_basic_ini_sections(name):
    path = os.path.join(os.path.dirname(__file__), 'basic-{}.ini'.format(name))
    config = fru.api.read_config(path)
    actual = fru.api.dump(config)

    path = os.path.join(os.path.dirname(__file__), 'basic-{}.bin'.format(name))
    with open(path, 'rb') as f:
        expected = f.read()

    assert actual == expected


@pytest.mark.parametrize('name', sections)
def test_identical_loading(name):
    path = os.path.join(os.path.dirname(__file__), 'basic-{}.ini'.format(name))
    ini_data = fru.api.read_config(path)

    path = os.path.join(os.path.dirname(__file__), 'basic-{}.bin'.format(name))
    bin_data = fru.api.load(path=path)

    assert ini_data == bin_data


def test_too_much_data():
    config = {
        "common": {"version": 1, "size": 20},
        "chassis": {"part": "a" * 250},
    }
    with pytest.raises(ValueError):
        fru.api.dump(config)


def test_empty_everything():
    config = {
        "common": {
            "version": 1,
            "size": 256,
        },
        "internal": {}, "chassis": {}, "board": {}, "product": {},
    }
    fru.api.dump(config)


def test_missing_required_elements():
    with pytest.raises(ValueError):
        fru.api.dump({})
    with pytest.raises(ValueError):
        fru.api.dump({"common": {"size": 512}})
    with pytest.raises(ValueError):
        fru.api.dump({"common": {"version": 1}})


def test_skipped_section():
    path = os.path.join(os.path.dirname(__file__), 'skip-section.ini')
    config = fru.api.read_config(path)
    assert "internal" not in config


def test_load_bad_calls():
    with pytest.raises(ValueError):
        fru.api.load()
    with pytest.raises(ValueError):
        fru.api.load(path='a', blob='a'.encode('ascii'))


def test_bad_header_checksum():
    blob = b"\x01\x00\x00\x00\x00\x00\x00\x00"
    with pytest.raises(ValueError):
        fru.api.load(blob=blob)


def test_internal_fru_file_not_found():
    path = os.path.join(
        os.path.dirname(__file__),
        'internal-fru-file-not-found.ini'
    )
    with pytest.raises(ValueError) as error:
        fru.api.read_config(path)
        assert 'not found' in error.msg


def test_internal_fru_requested_but_empty():
    path = os.path.join(os.path.dirname(__file__), 'internal-empty.ini')
    data = fru.api.read_config(path)
    assert 'internal' not in data


def test_checksum_of_zero():
    path = os.path.join(
        os.path.dirname(__file__),
        'checksum-zero.bin'
    )
    fru.api.load(path)


@pytest.mark.parametrize('section', ['board', 'chassis', 'product'])
def test_extras(section):
    for i in range(1, 10):
        key = 'extra{}'.format(i)
        data = {
            'common': {'size': 64, 'version': 1},
            section: {key: '---'}
        }
        symmetric_data = fru.api.load(blob=fru.api.dump(data))
        assert data[section][key] == symmetric_data[section][key]
