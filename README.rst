FRU Tool
########

FRU Tool is a command-line utility for generating and converting IPMI FRU binary data files.


Description
===========

Every modern component of a computer or electronic equipment,
commonly referred to as a Field Replaceable Unit or FRU,
contains a memory block that stores the inventory information of that component.
This includes the manufacturer's name, product name, manufacture date, serial numbers
and other details that help identify the component.

The Intel FRU Information Storage for `IPMI specification`_ defines the standard format
that devices are expected to conform to within their FRU areas.
Each component vendor populates the FRU area during their manufacturing process
and all FRU areas are easily accessible via IPMI.

The OEM FRU storage feature of Dell EMC PowerEdge servers is an additional FRU area that allows OEM customers,
who use Dell EMC servers as a component of their solution,
to include their own tracking information in the FRU storage area.
This can be loaded into the server during factory deployment
and can be accessed when the information is required during troubleshooting or support.
This allows the OEM customers to store their own part numbers and inventory information within the server,
enabling them to track their solutions in their internal management systems.
This is similar to the way Dell EMC servers use the standard FRU areas to store tracking information
such as service tags and manufacture date
and use that information when having to identify and support those systems once in the field.

Considering that the FRU area is a binary payload,
it is not trivial to build the content structure by hand.
To simplify the effort for OEM customers,
this Python tool is provided to speed up the process of creating the payload.

While FRU Tool was specifically authored to support this OEM use case,
it conforms to Intel's specification and can be used to build the FRU structure for any device.


Prerequisites
=============

FRU Tool is tested with Python 3.8 and higher.

In order to write, read, or edit the OEM FRU storage area on the target server,
the open source `IPMItool`_ utility or equivalent is required.
This utility can be installed on Linux distributions by using the built-in package manager such as yum or apt-get.
Dell EMC provides a Windows version which can be found in the *Driver and Downloads* section for any PowerEdge server
on `Dell EMC Support`_ under the *Systems Management* section.
It is contained in the package named *Dell OpenManage BMC Utility* which can also be found on Google by searching for the package by name.
For documentation on IPMItool, search for 'man ipmitool' on Google.


Installation
============

Installation is as simple as running ``python -m pip install fru``.


Usage Instructions
==================

FRU Tool includes a CLI named ``frutool``.
It can be run using either of these methods, depending on how your paths are configured:

..  code-block::

    frutool

    python -m fru

These are equivalent commands.
For convenience, the commands below run as ``frutool``.


Generate a sample text file


To create a complete -- but empty -- text file, run the ``frutool sample`` command:

..  code-block::

    frutool sample EDITABLE.txt


(Change ``EDITABLE.txt`` to whatever filename matches your needs.)

You can then open the text file in any editor and edit its contents.
Note that the file format is TOML;
basic format instructions are included as comments at the top of the sample file.


Convert a binary FRU file to text
---------------------------------

To convert a binary FRU file to an editable text file, run the ``frutool dump`` command:

..  code-block::

    frutool dump FRU.bin EDITABLE.txt


(Change ``FRU.bin`` and ``EDITABLE.txt`` to whatever filenames match your needs.)

You can then review and edit the text file.


Convert a text file to a binary FRU file
----------------------------------------

To convert a text file to binary FRU file, run the ``frutool generate`` command:

..  code-block::

    frutool generate EDITABLE.txt FRU.bin


(Change ``EDITABLE.txt`` and ``FRU.bin`` to whatever filenames match your needs.)

You can then write the binary FRU file to the hardware system using ``ipmitool``:

..  code-block::

    ipmitool -I lanplus -H $IP_ADDRESS -U root -P password fru write FRU.bin


Detailed usage information and use cases for the OEM FRU feature
can be found in the `Dell OEM FRU Whitepaper`_.


Contribution
============

In order to contribute, feel free to fork the project and submit a pull request with all your changes and a description on what was added or removed and why.
If approved, the project owners will merge it.


Licensing
=========

FRU Tool is freely distributed under the MIT License.


Support
=======

Please file bugs and issues on the GitHub issues page for this project.
The code and documentation are released with no warranties or SLAs
and are intended to be supported through a community driven process.


..  Links
..  -----
..
..  _IPMI specification: https://www.intel.com/content/dam/www/public/us/en/documents/specification-updates/ipmi-platform-mgt-fru-info-storage-def-v1-0-rev-1-3-spec-update.pdf
..  _IPMItool: https://codeberg.org/IPMITool/ipmitool
..  _Dell EMC Support: https://support.dell.com
..  _Dell OEM FRU Whitepaper: https://downloads.dell.com/solutions/general-solution-resources/White%20Papers/OEM%20FRU%20Technical%20Whitepaper.pdf
