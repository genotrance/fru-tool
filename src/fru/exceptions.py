# fru - Read and write binary IPMI FRU files
# Copyright 2018-2021 Kurt McKee <contactme@kurtmckee.org>
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
    the number of minutes since 1996-01-01T00:00:00. This forces all
    dates and times to stay within a certain range, and prevents seconds
    from being represented.
    """


class DateTimeIncorrectFormat(DateTimeException):
    """A date/time with an invalid format was encountered."""


class DateTimeTooLow(DateTimeException):
    """A date/time before 1996-01-01T00:00:00 was encountered."""


class DateTimeTooHigh(DateTimeException):
    """A date/time after 2027-11-24T20:15:00 was encountered."""


class DateTimeIncludesSeconds(DateTimeException):
    """A date/time with seconds specified was encountered."""
