import datetime

from litestar.response import Response


class QCrBoxResponse(Response):
    """Custom response class for QCrBox API responses.

    This class sets the default content type to JSON and adds a timestamp.
    """

    def __init__(self, content: dict, *args, **kwargs):
        content.setdefault("timestamp", datetime.datetime.now(tz=datetime.UTC).isoformat() + "Z")
        super().__init__(content, media_type="application/json", *args, **kwargs)
