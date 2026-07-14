"""
FastAPI dependency factories for declarative permission / role checks.

These factories let route handlers express their access control in one
line instead of inlining the same `has_role("platform_admin") or
has_role("org_admin", str(org_id))` ladder on every endpoint.

Usage:

    from src.auth.dependencies import require_role, require_permission

    @router.post("/organizations/{org_id}/agents")
    async def create_agent(
        org_id: UUID,
        _auth: tuple[UUID, UserProfile] = Depends(
            require_role("org_admin", org_id_source="path")
        ),
    ):
        ...

    @router.post("/agents", response_model=VoiceAgent)
    async def create_agent_body(
        agent_data: VoiceAgentCreate,
        _auth: tuple[UUID, UserProfile] = Depends(
            require_permission("agent", "create",
                               org_id_source="body",
                               body_field="organization_id")
        ),
    ):
        ...

Design:

The factory returns an *async* dependency callable. FastAPI evaluates
the dependency per request; the factory itself is called once at import
time and only stores its configuration (resource, action, org source).

`org_id_source` is intentionally a small enum-string to keep the
factory's surface area minimal. The first iteration supports:

  - "path"  → read from request.path_params[org_id_param]
  - "body"  → parse JSON body, read body[body_field]
  - any other value → NotImplementedError (planned follow-up: "query").

Platform admins always pass. Non-platform-admins are checked against
`profile.has_role(...)` or `profile.has_permission(...)` scoped to the
resolved org_id. A failure raises HTTPException(403).

Why a factory and not a plain dependency function:
  - Routes express the SAME logic with different (resource, action,
    org_id_source) triples. A factory lets us declare those triples
    declaratively in the route signature.
  - Adding a new source (e.g. "query", "header") only touches this file,
    not every route.

Also exports :func:`check_billing_permissions` — the shared dependency
used by `billing/routes.py` and `phone_numbers/routes.py`. It is the
OR of three checks (platform_admin / org_admin on target org /
`billing:subscribe` on target org) and is implemented as a thin
wrapper over the helpers below so all three layers share the
platform-admin short-circuit in one place.
"""
from typing import Awaitable, Callable, Optional
from uuid import UUID

from fastapi import Depends, Header, HTTPException, Request, status
from opentelemetry import trace

from src.auth.middleware import get_authenticated_user
from src.auth.models import UserProfile

tracer = trace.get_tracer(__name__)

# Supported values for `org_id_source`. Anything else raises at
# factory-construction time, not at request time, so misconfiguration
# surfaces during app startup or test collection, not under load.
_ORG_ID_SOURCE_PATH = "path"
_ORG_ID_SOURCE_BODY = "body"
SUPPORTED_ORG_ID_SOURCES = frozenset({_ORG_ID_SOURCE_PATH, _ORG_ID_SOURCE_BODY})


# --- Shared dependency: billing access ----------------------------------
#
# The check is the OR of four conditions (see permission-matrix.md):
#
#   1. `platform_admin` (org-agnostic).
#   2. `org_admin` on the target org (the normal billing manager).
#   3. `billing:manage` on the target org (N1 nav / UI composite).
#   4. `billing:subscribe` on the target org (legacy API seed).
#
# Phone-number routes MUST NOT use this helper — they use
# ``phone_number:*`` via :func:`assert_has_permission` so a
# billing-only grant cannot mutate phone inventory.
def assert_billing_access(
    user_profile: UserProfile,
    organization_id: UUID,
    *,
    error_message: Optional[str] = None,
) -> None:
    """Assert the caller may perform billing ops on ``organization_id``.

    Raises HTTPException(403) when none of the four conditions pass.
    Prefer this helper over try/except chains around
    :func:`assert_has_role` / :func:`assert_has_permission` so a
    denied check never gets re-wrapped as HTTP 500.
    """
    detail = (
        error_message
        or "Insufficient permissions for billing operations in this organization"
    )
    org_key = str(organization_id)
    if user_profile.has_role("platform_admin"):
        return
    if user_profile.has_role("org_admin", org_key):
        return
    if user_profile.has_permission("billing:manage", org_key):
        return
    if user_profile.has_permission("billing:subscribe", org_key):
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


async def check_billing_permissions(
    organization_id: UUID, authorization: str = Header(None)
) -> tuple[UUID, UserProfile]:
    """Shared FastAPI dependency for billing-scoped routes.

    Args:
        organization_id: Org to scope the check to (path/query param
            named ``organization_id`` so FastAPI injects it).
        authorization: The ``Authorization`` header value.

    Returns:
        ``(user_id, user_profile)`` on success.

    Raises:
        HTTPException(401) if the token is missing/invalid.
        HTTPException(403) if :func:`assert_billing_access` fails.
    """
    user_id, user_profile = await get_authenticated_user(authorization)
    assert_billing_access(user_profile, organization_id)
    return user_id, user_profile


