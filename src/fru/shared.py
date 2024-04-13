# fru - Read and write binary IPMI FRU files
# Copyright 2018-2024 Kurt McKee <contactme@kurtmckee.org>
# Copyright 2017 Dell Technologies
#
# https://github.com/kurtmckee/fru-tool/
#
# Licensed under the terms of the MIT License:
# https://opensource.org/licenses/MIT


from typing import Dict, Tuple, Union


def get_default_common_section() -> Dict[str, int]:
    """Create an empty common section with default values."""

    return {
        "format_version": 1,
        "size": 0,  # Guarantee an error if this is not updated.
    }


def get_default_board_section() -> Dict[str, Union[int, str, list]]:
    """Create an empty board section with default values."""

    return {
        "format_version": 1,
        "language_code": 0,
        "mfg_date_time": 0,
        "manufacturer": "",
        "product_name": "",
        "serial_number": "",
        "part_number": "",
        "fru_file_id": "",
        "custom_fields": [],
    }


def get_board_section_names() -> Tuple[str, ...]:
    """Get the list of board section names, in their correct order."""

    return (
        "manufacturer",
        "product_name",
        "serial_number",
        "part_number",
        "fru_file_id",
    )


def get_default_chassis_section() -> Dict[str, Union[int, str, list]]:
    """Create an empty chassis section with default values."""

    return {
        "format_version": 1,
        "type": 0,
        "part_number": "",
        "serial_number": "",
        "custom_fields": [],
    }


def get_chassis_section_names() -> Tuple[str, ...]:
    """Get the list of chassis section names, in their correct order."""

    return (
        "part_number",
        "serial_number",
    )


def get_default_product_section() -> Dict[str, Union[int, str, list]]:
    """Create an empty product section with default values."""

    return {
        "format_version": 1,
        "language_code": 0,
        "manufacturer": "",
        "product_name": "",
        "part_number": "",
        "product_version": "",
        "serial_number": "",
        "asset_tag": "",
        "fru_file_id": "",
        "custom_fields": [],
    }


def get_product_section_names() -> Tuple[str, ...]:
    """Get the list of product section names, in their correct order."""

    return (
        "manufacturer",
        "product_name",
        "part_number",
        "product_version",
        "serial_number",
        "asset_tag",
        "fru_file_id",
    )


def get_default_internal_section() -> Dict[str, Union[int, bytes]]:
    """Create an empty internal section with default values."""

    return {
        "format_version": 1,
        "data": b"",
    }
