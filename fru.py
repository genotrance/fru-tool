# fru.py - Generate a binary IPMI FRU data file.
# Copyright (c) 2017 Dell Technologies
#
# https://github.com/genotrance/fru-tool/
#
# Licensed under the terms of the MIT License:
# https://opensource.org/licenses/MIT

import itertools
import os
import struct
import sys

try:
    import configparser
except ImportError:
    import ConfigParser as configparser


__version__ = "1.0"

EXTRAS = ["extra1", "extra2", "extra3", "extra4", "extra5", "extra6", "extra7", "extra8", "extra9"]


def dummystr(length):
    out = "1234567890"
    while len(out) < length:
        out += "1234567890"
    return out[:length]


def read_config(path):
    parser = configparser.ConfigParser()
    parser.read(path)

    config = {
        section: {
            option: parser.get(section, option).strip('"')
            for option in parser.options(section)
        }
        for section in parser.sections()
    }

    integers = [
        ('common', 'size'),
        ('common', 'version'),
    ]

    hex_integers = [
        ('board', 'date'),
        ('board', 'language'),
        ('chassis', 'type'),
        ('product', 'language'),
    ]

    for k in ["internal", "chassis", "board", "product", "multirecord"]:
        config["common"].setdefault(k, "0")
        if config["common"][k] == "1" and k not in config:
            print("Skipping '%s = 1' - [%s] section missing" % (k, k))
            config["common"][k] = "0"
        elif config["common"][k] != "1" and k in config:
            print("Skipping [%s] section - %s != 1" % (k, k))
            del(config[k])
        if k in config["common"]:
            del(config["common"][k])

    for keys in integers:
        if keys[0] in config and keys[1] in config[keys[0]]:
            config[keys[0]][keys[1]] = int(config[keys[0]][keys[1]])

    for keys in hex_integers:
        if keys[0] in config and keys[1] in config[keys[0]]:
            config[keys[0]][keys[1]] = int(config[keys[0]][keys[1]], 16)

    return config


def validate_checksum(blob, offset):
    """Validate a chassis, board, or product checksum.

    *blob is the binary data blob, and *offset* is the integer offset that
    the chassis, board, or product info area starts at.

    :type blob: bytes
    :type offset: int
    """

    length = ord(blob[offset + 1]) * 8
    checksum = ord(blob[offset + length - 1])
    data_sum = sum(ord(c) for c in blob[offset:offset + length - 1]) & 0xff
    if data_sum + checksum != 0x100:
        raise ValueError('The data does not match its checksum.')


def extract_values(blob, offset, names):
    """Extract values that are delimited by type/length bytes.

    The values will be extracted into a dictionary. They'll be saved to keys
    in the same order that keys are provided in *names*. If there are more
    values than key names then additional keys will be generated with the
    names *extra1*, *extra2*, and so forth.

    :type blob: bytes
    :type offset: int
    :type names: list[str]
    """

    data = {}

    extra_names = ('extra{}'.format(i) for i in itertools.count(1))
    for name in itertools.chain(names, extra_names):
        type_length = ord(blob[offset])
        if type_length == 0xc1:
            return data
        length = type_length & 0x3f
        # encoding = (ord(blob[offset]) & 0xc0) >> 6
        data[name] = blob[offset + 1:offset + length + 1].decode('ascii')
        offset += length + 1


