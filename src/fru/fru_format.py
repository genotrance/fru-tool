# fru - Read and write binary IPMI FRU files
# Copyright 2018-2021 Kurt McKee <contactme@kurtmckee.org>
# Copyright 2017 Dell Technologies
#
# https://github.com/kurtmckee/fru-tool/
#
# Licensed under the terms of the MIT License:
# https://opensource.org/licenses/MIT


import itertools
import os
import pathlib
import struct
from typing import Dict, List, Union

from . import shared


def validate_checksum(blob: bytes, offset: int, length: int):
    """Validate a chassis, board, or product checksum.

    *blob* is the binary data blob, and *offset* is the integer offset that
    the chassis, board, or product info area starts at.
    """

    checksum = ord(blob[offset + length - 1:offset + length])
    data_sum = sum(
        struct.unpack('%dB' % (length - 1), blob[offset:offset + length - 1])
    )
    if 0xff & (data_sum + checksum) != 0:
        raise ValueError('The data do not match the checksum')


def extract_values(blob: bytes, offset: int, names: List[str]):
    """Extract values that are delimited by type/length bytes.

    The values will be extracted into a dictionary. They'll be saved to keys
    in the same order that keys are provided in *names*.

    If there are more values than key names then the values will be stored
    in the key *custom_fields*.
    """

    data = {
        'custom_fields': [],
    }

    for name in names:
        type_length = ord(blob[offset:offset + 1])
        if type_length == 0xc1:
            return data
        length = type_length & 0x3f
        # encoding = (ord(blob[offset:offset + 1]) & 0xc0) >> 6
        data[name] = blob[offset + 1:offset + length + 1].decode('ascii')
        offset += length + 1

    while True:
        type_length = ord(blob[offset:offset + 1])
        if type_length == 0xc1:
            return data
        length = type_length & 0x3f
        # encoding = (ord(blob[offset:offset + 1]) & 0xc0) >> 6
        data['custom_fields'].append(blob[offset + 1:offset + length + 1].decode('ascii'))
        offset += length + 1


def load(
        path: Union[pathlib.Path, str] = None,
        blob: bytes = None,
) -> Dict[str, Dict[str, Union[bool, int, str, List]]]:
    """Load binary FRU information from a file or binary data blob.

    If *path* is provided, it will be read into memory.
    If *blob* is provided it will be used as-is.
    """

    if not path and not blob:
        raise ValueError('You must specify *path* or *blob*.')
    if path and blob:
        raise ValueError('You must specify *path* or *blob*, but not both.')

    if path:
        with open(path, 'rb') as f:
            blob = f.read()

    validate_checksum(blob, 0, 8)

    format_version = ord(blob[0:1]) & 0x0f
    internal_offset = ord(blob[1:2]) * 8
    chassis_offset = ord(blob[2:3]) * 8
    board_offset = ord(blob[3:4]) * 8
    product_offset = ord(blob[4:5]) * 8
    # multirecord_offset = ord(blob[5:6]) * 8

    data = {
        'common': {
            'format_version': format_version,
            'size': len(blob),
        },
    }

    if internal_offset:
        next_offset = chassis_offset or board_offset or product_offset
        internal_blob = blob[internal_offset + 1:next_offset or len(blob)]
        data['internal'] = {
            'format_version': ord(blob[internal_offset:internal_offset + 1]) & 0x0f,
            'data': internal_blob,
        }

    if chassis_offset:
        length = ord(blob[chassis_offset + 1:chassis_offset + 2]) * 8
        validate_checksum(blob, chassis_offset, length)

        data['chassis'] = shared.get_default_chassis_section()
        data['chassis'].update({
            'format_version': ord(blob[chassis_offset:chassis_offset + 1]) & 0x0f,
            'type': ord(blob[chassis_offset + 2:chassis_offset + 3]),
        })
        names = shared.get_chassis_section_names()
        data['chassis'].update(extract_values(blob, chassis_offset + 3, names))

    if board_offset:
        length = ord(blob[board_offset + 1:board_offset + 2]) * 8
        validate_checksum(blob, board_offset, length)

        data['board'] = shared.get_default_board_section()
        data['board'].update({
            'format_version': ord(blob[board_offset:board_offset + 1]) & 0x0f,
            'language_code': ord(blob[board_offset + 2:board_offset + 3]),
            'mfg_date_time': sum([
                ord(blob[board_offset + 3:board_offset + 4]),
                ord(blob[board_offset + 4:board_offset + 5]) << 8,
                ord(blob[board_offset + 5:board_offset + 6]) << 16,
            ]),
        })
        names = shared.get_board_section_names()
        data['board'].update(extract_values(blob, board_offset + 6, names))

    if product_offset:
        length = ord(blob[product_offset + 1:product_offset + 2]) * 8
        validate_checksum(blob, product_offset, length)

        data['product'] = shared.get_default_product_section()
        data['product'].update({
            'format_version': ord(blob[product_offset:product_offset + 1]) & 0x0f,
            'language_code': ord(blob[product_offset + 2:product_offset + 3]),
        })
        names = shared.get_product_section_names()
        data['product'].update(extract_values(blob, product_offset + 3, names))

    return data