def _resolve_org_id(
    request: Request,
    org_id_source: str,
    org_id_param: str,
    body_field: Optional[str],
) -> UUID:
    """Resolve the org_id from the request based on the chosen source.

    Raises:
        HTTPException(400) if the source is configured but the org_id
            cannot be found (e.g. body missing the field, path missing
            the param). A missing org_id is a client error, not a 403.
    """
    if org_id_source == _ORG_ID_SOURCE_PATH:
        raw = request.path_params.get(org_id_param)
        if raw is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Path parameter '{org_id_param}' is required for this check",
            )
        try:
            return UUID(raw)
        except (ValueError, TypeError) as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Path parameter '{org_id_param}' is not a valid UUID",
            ) from exc

    if org_id_source == _ORG_ID_SOURCE_BODY:
        if not body_field:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="org_id_source='body' requires body_field to be set",
            )
        # We cannot `await` here; the caller (the dependency wrapper)
        # does that and passes the parsed body via a closure. See
        # require_permission / require_role below.
        raise NotImplementedError(
            "Body source resolves org_id inside the dependency wrapper; "
            "_resolve_org_id should not be called directly with source='body'"
        )

    raise NotImplementedError(
        f"org_id_source='{org_id_source}' is not implemented. "
        f"Supported sources: {sorted(SUPPORTED_ORG_ID_SOURCES)}"
    )


def _check_access(
    *,
    user_profile: UserProfile,
    check_kind: str,
    check_arg: str,
    org_id: UUID,
    error_message: str,
    current_span=None,
) -> None:
    """Apply the role/permission check against a user profile.

    Pure function — no FastAPI involvement, no I/O. Platform admins
    always pass. Otherwise the org-scoped role or permission is
    checked against `org_id`.

    Raises:
        HTTPException(403) if the check fails.
    """
    # Platform admin always passes.
    if user_profile.has_role("platform_admin"):
        return

    # Apply the org-scoped check.
    if check_kind == "role":
        allowed = user_profile.has_role(check_arg, str(org_id))
    elif check_kind == "permission":
        allowed = user_profile.has_permission(check_arg, str(org_id))
    else:
        # Defensive: should be unreachable because _make_check is
        # only called from the two factories below.
        raise NotImplementedError(f"Unknown check_kind: {check_kind}")

    if not allowed:
        if current_span is not None:
            current_span.set_status(
                trace.Status(trace.StatusCode.ERROR, error_message)
            )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=error_message
        )


def _make_check(
    *,
    check_kind: str,
    check_arg: str,
    org_id_source: str,
    org_id_param: str,
    body_field: Optional[str],
    error_message: str,
) -> Callable[..., Awaitable[tuple[UUID, UserProfile]]]:
    """Build an async dependency callable for FastAPI.

    Args:
        check_kind: "role" or "permission".
        check_arg: the role name (e.g. "org_admin") or resource+action
            joined as "<resource>:<action>" (e.g. "agent:create").
        org_id_source: see SUPPORTED_ORG_ID_SOURCES.
        org_id_param: name of the path parameter (default "org_id").
        body_field: for org_id_source="body", the JSON field to read.
        error_message: detail string for the 403 response.

    Returns:
        An async function suitable for `Depends(...)` whose signature
        is `async (request, _auth_dep) -> (user_id, user_profile)`.
    """
    if org_id_source not in SUPPORTED_ORG_ID_SOURCES:
        raise NotImplementedError(
            f"org_id_source='{org_id_source}' is not implemented. "
            f"Supported sources: {sorted(SUPPORTED_ORG_ID_SOURCES)}"
        )

    async def dependency(
        request: Request,
        # `_auth_dep` is declared as a Depends so that route-level
        # `app.dependency_overrides[get_authenticated_user]` works in
        # tests. FastAPI sees this Depends and resolves it; the
        # factory itself never calls `get_authenticated_user` directly.
        _auth_dep: tuple[UUID, UserProfile] = Depends(get_authenticated_user),
    ) -> tuple[UUID, UserProfile]:
        """Run the permission/role check and return the auth tuple.

        In production, `_auth_dep` is resolved by FastAPI from the
        Authorization header. In tests, it is overridden via
        `app.dependency_overrides[get_authenticated_user]`.
        """
        current_span = trace.get_current_span()
        user_id, user_profile = _auth_dep

        # Resolve the org_id.
        if org_id_source == _ORG_ID_SOURCE_PATH:
            org_id = _resolve_org_id(
                request, org_id_source, org_id_param, body_field
            )
        else:  # body
            try:
                # `await request.json()` is safe inside an async dep
                # because FastAPI has not yet consumed the body for
                # any other dependency when this one runs. If the
                # route also has a Pydantic body parameter, FastAPI
                # will re-read the body via its own receive channel.
                # Starlette caches the body internally for this.
                body = await request.json()
            except Exception as exc:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Request body is not valid JSON",
                ) from exc
            if not body_field or body_field not in body:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Request body is missing field '{body_field}'",
                )
            try:
                org_id = UUID(body[body_field])
            except (ValueError, TypeError) as exc:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Body field '{body_field}' is not a valid UUID",
                ) from exc

        current_span.set_attribute("auth.org_id", str(org_id))
        current_span.set_attribute("auth.check_kind", check_kind)
        current_span.set_attribute("auth.check_arg", check_arg)

        _check_access(
            user_profile=user_profile,
            check_kind=check_kind,
            check_arg=check_arg,
            org_id=org_id,
            error_message=error_message,
            current_span=current_span,
        )

        return user_id, user_profile

    return dependency


