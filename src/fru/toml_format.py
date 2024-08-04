# fru - Read and write binary IPMI FRU files
# Copyright 2018-2024 Kurt McKee <contactme@kurtmckee.org>
# Copyright 2017 Dell Technologies
#
# https://github.com/kurtmckee/fru-tool/
#
# Licensed under the terms of the MIT License:
# https://opensource.org/licenses/MIT


import datetime
import os
import pathlib
import sys
import textwrap
from importlib.metadata import version
from typing import Dict, List, Tuple, Union

if sys.version_info >= (3, 11):
    import tomllib
else:
    # Compatibility
    import tomli as tomllib

from . import exceptions, shared

min_date = datetime.datetime(1996, 1, 1, 0, 0)  # 0x000000
max_date = datetime.datetime(2027, 11, 24, 20, 15)  # 0xffffff


def convert_str_to_minutes(stamp: str) -> int:
    """Convert a str to the number of minutes since 1996-01-01 00:00."""

    try:
        date = datetime.datetime.strptime(stamp, "%Y-%m-%d %H:%M")
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
        msg = f"*minutes* must be >= 0 (got {minutes})"
        raise exceptions.DateTimeException(msg)

    if minutes > 0xFF_FF_FF:
        msg = f"*minutes* must be <= 0xffffff (got 0x{minutes:x})"
        raise exceptions.DateTimeException(msg)

    date = min_date + datetime.timedelta(minutes=minutes)
    return date.strftime("%Y-%m-%d %H:%M")


def repr_(value: Union[bool, int, str, List]) -> str:
    if isinstance(value, bool):
        return str(bool(value)).lower()
    elif isinstance(value, int):
        return str(value)
    elif isinstance(value, str):
        value = value.replace("\\", "\\\\")
        value = value.replace('"', '\\"')
        return f'"{value}"'
    elif isinstance(value, list):
        output = " ".join(f"{repr_(v)}," for v in value).rstrip(",")
        return f"[{output}]"

    msg = f"Unable to represent {repr(value)} (type={type(value)}) in the TOML format"
    raise exceptions.TOMLException(msg)


def repr_internal(value: bytes) -> str:
    """Represent the internal section as a sequence of bytes."""

    if not value:
        return "[]"

    output = ["["]
    for block in range(0, len(value), 16):
        pieces = []
        for i in value[block : block + 16]:
            pieces.append(f"0x{i:02x}")
        output.append("    " + ", ".join(pieces) + ",")
    output.append("]")
    return "\n".join(output)


def load(
    path: Union[pathlib.Path, str] = None, text: str = None
) -> Dict[str, Dict[str, Union[bytes, int, str]]]:
    """Load a TOML file and return its data as a dictionary.

    If *path* is specified it must be a TOML-formatted file.
    If *text* is specified it must be a TOML-formatted string.
    """

    if not path and not text:
        raise exceptions.FRUException("*path* or *text* must be specified")

    data = {
        "common": shared.get_default_common_section(),
        "board": shared.get_default_board_section(),
        "chassis": shared.get_default_chassis_section(),
        "product": shared.get_default_product_section(),
        "internal": shared.get_default_internal_section(),
    }

    if path:
        with open(path, encoding="utf-8") as file:
            toml_data = tomllib.loads(file.read())
    else:
        toml_data = tomllib.loads(text)

    for section in data:
        if section in toml_data:
            data[section].update(toml_data[section])

    # These values must be integers.
    integers: Tuple[Tuple[str, str], ...] = (
        ("common", "size"),
        ("common", "format_version"),
        ("board", "language_code"),
        ("chassis", "type"),
        ("product", "language_code"),
    )

    dates = (("board", "mfg_date_time"),)

    # Remove sections that are excluded, either explicitly or implicitly.
    for section in ["internal", "chassis", "board", "product", "multirecord"]:
        include_section = f"include_{section}"
        if not data["common"].get(include_section, False) and section in data:
            del data[section]
        if include_section in data["common"]:
            del data["common"][include_section]

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
                data[section][key] = "1996-01-01 00:00"
            if not isinstance(data[section][key], str):
                msg = f'Section [{section}] key "{key}" must be a string'
                raise exceptions.TOMLException(msg)
            data[section][key] = convert_str_to_minutes(data[section][key])

    # Normalize the internal info area data.
    if data.get("internal", {}).get("data"):
        msg = 'Section [internal] key "data" must be a list of numbers or a string'
        try:
            data["internal"]["data"] = bytes(data["internal"]["data"])
        except TypeError:
            try:
                data["internal"]["data"] = data["internal"]["data"].encode("utf8")
            except AttributeError:
                raise exceptions.TOMLException(msg)
    elif data.get("internal", {}).get("file"):
        internal_file = os.path.join(os.path.dirname(path), data["internal"]["file"])
        try:
            with open(internal_file, "rb") as f:
                data["internal"]["data"] = f.read()
        except FileNotFoundError:
            msg = f"Internal info area file {internal_file} not found"
            raise exceptions.TOMLException(msg)
    if "file" in data.get("internal", {}):
        del data["internal"]["file"]

    return data


