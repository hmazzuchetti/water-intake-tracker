"""Single source of truth for the app version.

Bump rules (Semantic Versioning 2.0.0):
  - MAJOR: backwards-incompatible change in UX/data format
  - MINOR: backwards-compatible new feature
  - PATCH: backwards-compatible bug fix or hardening

When bumping here, also update `installer.iss` (`MyAppVersion`).
"""

__version__ = "2.2.0"
