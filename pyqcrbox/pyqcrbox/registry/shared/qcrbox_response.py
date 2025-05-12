import datetime
from typing import Any

from litestar.response import Response


class QCrBoxResponse(Response):
    """Custom response class for QCrBox API responses.

    This class sets the default content type to JSON and adds a timestamp.
    """

    def __init__(self, content: Any, *args, **kwargs):
        # If the content type if a dict/json, add a timestamp to the end
        if isinstance(content, dict):
            content.setdefault("timestamp", datetime.datetime.now(tz=datetime.UTC).isoformat() + "Z")
            kwargs["media_type"] = "application/json"

        # Get everything else from the parent class, so this should behave as
        # a normal response otherwise
        super().__init__(content, *args, **kwargs)
