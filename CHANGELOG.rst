..
    This is the FRU Tool changelog.

    It is managed and updated by scriv during development.
    Please do not edit this file directly.
    Instead, run "scriv create" to create a new changelog fragment.


Changelog
*********


Unreleased changes
==================

Please see the fragment files in the `changelog.d directory`_.

..  _changelog.d directory: https://github.com/genotrance/fru-tool/tree/main/changelog.d


..  scriv-insert-here

.. _changelog-4.1.0:

4.1.0 - 2024-09-26
==================

Added
-----

-   Decode FRU fields encoded using 6-bit ASCII.

    Note that it is currently not possible to encode fields back to 6-bit ASCII.

.. _changelog-4.0.2:

4.0.2 - 2024-08-04
==================

Changed
-------

-   Exclude FRU sections when the associated ``include_*`` key
    has been removed from the ``[common]`` section. (#21)

    The previous behavior was to assume a section should be included
    unless the associated ``include_*`` key was explicitly set to false.

.. _changelog-4.0.1:

4.0.1 - 2024-05-30
==================

Fixed
-----

- Always specify UTF-8 encoding when reading TOML files.

.. _changelog-4.0.0:

4.0.0 - 2024-04-13
==================

Python support
--------------

*   Support Python 3.8 and higher.

Documentation
-------------

*   Overhaul the README.
*   Add a CHANGELOG.

Development
-----------

*   Add configurations for common tools:

    *   Dependabot
    *   EditorConfig
    *   pre-commit

*   Add a GitHub workflow to test the project.
*   Allow project dependencies to auto-update by running ``tox run -m update``.
*   Prepare to test the project using mypy.
