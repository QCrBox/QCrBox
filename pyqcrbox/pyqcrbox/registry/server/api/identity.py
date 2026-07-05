"""Resolution of the acting user's identity from request headers.

Two trusted identity paths exist (identity is always optional — requests
without valid identity headers proceed as anonymous):

1. `X-QCrBox-User` + `X-QCrBox-Service-Token`: trusted services (e.g. the web
   frontend, which calls the registry directly on the docker network) act on
   behalf of an end user. The claimed username is honoured only when a service
   token is configured AND the provided token matches.
2. `Remote-User`: injected by Authelia for requests arriving via Traefik.
"""

import secrets

from litestar import Request

from pyqcrbox.settings import settings

__all__ = ["get_current_user"]


async def get_current_user(request: Request) -> str | None:
    """Resolve the acting user's username from the request headers, if any."""
    claimed_user = request.headers.get("x-qcrbox-user")
    if claimed_user:
        configured_token = settings.auth.service_token
        provided_token = request.headers.get("x-qcrbox-service-token")
        if configured_token and provided_token and secrets.compare_digest(provided_token, configured_token):
            return claimed_user

    if settings.auth.trust_remote_user_headers:
        remote_user = request.headers.get("remote-user")
        if not remote_user:
            return None
        gateway_token = settings.auth.gateway_token
        if gateway_token:
            # Remote-User is only trustworthy when the request came through
            # Traefik, which proves it by injecting the gateway token.
            provided_gateway_token = request.headers.get("x-qcrbox-gateway-token")
            if not (provided_gateway_token and secrets.compare_digest(provided_gateway_token, gateway_token)):
                return None
        return remote_user

    return None