def dump(data):
    if 'common' not in data:
        raise ValueError('[common] section missing in data')

    if 'format_version' not in data['common']:
        raise ValueError('"format_version" key missing in [common]')

    if 'size' not in data['common']:
        raise ValueError('"size" key missing in [common]')

    internal_offset = 0
    chassis_offset = 0
    board_offset = 0
    product_offset = 0
    multirecord_offset = 0

    internal = bytes()
    chassis = bytes()
    board = bytes()
    product = bytes()

    if data.get('internal', {}).get('data'):
        internal = make_internal(data)
    if 'chassis' in data:
        chassis = make_chassis(data)
    if 'board' in data:
        board = make_board(data)
    if 'product' in data:
        product = make_product(data)

    pos = 1
    if len(internal):
        internal_offset = pos
        pos += len(internal) // 8
    if len(chassis):
        chassis_offset = pos
        pos += len(chassis) // 8
    if len(board):
        board_offset = pos
        pos += len(board) // 8
    if len(product):
        product_offset = pos

    # Header
    out = struct.pack(
        'BBBBBBB',
        data['common']['format_version'],
        internal_offset,
        chassis_offset,
        board_offset,
        product_offset,
        multirecord_offset,
        0x00
    )

    # Checksum
    out += struct.pack('B', (0 - sum(bytearray(out))) & 0xff)

    blob = out + internal + chassis + board + product
    difference = data['common']['size'] - len(blob)
    pad = struct.pack('B' * difference, *[0] * difference)

    if len(blob + pad) > data['common']['size']:
        raise ValueError('Too much content, does not fit')

    return blob + pad


def make_internal(data):
    return struct.pack(
        'B%ds' % len(data['internal']['data']),
        data['internal'].get('format_version', 1),
        data['internal']['data'],
    )


def make_chassis(config):
    chassis = shared.get_default_chassis_section()
    chassis.update(config['chassis'])

    out = bytes()

    # Type
    out += struct.pack('B', chassis['type'])

    # Strings
    fields = shared.get_chassis_section_names()

    for key in fields:
        if chassis[key]:
            value = chassis[key].encode('ascii')
            out += struct.pack('B%ds' % len(value), len(value) | 0xC0, value)
        else:
            out += struct.pack('B', 0)

    if isinstance(chassis['custom_fields'], (list, tuple)):
        for record in chassis['custom_fields']:
            value = record.encode('ascii')
            out += struct.pack('B%ds' % len(value), len(value) | 0xC0, value)

    # No more fields
    out += struct.pack('B', 0xC1)

    # Padding
    while len(out) % 8 != 5:
        out += struct.pack('B', 0)

    # Header version and length in bytes
    out = struct.pack(
        'BB',
        chassis['format_version'],
        (len(out) + 3) // 8,
    ) + out

    # Checksum
    out += struct.pack('B', (0 - sum(bytearray(out))) & 0xff)

    return out


def make_board(config):
    board = shared.get_default_board_section()
    board.update(config['board'])

    out = bytes()

    # Language
    out += struct.pack('B', board['language_code'])

    # Date
    date = board['mfg_date_time']
    out += struct.pack(
        'BBB',
        (date & 0xFF),
        (date & 0xFF00) >> 8,
        (date & 0xFF0000) >> 16,
    )

    # String values
    fields = shared.get_board_section_names()

    for key in fields:
        if board[key]:
            value = board[key].encode('ascii')
            out += struct.pack('B%ds' % len(value), len(value) | 0xC0, value)
        else:
            out += struct.pack('B', 0)

    if isinstance(board['custom_fields'], (list, tuple)):
        for record in board['custom_fields']:
            value = record.encode('ascii')
            out += struct.pack('B%ds' % len(value), len(value) | 0xC0, value)

    # No more fields
    out += struct.pack('B', 0xC1)

    # Padding
    while len(out) % 8 != 5:
        out += struct.pack('B', 0)

    # Header version and length in bytes
    out = struct.pack(
        'BB',
        board['format_version'],
        (len(out)+3) // 8,
    ) + out

    # Checksum
    out += struct.pack('B', (0 - sum(bytearray(out))) & 0xff)

    return out


def make_product(config):
    product = shared.get_default_product_section()
    product.update(config['product'])

    out = bytes()

    # Language
    out += struct.pack('B', product['language_code'])

    # Strings
    fields = shared.get_product_section_names()

    for key in fields:
        if product[key]:
            value = product[key].encode('ascii')
            out += struct.pack('B%ds' % len(value), len(value) | 0xC0, value)
        else:
            out += struct.pack('B', 0)

    if isinstance(product['custom_fields'], (list, tuple)):
        for record in product['custom_fields']:
            value = record.encode('ascii')
            out += struct.pack('B%ds' % len(value), len(value) | 0xC0, value)

    # No more fields
    out += struct.pack('B', 0xC1)

    # Padding
    while len(out) % 8 != 5:
        out += struct.pack('B', 0)

    # Header version and length in bytes
    out = struct.pack(
        'BB',
        product['format_version'],
        (len(out) + 3) // 8,
    ) + out

    # Checksum
    out += struct.pack('B', (0 - sum(bytearray(out))) & 0xff)

    return out
