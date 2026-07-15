# SPDX-License-Identifier: MPL-2.0
"""Artifact kinds for typed command return values.

Commands can return, besides at most one pipeline-continuing CIF, any number
of typed artifacts. The kind determines how the frontend renders the file and
which media type it is served with. Pipeline CIFs and plain uploads carry no
kind (``None``).
"""

from enum import Enum
from pathlib import Path

__all__ = ["ArtifactKind", "media_type_for_data_file"]


class ArtifactKind(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    HTML = "html"
    INTERACTIVE_STRUCTURE = "interactive_structure"
    INTERACTIVE_GRAPH = "interactive_graph"


_IMAGE_MEDIA_TYPES = {
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "gif": "image/gif",
    "svg": "image/svg+xml",
    "webp": "image/webp",
}

# Fallback media types for files WITHOUT an artifact kind (pipeline CIFs,
# plain uploads). Deliberately never text/html: an undeclared .html upload is
# served as plain text so executable HTML cannot be smuggled in through the
# generic upload path.
_KINDLESS_MEDIA_TYPES = {
    "cif": "chemical/x-cif",
    "fcf": "chemical/x-cif",
    "txt": "text/plain",
    "json": "application/json",
    "html": "text/plain",
    "htm": "text/plain",
}


def media_type_for_data_file(kind: str | None, filename: str) -> str:
    """Return the media type for serving a data file inline.

    The artifact kind takes precedence; for kind-less files a conservative
    extension-based fallback is used (never text/html). Media types are
    returned WITHOUT a charset parameter - Litestar appends `; charset=utf-8`
    to text/* types itself.
    """
    extension = Path(filename).suffix[1:].lower()
    match kind:
        case ArtifactKind.TEXT:
            return "text/plain"
        case ArtifactKind.HTML:
            return "text/html"
        case ArtifactKind.INTERACTIVE_STRUCTURE:
            return "chemical/x-cif"
        case ArtifactKind.INTERACTIVE_GRAPH:
            return "application/json"
        case ArtifactKind.IMAGE:
            return _IMAGE_MEDIA_TYPES.get(extension, "application/octet-stream")
        case _:
            return _KINDLESS_MEDIA_TYPES.get(extension, "application/octet-stream")