def load_bin(path=None, blob=None):
    """Load binary FRU information from a file or binary data blob.

    If *path* is provided, it will be read into memory. If *blob* is provided
    it will be used as-is.

    :type path: str
    :type blob: bytes
    """

    if not path and not blob:
        raise ValueError("You must specify *path* or *blob*.")
    if path and blob:
        raise ValueError("You must specify *path* or *blob*, but not both.")

    if path:
        with open(path, 'rb') as f:
            blob = f.read()

    checksum = ord(blob[7])
    data_checksum = sum(ord(c) for c in blob[:7])
    if checksum + data_checksum != 0x100:
        raise ValueError('The header checksum does not match the header data.')

    version = ord(blob[0])
    internal_offset = ord(blob[1]) * 8
    chassis_offset = ord(blob[2]) * 8
    board_offset = ord(blob[3]) * 8
    product_offset = ord(blob[4]) * 8
    # multirecord_offset = ord(blob[5]) * 8

    data = {'common': {'version': version, 'size': len(blob)}}

    if internal_offset:
        # Not implemented.
        pass

    if chassis_offset:
        validate_checksum(blob, chassis_offset)

        data['chassis'] = {
            'type': ord(blob[chassis_offset + 2]),
        }
        names = ['part', 'serial']
        data['chassis'].update(extract_values(blob, chassis_offset + 3, names))

    if board_offset:
        validate_checksum(blob, board_offset)

        data['board'] = {
            'version': ord(blob[board_offset]),
            'language': ord(blob[board_offset+2]),
            'date': sum([
                ord(blob[board_offset + 3]),
                ord(blob[board_offset + 4]) << 8,
                ord(blob[board_offset + 5]) << 16,
            ]),
        }
        names = ['manufacturer', 'product', 'serial', 'part', 'fileid']
        data['board'].update(extract_values(blob, board_offset + 6, names))

    if product_offset:
        validate_checksum(blob, product_offset)

        data['product'] = {
            'language': ord(blob[product_offset + 2]),
        }
        names = [
            'manufacturer', 'product', 'part', 'version',
            'serial', 'asset', 'fileid',
        ]
        data['product'].update(extract_values(blob, product_offset + 3, names))

    return data


def make_fru(config):
    if "common" not in config:
        raise ValueError("[common] section missing in config")

    if "version" not in config["common"]:
        raise ValueError("'version' missing in [common]")

    if "size" not in config["common"]:
        raise ValueError("'size' missing in [common]")

    internal_offset = 0
    chassis_offset = 0
    board_offset = 0
    product_offset = 0
    multirecord_offset = 0

    chassis = bytes()
    board = bytes()
    product = bytes()
    internal = bytes()

    if "chassis" in config:
        chassis = make_chassis(config)
    if "board" in config:
        board = make_board(config)
    if "product" in config:
        product = make_product(config)
    if "internal" in config:
        internal = make_internal(config)

    pos = 1
    if len(chassis):
        chassis_offset = pos
        pos += int(len(chassis) / 8)
    if len(board):
        board_offset = pos
        pos += int(len(board) / 8)
    if len(product):
        product_offset = pos
        pos += int(len(product) / 8)
    if len(internal):
        internal_offset = pos

    # Header
    out = struct.pack(
        "BBBBBBB",
        int(config["common"].get("version", "1")),
        internal_offset,
        chassis_offset,
        board_offset,
        product_offset,
        multirecord_offset,
        0x00
    )

    # Checksum
    out += struct.pack("B", (0 - sum(bytearray(out))) & 0xff)

    pad = bytes()
    while len(out + chassis + board + product + internal + pad) < int(config["common"]["size"]):
        pad += struct.pack("B", 0)

    if len(out + chassis + board + product + internal + pad) > int(config["common"]["size"]):
        raise ValueError("Too much content, does not fit")

    return out + chassis + board + product + internal + pad


def make_internal(config):
    out = bytes()

    # Data
    if config["internal"].get("data"):
        value = config["internal"]["data"]
        try:
            value = bytes(value, "ascii")
        except TypeError:
            pass
        out += struct.pack("B%ds".encode('ascii') % len(value), int(config["common"].get("version", "1")), value.encode('ascii'))
        print("Adding internal data")
    elif config["internal"].get("file"):
        try:
            value = open(config["internal"]["file"], "r").read()
            try:
                value = bytes(value, "ascii")
            except TypeError:
                pass
            out += struct.pack("B%ds" % len(value), int(config["common"].get("version", "1")), value)
            print("Adding internal file")
        except (configparser.NoSectionError, configparser.NoOptionError, IOError):
            print("Skipping [internal] file %s - missing" % config["internal"]["file"])
    return out


