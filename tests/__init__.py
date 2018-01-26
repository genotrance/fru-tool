# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import os

import pytest

import fru


sections = ['all', 'board', 'chassis', 'empty', 'internal', 'product']


@pytest.mark.parametrize('name', sections)
def test_basic_ini_sections(name):
    path = os.path.join(os.path.dirname(__file__), 'basic-{}.ini'.format(name))
    config = fru.read_config(path)
    actual = fru.make_fru(config)

    path = os.path.join(os.path.dirname(__file__), 'basic-{}.bin'.format(name))
    with open(path, 'rb') as f:
        expected = f.read()

    assert actual == expected
