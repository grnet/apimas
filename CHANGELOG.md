# Change Log
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/)
and this project adheres to [Semantic Versioning](http://semver.org/).

## [0.4] - Unreleased
### Changed
- This version brings major backwards-incompatible changes.

### Removed
- Support for DRF was dropped in favor of a native django support

## [0.3.3] - 2018-02-15
### Fixed
- Proper format for datetime field

### Added
- Support for decimal field

## [0.3.2] - 2018-01-25
### Fixed
- Specify compatible versions of dependencies.

## [0.3.1] - 2017-08-03
### Fixed
- Regular expressions for validating email addresses.

## [0.3] - 2017-03-24
### Added
- Specification can now specify multiple endpoints.
- Informative error messages when handling the specification.
- CLI subcommands for every endpoint.
- An optional `--config` CLI option to specify the location of
  specification.
- New field predicates: `.choices` and `.text`.
- New `max_length` parameter for `.string` fields.

### Changed
- The DRF-specific code is split off in a separate package `apimas_drf`.
- `.endpoint` is no longer top-level; it now describes its parent node.
- A reference to a collection must now be prefixed by its endpoint.
- API of testing utility methods used by developers.
- `format` parameter of `.date` and `.datetime` fields now expects a list of
  string formats.
- `.cli_auth` now gets two parameters:
  a) `format` (the credentials file format),
  b) `schema` (the credentials schema).
- Adapter method `apply()` is removed; its functionality is merged into
  construct().
- `mkdeb` script is installed along with apimas.

### Fixed
- Client side data validation between two consecutive calls.

[Unreleased]: https://github.com/grnet/apimas
[0.3.3]: https://github.com/grnet/apimas/tree/0.3.3
[0.3.2]: https://github.com/grnet/apimas/tree/0.3.2
[0.3.1]: https://github.com/grnet/apimas/tree/0.3.1
[0.3]: https://github.com/grnet/apimas/tree/0.3
