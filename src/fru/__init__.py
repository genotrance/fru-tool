# fru - Read and write binary IPMI FRU files
# Copyright 2018-2024 Kurt McKee <contactme@kurtmckee.org>
# Copyright 2017 Dell Technologies
#
# https://github.com/kurtmckee/fru-tool/
#
# Licensed under the terms of the MIT License:
# https://opensource.org/licenses/MIT


from .fru_format import dump, load

__all__ = ("dump", "load")
