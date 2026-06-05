"""Vault migration protocol - full snapshot export/import.

Phase 1 (current): snapshot mode. Export creates a portable archive
(.eidolon_keybundle_full) containing the identity files (.psnx, .blend_data)
plus all vault-scoped state (persistent vault data, runtime cycles,
escrowed documents, distribution caches). Source machine is NOT sealed
after export, so the user is responsible for not forking by using two
machines concurrently.

Phase 2+ will add a "transfer mode" with cryptographic sealing that
prevents source-machine reuse until the archive is confirmed imported.

Public API:

    from src.protocols.vault_migration import (
        export_vault, import_vault, inspect_archive,
        ExportError, ImportError,
        MIGRATION_FILE_SUFFIX,
    )
"""

from .exporter import export_vault, ExportError
from .importer import import_vault, inspect_archive, ImportError, ImportConflict
from .format_version import (
    CURRENT_SCHEMA_VERSION,
    CURRENT_FORMAT_SUITE,
    MIGRATION_FILE_SUFFIX,
    PRODUCER_TAG,
)

__all__ = [
    "export_vault",
    "import_vault",
    "inspect_archive",
    "ExportError",
    "ImportError",
    "ImportConflict",
    "CURRENT_SCHEMA_VERSION",
    "CURRENT_FORMAT_SUITE",
    "MIGRATION_FILE_SUFFIX",
    "PRODUCER_TAG",
]
