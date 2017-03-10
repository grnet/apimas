# Change Log
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/)
and this project adheres to [Semantic Versioning](http://semver.org/).

## [Unreleased]
### Added
- max_length` parameter for `.string` fields.
- Informative messages when an error occurs during the conversion
  of specification into implementation.
- Multiple endpoints specified on one specification. Therefore, in order
  to refer to a collection, you also need to provide the endpoint to which
  it belongs.
- `.choices` field predicate.
- Subcommands for every endpoint, provided by CLI adapter.
- An optional `--config` option for `apimas` command to specify the
  location of specification.
- `.text` field predicate.

### Changed
- `mkdeb` script is installed together with the apimas.
- API of testing utility methods used by developers.
- `.endpoint` is no longer top-level. It describes the parent node based
  on specification.
- Each implementation item (e.g. a client object, a drf view) is associated
  with an endpoint and a collection.
- `format` parameter of `.date` and `.datetime` fields gets a list
  string formats of the respective date and datetime fields instead of only
  one.
- Parameters of `.cli_auth` is changed. Now, it gets two parameters
  a) `format`, i.e. the format of the file where credentials are stored
  (e.g. JSON or YAML), b) `schema`, i.e. the schema of credentials.
- Remove `apply()` method from every adapter class.
- Package is split into two namespace packages: a) `apimas` package which
  includes interfaces for creating an adapter, CLI and client adapters, and
  puppet and scripts for deploying an application, and creating Debian packages.
  b) `apimas_drf` which provides an adapter for creating a Django application.

### Fixed
- Old-style python string formatting is replaced with the new one. 
- Data validation (from client side) between two consecutive client calls.

[Unreleased]: https://github.com/grnet/apimas/
