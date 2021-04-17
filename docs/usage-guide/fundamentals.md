# Usage Guide

This section provides detailed descriptions of all the ways `instagrapi` can be used. If you are new to `instagrapi`, the
[Getting Started][getting-started] page provides a gradual introduction of the basic functionality with examples.

## Public vs Private Requests

* `Public` (anonymous request via web api) methods have a suffix `_gql` (Instagram `GraphQL`) or `_a1` (example `https://www.instagram.com/adw0rd/?__a=1`)
* `Private` (authorized request via mobile api) methods have `_v1` suffix

The first request to fetch media/user is `public` (anonymous), if instagram raise exception, then use `private` (authorized).

## Detailed Sections

* [Interactions][interactions]
* [Optional Questions & Branching][optional-questions]
* [Validators][validators]
* [Command Line Interface][command-line]

[getting-started]: ../getting-started.md
[interactions]: interactions.md