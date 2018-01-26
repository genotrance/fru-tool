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

CONFIG = None
VERSION = 1
EXTRAS = ["extra1", "extra2", "extra3", "extra4", "extra5", "extra6", "extra7", "extra8", "extra9"]


def dummystr(length):
    out = "1234567890"
    while len(out) < length:
        out += "1234567890"
    return out[:length]


def read_config(path):
    global CONFIG
    global VERSION

    CONFIG = configparser.ConfigParser()
    CONFIG.read(path)

    if "common" not in CONFIG.sections():
        print("[common] section missing in config")
        sys.exit()

    if "version" not in CONFIG.options("common"):
        print("'version' missing in [common]")
        sys.exit()
    else:
        VERSION = int(CONFIG.get("common", "version"))

    if "size" not in CONFIG.options("common"):
        print("'size' missing in [common]")
        sys.exit()

    for i in ["internal", "chassis", "board", "product", "multirecord"]:
        if i in CONFIG.options("common") and CONFIG.get("common", i) == "1":
            if i not in CONFIG.sections():
                print("Skipping '%s = 1' - [%s] section missing" % (i, i))
                CONFIG.set("common", i, "0")


def make_fru():
    internal_offset = 0
    chassis_offset = 0
    board_offset = 0
    product_offset = 0
    multirecord_offset = 0

    chassis = make_chassis()
    board = make_board()
    product = make_product()
    internal = make_internal()

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
        VERSION,
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
    while len(out + chassis + board + product + internal + pad) < int(CONFIG.get("common", "size")):
        pad += struct.pack("B", 0)

    if len(out + chassis + board + product + internal + pad) > int(CONFIG.get("common", "size")):
        print("Too much content, does not fit")
        sys.exit()

    return out + chassis + board + product + internal + pad


def make_internal():
    out = bytes()
    if "internal" in CONFIG.options("common") and CONFIG.get("common", "internal") == "1":
        # Data
        if "data" in CONFIG.options("internal") and CONFIG.get("internal", "data") != "":
            value = CONFIG.get("internal", "data")
            try:
                value = bytes(value, "ascii")
            except TypeError:
                pass
            out += struct.pack("B%ds" % len(value), VERSION, value)
            print("Adding internal data")
        elif "file" in CONFIG.options("internal") and CONFIG.get("internal", "file") != "":
            try:
                value = open(CONFIG.get("internal", "file"), "r").read()
                try:
                    value = bytes(value, "ascii")
                except TypeError:
                    pass
                out += struct.pack("B%ds" % len(value), VERSION, value)
                print("Adding internal file")
            except (configparser.NoSectionError, configparser.NoOptionError, IOError):
                print("Skipping [internal] file %s - missing" % CONFIG.get("internal", "file"))
    return out


def make_chassis():
    out = bytes()
    if "chassis" in CONFIG.options("common") and CONFIG.get("common", "chassis") == "1":
        # Type
        if "type" in CONFIG.options("chassis") and CONFIG.get("chassis", "type") != "":
            out += struct.pack("B", int(CONFIG.get("chassis", "type"), 16))
        else:
            out += struct.pack("B", 0)

        # Strings
        fields = ["part", "serial"]
        fields.extend(EXTRAS)
        offset = 0
        print("[Chassis]")
        for i in fields:
            if i in CONFIG.options("chassis") and CONFIG.get("chassis", i) != "":
                value = CONFIG.get("chassis", i).strip('"')
                try:
                    value = bytes(value, "ascii")
                except TypeError:
                    pass
                out += struct.pack("B%ds" % len(value), len(value) | 0xC0, value)
                if "--cmd" in sys.argv:
                    print("; ipmitool -I lanplus -H %%IP%% -U root -P password fru edit 17 field c %d %s" % (offset, dummystr(len(value))))
                print("%d: %s = %s (%d)" % (offset, i, value, len(value)))
                offset += 1
            elif i not in EXTRAS:
                out += struct.pack("B", 0)
                offset += 1
        print()

        # No more fields
        out += struct.pack("B", 0xC1)

        # Padding
        while len(out) % 8 != 5:
            out += struct.pack("B", 0)

        # Header version and length in bytes
        out = struct.pack("BB", VERSION, int((len(out)+3)/8)) + out

        # Checksum
        out += struct.pack("B", (0 - sum(bytearray(out))) & 0xff)

    return out


