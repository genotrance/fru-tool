# fru - Read and write binary IPMI FRU files
# Copyright 2018-2024 Kurt McKee <contactme@kurtmckee.org>
# Copyright 2017 Dell Technologies
#
# https://github.com/kurtmckee/fru-tool/
#
# Licensed under the terms of the MIT License:
# https://opensource.org/licenses/MIT


class FRUException(Exception):
    """Base exception for the fru module."""


class DateTimeException(FRUException):
    """A date or time error was encountered.

    The FRU format stores dates and times as three bytes representing
    the number of minutes since 1996-01-01 at 00:00. This forces all
    dates and times to stay within a certain range, and prevents seconds
    from being represented.
    """


class TOMLException(FRUException):
    """An error was encountered while encoding or decoding TOML."""
