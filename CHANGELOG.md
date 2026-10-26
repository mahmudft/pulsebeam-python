# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-10-26

### Added
- `Table[Row, Insert]` declarations and an immutable `SelectQuery` builder with comparison,
  pattern, `in`, `is`, ordering, paging and count support.
- `Table.insert()` producing an `InsertQuery` checked against the table's insert type.
- `execute()` on both clients, overloaded to return `Page[Row]` or `list[Row]`.
- `PostgrestError`, `UnexpectedResponseError` and `PulsebeamConnectionError` under a common
  `PulsebeamError`.
- Docker Compose setup with a seeded PostgREST, integration tests and a runnable example.
