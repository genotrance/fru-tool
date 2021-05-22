# fru - Read and write binary IPMI FRU files
# Copyright 2018-2021 Kurt McKee <contactme@kurtmckee.org>
# Copyright 2017 Dell Technologies
#
# https://github.com/kurtmckee/fru-tool/
#
# Licensed under the terms of the MIT License:
# https://opensource.org/licenses/MIT


import datetime
import os
import pathlib
from typing import Dict, List, Tuple, Union

try:
    from importlib.metadata import version
except ImportError:
    # Python <3.8
    from importlib_metadata import version

import toml

from . import exceptions
from . import shared


min_date =  datetime.datetime(1996, 1, 1, 0, 0)  # 0x000000
max_date = datetime.datetime(2027, 11, 24, 20, 15)  # 0xffffff


def convert_str_to_minutes(stamp: str) -> int:
    """Convert a str to the number of minutes since 1996-01-01 00:00."""

    try:
        date = datetime.datetime.strptime(stamp, '%Y-%m-%d %H:%M')
    except ValueError:
        msg = f'The date "{stamp}" must follow the format "YYYY-MM-DD HH:MM"'
        raise exceptions.DateTimeException(msg)

    if date < min_date:
        msg = f'The date/time "{stamp}" must be at least 1996-01-01 00:00'
        raise exceptions.DateTimeException(msg)

    if date > max_date:
        msg = f'The date/time "{stamp}" must be at most 2027-11-24 20:15'
        raise exceptions.DateTimeException(msg)

    return int((date - min_date).total_seconds()) // 60


def convert_minutes_to_str(minutes: int) -> str:
    """Format minutes as a human-friendly date/time string.

    The return string will be formatted as YYYY-MM-DD HH:MM.
    For example, "2021-02-01 19:28".
    """

    if minutes < 0:
        msg = f'*minutes* must be >= 0 (got {minutes})'
        raise exceptions.DateTimeException(minutes)

    if minutes > 0xff_ff_ff:
        msg = f'*minutes* must be <= 0xffffff (got 0x{minutes:x})'
        raise exceptions.DateTimeException(minutes)

    date = min_date + datetime.timedelta(minutes=minutes)
    return date.strftime('%Y-%m-%d %H:%M')


def repr_(value: Union[bool, int, str, List]) -> str:
    if isinstance(value, bool):
        return str(bool(value)).lower()
    elif isinstance(value, int):
        return str(value)
    elif isinstance(value, str):
        value = value.replace('\\', '\\\\')
        value = value.replace('"', '\\"')
        return f'"{value}"'
    elif isinstance(value, list):
        output = ' '.join(f'{repr_(v)},' for v in value).rstrip(',')
        return f'[{output}]'

    msg = f'Unable to represent {repr(value)} (type={type(value)}) in the TOML format'
    raise exceptions.TOMLException(msg)


def repr_internal(value: bytes) -> str:
    """Represent the internal section as a sequence of bytes."""

    if not value:
        return '[]'

    output = ['[']
    for block in range(0, len(value), 16):
        pieces = []
        for i in value[block:block + 16]:
            pieces.append(f'0x{i:02x}')
        output.append('    ' + ', '.join(pieces) + ',')
    output.append(']')
    return '\n'.join(output)


def load(path: Union[pathlib.Path, str] = None, text: str = None) -> Dict[str, Dict[str, Union[bytes, int, str]]]:
    """Load a TOML file and return its data as a dictionary.

    If *path* is specified it must be a TOML-formatted file.
    If *text* is specified it must be a TOML-formatted string.
    """

    if not path and not text:
        raise exceptions.FRUException('*path* or *text* must be specified')

    data = {
        'common': shared.get_default_common_section(),
        'board': shared.get_default_board_section(),
        'chassis': shared.get_default_chassis_section(),
        'product': shared.get_default_product_section(),
        'internal': shared.get_default_internal_section(),
    }

    if path:
        toml_data = toml.load(path)
    else:
        toml_data = toml.loads(text)

    for section in data:
        if section in toml_data:
            data[section].update(toml_data[section])

    # These values must be integers.
    integers: Tuple[Tuple[str, str], ...] = (
        ('common', 'size'),
        ('common', 'format_version'),
        ('board', 'language_code'),
        ('chassis', 'type'),
        ('product', 'language_code'),
    )

    dates = (
        ('board', 'mfg_date_time'),
    )

    # Remove sections that are explicitly excluded.
    for section in ['internal', 'chassis', 'board', 'product', 'multirecord']:
        include_section = f'include_{section}'
        if not data['common'].get(include_section, True) and section in data:
            del(data[section])
        if include_section in data['common']:
            del(data['common'][include_section])

    # Standardize integer values.
    for section, key in integers:
        if not isinstance(data.get(section, {}).get(key, 0), int):
            msg = f'Section [{section}] key "{key}" must be a number'
            raise exceptions.TOMLException(msg)

    # Standardize date/time values.
    for section, key in dates:
        if section in data and key in data[section]:
            # Convert a default value of 0 to a corresponding string.
            if not data[section][key]:
                data[section][key] = '1996-01-01 00:00'
            if not isinstance(data[section][key], str):
                msg = f'Section [{section}] key "{key}" must be a string'
                raise exceptions.TOMLException(msg)
            data[section][key] = convert_str_to_minutes(data[section][key])

    # Normalize the internal info area data.
    if data.get('internal', {}).get('data'):
        msg = f'Section [internal] key "data" must be a list of numbers or a string'
        try:
            data['internal']['data'] = bytes(data['internal']['data'])
        except TypeError:
            try:
                data['internal']['data'] = data['internal']['data'].encode('utf8')
            except AttributeError:
                raise exceptions.TOMLException(msg)
    elif data.get('internal', {}).get('file'):
        internal_file = os.path.join(
            os.path.dirname(path), data['internal']['file']
        )
        try:
            with open(internal_file, 'rb') as f:
                data['internal']['data'] = f.read()
        except FileNotFoundError:
            msg = f'Internal info area file {internal_file} not found'
            raise exceptions.TOMLException(msg)
    if 'file' in data.get('internal', {}):
        del(data['internal']['file'])

    return data


