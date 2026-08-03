"""Transport-agnostic tool context placeholder.

Legacy tool methods historically typed their first argument as LiveKit's
``RunContext``. That coupled every tool implementation to LiveKit even when the
method never used the context object (credentials live on ``self``).

``ToolContext`` is a neutral stand-in so the same tools can run under Pipecat
(``voice-ws``) or LiveKit (``worker``). Runtimes may pass any object (including
LiveKit's ``RunContext``); tools must not rely on LiveKit-specific attributes.
"""


class ToolContext:
    """Opaque context passed as the first argument to tool methods.

    Intentionally empty. Reserved for future shared call metadata (session id,
    caller phone, etc.) without tying tools to a media transport.
    """

    pass