def dump(data: Dict[str, Dict[str, Union[bytes, int, str]]] = None) -> str:
    """Dump data to the TOML format.

    This function can also generate a blank TOML file.
    """

    data = data or {}
    info = {
        "common": shared.get_default_common_section(),
        "board": shared.get_default_board_section(),
        "chassis": shared.get_default_chassis_section(),
        "product": shared.get_default_product_section(),
    }
    for section in ("common", "board", "chassis", "product"):
        info[section].update(data.get(section, {}))

    output = f"""
        # -------------------------------------------------------------------
        # Generated by frutool {version("fru")}
        # https://github.com/kurtmckee/fru-tool/
        #
        # Notes regarding the TOML format, which is like an INI file:
        #
        # * Values surrounded by quotation marks are strings: "Vendor"
        #   Literal quotation marks must be escaped using a backslash: "\\""
        #   Literal backslashes must also be escaped using a backslash: "\\\\"
        # * Boolean values use the words "true" and "false" without quotes.
        # * Numbers that begin with 0x are interpreted as hexadecimal: 0x30
        #
        # -------------------------------------------------------------------


        [common]
        # Warning: It may be harmful to modify *format_version*.
        format_version = {repr_(info["common"]["format_version"])}

        # Warning: It may be harmful to modify *size*.
        size = {repr_(info["common"]["size"])}

        # These options control which sections are included in the FRU file.
        include_board = {repr_(bool(data.get("board", False)))}
        include_chassis = {repr_(bool(data.get("chassis", False)))}
        include_product = {repr_(bool(data.get("product", False)))}
        include_internal = {repr_(bool(data.get("internal", False)))}
        include_multirecord = {repr_(bool(data.get("multirecord", False)))}


        [board]
        # Warning: It may be harmful to modify *format_version*.
        format_version = {repr_(info["board"]["format_version"])}

        language_code = {repr_(info["board"]["language_code"])}

        mfg_date_time = "{convert_minutes_to_str(info["board"]["mfg_date_time"])}"
        #                │    │  │  │  │
        #         year ──┘    │  │  │  ╰── minutes
        #             month ──╯  │  ╰── hours
        #                  day ──╯

        manufacturer = {repr_(info["board"]["manufacturer"])}
        product_name = {repr_(info["board"]["product_name"])}
        serial_number = {repr_(info["board"]["serial_number"])}
        part_number = {repr_(info["board"]["part_number"])}
        fru_file_id = {repr_(info["board"]["fru_file_id"])}
        custom_fields = {repr_(info["board"]["custom_fields"])}


        [chassis]
        # Warning: It may be harmful to modify *format_version*.
        format_version = {repr_(info["chassis"]["format_version"])}

        type = {repr_(info["chassis"]["type"])}
        part_number = {repr_(info["chassis"]["part_number"])}
        serial_number = {repr_(info["chassis"]["serial_number"])}
        custom_fields = {repr_(info["chassis"]["custom_fields"])}


        [product]
        # Warning: It may be harmful to modify *format_version*.
        format_version = {repr_(info["product"]["format_version"])}

        language_code = {repr_(info["product"]["language_code"])}
        manufacturer = {repr_(info["product"]["manufacturer"])}
        product_name = {repr_(info["product"]["product_name"])}
        part_number = {repr_(info["product"]["part_number"])}
        product_version = {repr_(info["product"]["product_version"])}
        serial_number = {repr_(info["product"]["serial_number"])}
        asset_tag = {repr_(info["product"]["asset_tag"])}
        fru_file_id = {repr_(info["product"]["fru_file_id"])}
        custom_fields = {repr_(info["product"]["custom_fields"])}


        [internal]
        # Warning: It may be harmful to modify *format_version*.
        format_version = {repr_(data.get("internal", {}).get("format_version", 1))}

        # The *data* key can be used to encode a sequence of bytes serialized
        # as a list of numbers. For small amounts of internal data this might
        # be sufficient.
        #
        # Alternatively, if the *file* key is specified then the file will be
        # opened and read in binary mode.
        #
        # Examples:
        #
        #     data = [0x01, 0x02, 0x03]
        #     file = "path/to/file"
        #
        # Do not use the *data* and *file* keys at the same time.

        data = {repr_internal(data.get("internal", {}).get("data", b""))}
    """

    return textwrap.dedent(output).strip() + "\n"
