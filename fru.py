# fru.py - Generate a binary IPMI FRU data file.
# Copyright (c) 2017 Dell Technologies
#
# https://github.com/genotrance/fru-tool/
#
# Licensed under the terms of the MIT License:
# https://opensource.org/licenses/MIT

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

    if "common" not in config:
        raise ValueError("[common] section missing in config")

    if "version" not in config["common"]:
        raise ValueError("'version' missing in [common]")

    if "size" not in config["common"]:
        raise ValueError("'size' missing in [common]")

    for k in ["internal", "chassis", "board", "product", "multirecord"]:
        config["common"].setdefault(k, "0")
        if config["common"][k] == "1" and k not in config:
            print("Skipping '%s = 1' - [%s] section missing" % (k, k))
            config["common"][k] = "0"
        elif config["common"][k] != "1" and k in config:
            print("Skipping [%s] section - %s != 1" % (k, k))
            del(config[k])

    return config


def make_fru(config):
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
        int(config["common"]["version"]),
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
        out += struct.pack("B%ds" % len(value), int(config["common"]["version"]), value)
        print("Adding internal data")
    elif config["internal"].get("file"):
        try:
            value = open(config["internal"]["file"], "r").read()
            try:
                value = bytes(value, "ascii")
            except TypeError:
                pass
            out += struct.pack("B%ds" % len(value), int(config["common"]["version"]), value)
            print("Adding internal file")
        except (configparser.NoSectionError, configparser.NoOptionError, IOError):
            print("Skipping [internal] file %s - missing" % config["internal"]["file"])
    return out


def make_chassis(config):
    out = bytes()

    # Type
    out += struct.pack("B", int(config["chassis"].get("type", "0"), 16))

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
            out += struct.pack("B%ds" % len(value), len(value) | 0xC0, value)
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
    out = struct.pack("BB", int(config["common"]["version"]), int((len(out)+3)/8)) + out

    # Checksum
    out += struct.pack("B", (0 - sum(bytearray(out))) & 0xff)

    return out


def make_board(config):
    out = bytes()

    # Language
    out += struct.pack("B", int(config["board"].get("language", "0"), 16))

    # Date
    date = int(config["board"].get("date", "0"), 16)
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
            out += struct.pack("B%ds" % len(value), len(value) | 0xC0, value)
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
    out = struct.pack("BB", int(config["common"]["version"]), int((len(out)+3)/8)) + out

    # Checksum
    out += struct.pack("B", (0 - sum(bytearray(out))) & 0xff)

    return out


def make_product(config):
    out = bytes()

    # Language
    out += struct.pack("B", int(config["product"].get("language", "0"), 16))

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
            out += struct.pack("B%ds" % len(value), len(value) | 0xC0, value)
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
    out = struct.pack("BB", int(config["common"]["version"]), int((len(out)+3)/8)) + out

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
