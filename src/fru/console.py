# fru - Read and write binary IPMI FRU files
# Copyright 2018-2021 Kurt McKee <contactme@kurtmckee.org>
# Copyright 2017 Dell Technologies
#
# https://github.com/kurtmckee/fru-tool/
#
# Licensed under the terms of the MIT License:
# https://opensource.org/licenses/MIT

import os
import pathlib
import sys

import click

from . import api


@click.command(no_args_is_help=True)
@click.argument('ini_file', type=click.Path(exists=True, dir_okay=False, resolve_path=True, path_type=pathlib.Path))
@click.argument('bin_file', type=click.Path(exists=False, dir_okay=False, resolve_path=True, path_type=pathlib.Path))
@click.option('--force', is_flag=True, help='Overwrite an existing file if it already exists.')
@click.version_option()
def run_cli(ini_file: pathlib.Path, bin_file: pathlib.Path, force: bool):
    if bin_file.exists() and not force:
        click.echo(f'{bin_file} exists and will not be overwritten.')
        sys.exit(1)

    try:
        configuration = api.read_config(ini_file)
        blob = api.dump(configuration)
    except ValueError as error:
        click.echo(error.args[0])
        sys.exit(1)
    else:
        with open(bin_file, 'wb') as file:
            file.write(blob)
