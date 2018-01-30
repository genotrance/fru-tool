# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import os

import pytest

import fru


sections = ['all', 'empty', 'board', 'chassis', 'internal', 'product']


@pytest.mark.parametrize('name', sections)
def test_basic_ini_sections(name):
    path = os.path.join(os.path.dirname(__file__), 'basic-{}.ini'.format(name))
    config = fru.read_config(path)
    actual = fru.make_fru(config)

    path = os.path.join(os.path.dirname(__file__), 'basic-{}.bin'.format(name))
    with open(path, 'rb') as f:
        expected = f.read()

    assert actual == expected


@pytest.mark.parametrize('name', sections[2:])
def test_one_parsed_section(name):
    path = os.path.join(os.path.dirname(__file__), 'basic-{}.ini'.format(name))
    config = fru.read_config(path)
    assert len(config) == 2
    assert name in config


def test_too_much_data():
    config = {
        "common": {"version": 1, "size": 20},
        "chassis": {"part": "a".encode("ascii") * 250},
    }
    with pytest.raises(ValueError):
        fru.make_fru(config)


def test_empty_everything():
    config = {
        "common": {
            "version": 1,
            "size": 256,
            "internal": 1,
            "chassis": 1,
            "board": 1,
            "product": 1,
        },
        "internal": {}, "chassis": {}, "board": {}, "product": {},
    }
    fru.make_fru(config)


def test_missing_required_elements():
    with pytest.raises(ValueError):
        fru.make_fru({})
    with pytest.raises(ValueError):
        fru.make_fru({"common": {"size": "512"}})
    with pytest.raises(ValueError):
        fru.make_fru({"common": {"version": "1"}})


def test_skipped_section():
    path = os.path.join(os.path.dirname(__file__), 'skip-section.ini')
    config = fru.read_config(path)
    assert "internal" not in config