def make_chassis(config):
    out = bytes()

    # Type
    out += struct.pack("B", config["chassis"].get("type", 0))

    # Strings
    fields = ["part", "serial"]
    fields.extend(EXTRAS)
    offset = 0
    print("[Chassis]")
    for k in fields:
        if config["chassis"].get(k):
            value = config["chassis"][k]
            try:
                value = bytes(value, "ascii")
            except TypeError:
                pass
            out += struct.pack("B%ds".encode('ascii') % len(value), len(value) | 0xC0, value.encode('ascii'))
            if "--cmd" in sys.argv:
                print("; ipmitool -I lanplus -H %%IP%% -U root -P password fru edit 17 field c %d %s" % (offset, dummystr(len(value))))
            print("%d: %s = %s (%d)" % (offset, k, value, len(value)))
            offset += 1
        elif k not in EXTRAS:
            out += struct.pack("B", 0)
            offset += 1
    print()

    # No more fields
    out += struct.pack("B", 0xC1)

    # Padding
    while len(out) % 8 != 5:
        out += struct.pack("B", 0)

    # Header version and length in bytes
    out = struct.pack("BB", int(config["common"].get("version", "1")), int((len(out)+3)/8)) + out

    # Checksum
    out += struct.pack("B", (0 - sum(bytearray(out))) & 0xff)

    return out


def make_board(config):
    out = bytes()

    # Language
    out += struct.pack("B", config["board"].get("language", 0))

    # Date
    date = config["board"].get("date", 0)
    out += struct.pack("BBB", date & 0xFF, (date & 0xFF00) >> 8, (date & 0xFF0000) >> 16)

    # Strings
    fields = ["manufacturer", "product", "serial", "part", "fileid"]
    fields.extend(EXTRAS)
    offset = 0
    print("[Board]")
    for k in fields:
        if config["board"].get(k):
            value = config["board"][k]
            try:
                value = bytes(value, "ascii")
            except TypeError:
                pass
            out += struct.pack("B%ds".encode('ascii') % len(value), len(value) | 0xC0, value.encode('ascii'))
            if "--cmd" in sys.argv:
                print("; ipmitool -I lanplus -H %%IP%% -U root -P password fru edit 17 field b %d %s" % (offset, dummystr(len(value))))
            print("%d: %s = %s (%d)" % (offset, k, value, len(value)))
            offset += 1
        elif k not in EXTRAS:
            out += struct.pack("B", 0)
            offset += 1
    print()

    # No more fields
    out += struct.pack("B", 0xC1)

    # Padding
    while len(out) % 8 != 5:
        out += struct.pack("B", 0)

    # Header version and length in bytes
    out = struct.pack("BB", int(config["common"].get("version", "1")), int((len(out)+3)/8)) + out

    # Checksum
    out += struct.pack("B", (0 - sum(bytearray(out))) & 0xff)

    return out


def make_product(config):
    out = bytes()

    # Language
    out += struct.pack("B", config["product"].get("language", 0))

    # Strings
    fields = ["manufacturer", "product", "part", "version", "serial", "asset", "fileid"]
    fields.extend(EXTRAS)
    offset = 0
    print("[Product]")
    for k in fields:
        if config["product"].get(k):
            value = config["product"][k]
            try:
                value = bytes(value, "ascii")
            except TypeError:
                pass
            out += struct.pack("B%ds".encode('ascii') % len(value), len(value) | 0xC0, value.encode('ascii'))
            if "--cmd" in sys.argv:
                print("; ipmitool -I lanplus -H %%IP%% -U root -P password fru edit 17 field p %d %s" % (offset, dummystr(len(value))))
            print("%d: %s = %s (%d)" % (offset, k, value, len(value)))
            offset += 1
        elif k not in EXTRAS:
            out += struct.pack("B", 0)
            offset += 1
    print()

    # No more fields
    out += struct.pack("B", 0xC1)

    # Padding
    while len(out) % 8 != 5:
        out += struct.pack("B", 0)

    # Header version and length in bytes
    out = struct.pack("BB", int(config["common"].get("version", "1")), int((len(out)+3)/8)) + out

    # Checksum
    out += struct.pack("B", (0 - sum(bytearray(out))) & 0xff)

    return out


def run(ini_file, bin_file):  # pragma: nocover
    try:
        configuration = read_config(ini_file)
        blob = make_fru(configuration)
    except ValueError as error:
        print(error.message)
    else:
        open(bin_file, "wb").write(blob)


if __name__ == "__main__":  # pragma: nocover
    if len(sys.argv) < 3:
        print("fru.py input.ini output.bin [--force] [--cmd]")
        sys.exit()

    if not os.path.exists(sys.argv[1]):
        print("Missing INI file %s" % sys.argv[1])
        sys.exit()

    if os.path.exists(sys.argv[2]) and "--force" not in sys.argv:
        print("BIN file %s exists" % sys.argv[2])
        sys.exit()

    run(sys.argv[1], sys.argv[2])