def assert_has_permission(
    user_profile: UserProfile,
    resource: str,
    action: str,
    org_id: UUID,
    *,
    error_message: Optional[str] = None,
) -> None:
    """Assert the caller holds ``<resource>:<action>`` on ``org_id``.

    Use this when the org id is only known *after* loading a resource
    (e.g. agent update/delete by ``agent_id``). Prefer
    :func:`require_permission` when the org id is available from path
    or body at dependency-injection time.

    Platform admins always pass. Raises HTTPException(403) on failure.
    """
    permission_name = f"{resource}:{action}"
    _check_access(
        user_profile=user_profile,
        check_kind="permission",
        check_arg=permission_name,
        org_id=org_id,
        error_message=error_message
        or f"Insufficient permission '{permission_name}' for this organization",
    )


def assert_has_role(
    user_profile: UserProfile,
    role: str,
    org_id: UUID,
    *,
    error_message: Optional[str] = None,
) -> None:
    """Assert the caller holds ``role`` on ``org_id``.

    Same post-load pattern as :func:`assert_has_permission`. Platform
    admins always pass. Raises HTTPException(403) on failure.
    """
    _check_access(
        user_profile=user_profile,
        check_kind="role",
        check_arg=role,
        org_id=org_id,
        error_message=error_message
        or f"Insufficient role '{role}' for this organization",
    )


def assert_platform_role(
    user_profile: UserProfile,
    role: str,
    *,
    error_message: Optional[str] = None,
) -> None:
    """Assert the caller holds an org-agnostic role (e.g. ``platform_admin``).

    The post-load counterpart of
    :func:`require_role` for routes that do NOT have an org_id in
    scope. Most platform-admin-only checks (e.g. subscription-plan
    CRUD, org deletion, RBAC catalog reads) call this helper instead
    of constructing a sentinel UUID just to satisfy
    :func:`assert_has_role`'s signature.

    Raises:
        HTTPException(403) if the user does not hold ``role``.
    """
    if not user_profile.has_role(role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=error_message or f"Insufficient role '{role}' for this action",
        )


def require_role(
    role: str,
    *,
    org_id_source: str = "path",
    org_id_param: str = "org_id",
    error_message: Optional[str] = None,
) -> Callable[[Request], Awaitable[tuple[UUID, UserProfile]]]:
    """Build a dependency that requires the caller to hold `role` for the resolved org.

    Args:
        role: the role name (e.g. "org_admin").
        org_id_source: where to find the org_id. One of "path" or "body".
        org_id_param: name of the path parameter (default "org_id").
        error_message: optional 403 detail. Defaults to a sensible message.

    Returns:
        A FastAPI dependency that returns (user_id, user_profile) on
        success and raises 403 on failure.
    """
    return _make_check(
        check_kind="role",
        check_arg=role,
        org_id_source=org_id_source,
        org_id_param=org_id_param,
        body_field=None,
        error_message=error_message
        or f"Insufficient role '{role}' for this organization",
    )


def require_permission(
    resource: str,
    action: str,
    *,
    org_id_source: str = "path",
    org_id_param: str = "org_id",
    body_field: Optional[str] = None,
    error_message: Optional[str] = None,
) -> Callable[[Request], Awaitable[tuple[UUID, UserProfile]]]:
    """Build a dependency that requires the caller to hold `<resource>:<action>`.

    Args:
        resource: the resource name (e.g. "agent").
        action: the action name (e.g. "create"). The check looks up
            permission "<resource>:<action>".
        org_id_source: where to find the org_id. One of "path" or "body".
        org_id_param: name of the path parameter (default "org_id").
        body_field: required when org_id_source="body". The JSON field
            on the request body that holds the org_id UUID.
        error_message: optional 403 detail.

    Returns:
        A FastAPI dependency that returns (user_id, user_profile) on
        success and raises 403 on failure.
    """
    if org_id_source == "body" and not body_field:
        raise ValueError("body_field is required when org_id_source='body'")

    permission_name = f"{resource}:{action}"
    return _make_check(
        check_kind="permission",
        check_arg=permission_name,
        org_id_source=org_id_source,
        org_id_param=org_id_param,
        body_field=body_field,
        error_message=error_message
        or f"Insufficient permission '{permission_name}' for this organization",
    )