def make_board():
    out = bytes()
    if "board" in CONFIG.options("common") and CONFIG.get("common", "board") == "1":
        # Language
        if "language" in CONFIG.options("board") and CONFIG.get("board", "language") != "":
            out += struct.pack("B", int(CONFIG.get("board", "language"), 16))
        else:
            out += struct.pack("B", 0)

        # Date
        if "date" in CONFIG.options("board") and CONFIG.get("board", "date") != "":
            date = int(CONFIG.get("board", "date"), 16)
            out += struct.pack("BBB", date & 0xFF, (date & 0xFF00) >> 8, (date & 0xFF0000) >> 16)
        else:
            out += struct.pack("BBB", 0, 0, 0)

        # Strings
        fields = ["manufacturer", "product", "serial", "part", "fileid"]
        fields.extend(EXTRAS)
        offset = 0
        print("[Board]")
        for i in fields:
            if i in CONFIG.options("board") and CONFIG.get("board", i) != "":
                value = CONFIG.get("board", i).strip('"')
                try:
                    value = bytes(value, "ascii")
                except TypeError:
                    pass
                out += struct.pack("B%ds" % len(value), len(value) | 0xC0, value)
                if "--cmd" in sys.argv:
                    print("; ipmitool -I lanplus -H %%IP%% -U root -P password fru edit 17 field b %d %s" % (offset, dummystr(len(value))))
                print("%d: %s = %s (%d)" % (offset, i, value, len(value)))
                offset += 1
            elif i not in EXTRAS:
                out += struct.pack("B", 0)
                offset += 1
        print()

        # No more fields
        out += struct.pack("B", 0xC1)

        # Padding
        while len(out) % 8 != 5:
            out += struct.pack("B", 0)

        # Header version and length in bytes
        out = struct.pack("BB", VERSION, int((len(out)+3)/8)) + out

        # Checksum
        out += struct.pack("B", (0 - sum(bytearray(out))) & 0xff)

    return out


def make_product():
    out = bytes()
    if "product" in CONFIG.options("common") and CONFIG.get("common", "product") == "1":
        # Language
        if "language" in CONFIG.options("product") and CONFIG.get("product", "language") != "":
            out += struct.pack("B", int(CONFIG.get("product", "language"), 16))
        else:
            out += struct.pack("B", 0)

        # Strings
        fields = ["manufacturer", "product", "part", "version", "serial", "asset", "fileid"]
        fields.extend(EXTRAS)
        offset = 0
        print("[Product]")
        for i in fields:
            if i in CONFIG.options("product") and CONFIG.get("product", i) != "":
                value = CONFIG.get("product", i).strip('"')
                try:
                    value = bytes(value, "ascii")
                except TypeError:
                    pass
                out += struct.pack("B%ds" % len(value), len(value) | 0xC0, value)
                if "--cmd" in sys.argv:
                    print("; ipmitool -I lanplus -H %%IP%% -U root -P password fru edit 17 field p %d %s" % (offset, dummystr(len(value))))
                print("%d: %s = %s (%d)" % (offset, i, value, len(value)))
                offset += 1
            elif i not in EXTRAS:
                out += struct.pack("B", 0)
                offset += 1
        print()

        # No more fields
        out += struct.pack("B", 0xC1)

        # Padding
        while len(out) % 8 != 5:
            out += struct.pack("B", 0)

        # Header version and length in bytes
        out = struct.pack("BB", VERSION, int((len(out)+3)/8)) + out

        # Checksum
        out += struct.pack("B", (0 - sum(bytearray(out))) & 0xff)

    return out


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("fru.py fru.ini fru.bin [--force][--cmd]")
        sys.exit()

    if not os.path.exists(sys.argv[1]):
        print("Missing INI file %s" % sys.argv[1])
        sys.exit()

    if os.path.exists(sys.argv[2]) and "--force" not in sys.argv:
        print("BIN file %s exists" % sys.argv[2])
        sys.exit()

    read_config(sys.argv[1])
    blob = make_fru()
    f = open(sys.argv[2], "wb").write(blob)
