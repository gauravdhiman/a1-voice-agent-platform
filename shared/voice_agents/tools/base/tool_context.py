"""Transport-agnostic tool context placeholder.

Shared tool methods accept a ``ToolContext`` as their first argument so
credentials and config stay on ``self`` while runtimes (``voice-ws``) can inject
call metadata later without changing tool signatures.
"""


class ToolContext:
    """Opaque context passed as the first argument to tool methods.

    Intentionally empty. Reserved for future shared call metadata (session id,
    caller phone, etc.) without tying tools to a media transport.
    """

    pass
