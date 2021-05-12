# fru - Read and write binary IPMI FRU files
# Copyright 2018-2021 Kurt McKee <contactme@kurtmckee.org>
# Copyright 2017 Dell Technologies
#
# https://github.com/kurtmckee/fru-tool/
#
# Licensed under the terms of the MIT License:
# https://opensource.org/licenses/MIT

import os
import sys

from . import api


def run_cli():
    if len(sys.argv) < 3:
        print('fru-cli input.ini output.bin [--force] [--cmd]')
        sys.exit(1)

    ini_file = sys.argv[1]
    bin_file = sys.argv[2]

    if not os.path.exists(ini_file):
        print(f'Missing INI file {ini_file}')
        sys.exit(1)

    if os.path.exists(bin_file) and '--force' not in sys.argv:
        print(f'BIN file {bin_file} exists')
        sys.exit(1)

    try:
        configuration = api.read_config(ini_file)
        blob = api.dump(configuration)
    except ValueError as error:
        print(error.args[0])
    else:
        with open(bin_file, 'wb') as file:
            file.write(blob)