def dump(data: Dict[str, Dict[str, Union[bytes, int, str]]] = None) -> str:
    """Dump data to the TOML format.

    This function can also generate a blank TOML file.
    """

    data = data or {}
    info = {
        'common': shared.get_default_common_section(),
        'board': shared.get_default_board_section(),
        'chassis': shared.get_default_chassis_section(),
        'product': shared.get_default_product_section(),
    }
    for section in ('common', 'board', 'chassis', 'product'):
        info[section].update(data.get(section, {}))

    output = [
        # Header
        f'# -------------------------------------------------------------------',
        f'# Generated by frutool {version("fru")}',
        f'# https://github.com/kurtmckee/fru-tool/',
        f'#',
        f'# Notes regarding the TOML format, which is like an INI file:',
        f'#',
        f'# * Values surrounded by quotation marks are strings: "Vendor"',
        f'#   Literal quotation marks must be escaped using a backslash: "\\""',
        f'#   Literal backslashes must also be escaped using a backslash: "\\\\"',
        f'# * Boolean values use the words "true" and "false" without quotes.',
        f'# * Numbers that begin with 0x are interpreted as hexadecimal: 0x30',
        f'#',
        f'# -------------------------------------------------------------------',
        f'',
        f'',

        # Common
        f'[common]',
        f'# Warning: It may be harmful to modify *format_version*.',
        f'format_version = {repr_(info["common"]["format_version"])}',
        f'',
        f'# Warning: It may be harmful to modify *size*.',
        f'size = {repr_(info["common"]["size"])}',
        f'',
        f'# These options control which sections are included in the FRU file.',
        f'include_board = {repr_(bool(data.get("board", False)))}',
        f'include_chassis = {repr_(bool(data.get("chassis", False)))}',
        f'include_product = {repr_(bool(data.get("product", False)))}',
        f'include_internal = {repr_(bool(data.get("internal", False)))}',
        f'include_multirecord = {repr_(bool(data.get("multirecord", False)))}',
        f'',
        f'',

        # Board
        f'[board]',
        f'# Warning: It may be harmful to modify *format_version*.',
        f'format_version = {repr_(info["board"]["format_version"])}',
        f'',
        f'language_code = {repr_(info["board"]["language_code"])}',
        f'',
        f'mfg_date_time = "{convert_minutes_to_str(info["board"]["mfg_date_time"])}"',
        f'#                │    │  │  │  │',
        f'#         year ──┘    │  │  │  ╰── minutes',
        f'#             month ──╯  │  ╰── hours',
        f'#                  day ──╯',
        f'',
        f'manufacturer = {repr_(info["board"]["manufacturer"])}',
        f'product_name = {repr_(info["board"]["product_name"])}',
        f'serial_number = {repr_(info["board"]["serial_number"])}',
        f'part_number = {repr_(info["board"]["part_number"])}',
        f'fru_file_id = {repr_(info["board"]["fru_file_id"])}',
        f'custom_fields = {repr_(info["board"]["custom_fields"])}',
        f'',
        f'',

        # Chassis
        f'[chassis]',
        f'# Warning: It may be harmful to modify *format_version*.',
        f'format_version = {repr_(info["chassis"]["format_version"])}',
        f'',
        f'type = {repr_(info["chassis"]["type"])}',
        f'part_number = {repr_(info["chassis"]["part_number"])}',
        f'serial_number = {repr_(info["chassis"]["serial_number"])}',
        f'custom_fields = {repr_(info["chassis"]["custom_fields"])}',
        f'',
        f'',

        # Product
        f'[product]',
        f'# Warning: It may be harmful to modify *format_version*.',
        f'format_version = {repr_(info["product"]["format_version"])}',
        f'',
        f'language_code = {repr_(info["product"]["language_code"])}',
        f'manufacturer = {repr_(info["product"]["manufacturer"])}',
        f'product_name = {repr_(info["product"]["product_name"])}',
        f'part_number = {repr_(info["product"]["part_number"])}',
        f'product_version = {repr_(info["product"]["product_version"])}',
        f'serial_number = {repr_(info["product"]["serial_number"])}',
        f'asset_tag = {repr_(info["product"]["asset_tag"])}',
        f'fru_file_id = {repr_(info["product"]["fru_file_id"])}',
        f'custom_fields = {repr_(info["product"]["custom_fields"])}',
        f'',
        f'',

        # Internal
        f'[internal]',
        f'# Warning: It may be harmful to modify *format_version*.',
        f'format_version = {repr_(data.get("internal", {}).get("format_version", 1))}',
        f'',
        f'# The *data* key can be used to encode a sequence of bytes serialized',
        f'# as a list of numbers. For small amounts of internal data this might',
        f'# be sufficient.',
        f'#',
        f'# Alternatively, if the *file* key is specified then the file will be',
        f'# opened and read in binary mode.',
        f'#',
        f'# Examples:',
        f'#',
        f'#     data = [0x01, 0x02, 0x03]',
        f'#     file = "path/to/file"',
        f'#',
        f'# Do not use the *data* and *file* keys at the same time.',
        f'',
        f'data = {repr_internal(data.get("internal", {}).get("data", b""))}',
        f'',
        f'',
    ]
    
    return '\n'.join(output)
