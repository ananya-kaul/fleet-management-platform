"""Push notification dispatch.

Device tokens are registered by the mobile clients and kept in memory here. A
production deployment would persist them and post to APNs/FCM; the send() call
site and payload shape stay identical, so swapping the transport is a one-file
change.
"""

from collections import defaultdict

from app.core.logging import get_logger

logger = get_logger(__name__)

# user_id -> {(platform, token), ...}
_device_tokens: dict[int, set[tuple[str, str]]] = defaultdict(set)


def register_device(user_id: int, platform: str, token: str) -> None:
    _device_tokens[user_id].add((platform.lower(), token))
    logger.info("Registered %s push token for user id=%s", platform, user_id)


def unregister_device(user_id: int, token: str) -> None:
    _device_tokens[user_id] = {
        entry for entry in _device_tokens[user_id] if entry[1] != token
    }


def tokens_for(user_id: int) -> set[tuple[str, str]]:
    return set(_device_tokens.get(user_id, set()))


def send(*, user_id: int, title: str, body: str, reference: str | None = None) -> int:
    """Fan a notification out to every device registered for the user.

    Returns the number of devices targeted so callers and tests can assert on it.
    """
    targets = tokens_for(user_id)
    for platform, token in targets:
        logger.info(
            "PUSH -> user=%s platform=%s token=%s… title=%r ref=%s",
            user_id,
            platform,
            token[:8],
            title,
            reference,
        )
    return len(targets)
