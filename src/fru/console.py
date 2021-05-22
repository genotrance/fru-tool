# fru - Read and write binary IPMI FRU files
# Copyright 2018-2021 Kurt McKee <contactme@kurtmckee.org>
# Copyright 2017 Dell Technologies
#
# https://github.com/kurtmckee/fru-tool/
#
# Licensed under the terms of the MIT License:
# https://opensource.org/licenses/MIT


import json
import os
import pathlib
import sys

import click

from . import fru_format
from . import toml_format


@click.group()
@click.version_option()
def run():
    pass


@click.command('generate', no_args_is_help=True)
@click.argument('toml_file', type=click.Path(exists=True, dir_okay=False, resolve_path=True, path_type=pathlib.Path))
@click.argument('fru_file', type=click.Path(exists=False, dir_okay=False, resolve_path=True, path_type=pathlib.Path))
@click.option('--force', is_flag=True, help='Overwrite an existing file if it already exists.')
def run_generate(toml_file: pathlib.Path, fru_file: pathlib.Path, force: bool):
    """Generate a binary FRU file using data in a TOML file."""

    if fru_file.exists() and not force:
        click.echo(f'{fru_file} exists and will not be overwritten.')
        sys.exit(1)

    try:
        data = toml_format.load(toml_file)
        blob = fru_format.dump(data)
    except ValueError as error:
        click.echo(error.args[0])
        sys.exit(1)

    with open(fru_file, 'wb') as file:
        file.write(blob)


@click.command('dump', no_args_is_help=True)
@click.argument('fru_file', type=click.Path(exists=True, dir_okay=False, resolve_path=True, path_type=pathlib.Path))
@click.argument('toml_file', type=click.Path(exists=False, dir_okay=False, resolve_path=True, path_type=pathlib.Path), required=False)
@click.option('--force', is_flag=True, help='Overwrite an existing file if it already exists.')
def run_dump(fru_file: pathlib.Path, toml_file: pathlib.Path, force: bool):
    """Dump data from a binary FRU file to the TOML file format."""

    if toml_file and toml_file.exists() and not force:
        click.echo(f'{toml_file} exists and will not be overwritten.')
        sys.exit(1)

    try:
        data = fru_format.load(path=fru_file)
    except ValueError as error:
        click.echo(error.args[0])
        sys.exit(1)

    output = toml_format.dump(data)
    if toml_file:
        with toml_file.open('wt', encoding='utf8') as file:
            file.write(output)
    else:
        click.echo(output)


@click.command('sample')
@click.argument('toml_file', type=click.Path(exists=False, dir_okay=False, resolve_path=True, path_type=pathlib.Path), required=False)
@click.option('--force', is_flag=True, help='Overwrite an existing file if it already exists.')
def run_sample(toml_file, force: bool):
    """Generate a blank TOML document."""

    if toml_file and toml_file.exists() and not force:
        click.echo(f'{toml_file} exists and will not be overwritten.')
        sys.exit(1)

    output = toml_format.dump()
    if toml_file:
        with toml_file.open('wt', encoding='utf8') as file:
            file.write(output)
    else:
        click.echo(output)


run.add_command(run_generate)
run.add_command(run_dump)
run.add_command(run_sample)
