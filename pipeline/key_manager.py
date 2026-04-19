"""
key_manager.py — Automatic API Key Rotation for EpiCred

Supports up to 3 keys per service. When a key hits a rate-limit or quota
error, it is marked exhausted and the next key is tried automatically.

Usage:
    from pipeline.key_manager import gemini_keys, newsdata_keys

    key = gemini_keys.current()          # get active key
    gemini_keys.rotate()                 # force-rotate to next key
    gemini_keys.on_error(exc)            # rotate if exc is a quota/rate error
"""
import logging
import time
from threading import RLock

logger = logging.getLogger(__name__)

# ── Rate-limit signal strings ─────────────────────────────────────────────────
_QUOTA_SIGNALS = (
    "quota",
    "rate limit",
    "ratelimit",
    "resource_exhausted",
    "resourceexhausted",
    "429",
    "too many requests",
    "limit exceeded",
    "dailylimitexceeded",
    "usagelimitexceeded",
)


def _is_quota_error(exc: Exception) -> bool:
    """Return True if the exception looks like a quota / rate-limit error."""
    msg = str(exc).lower()
    return any(signal in msg for signal in _QUOTA_SIGNALS)


class KeyManager:
    """
    Thread-safe round-robin key rotator with time-based exhaustion reset.

    Keys marked exhausted are automatically un-exhausted after `cooldown_seconds`
    (default 65s — just over Gemini's 1-minute rate-limit window). This prevents
    the manager from getting permanently locked out across requests.

    Args:
        keys:             List of API key strings.
        service_name:     Human-readable label for log messages.
        cooldown_seconds: How long (s) before an exhausted key is retried.
    """

    def __init__(self, keys: list[str], service_name: str, cooldown_seconds: int = 65):
        self._service = service_name
        self._cooldown = cooldown_seconds
        self._keys = [k for k in keys if k and not k.startswith("your_")]
        self._index = 0
        # maps key-index → unix timestamp when it was exhausted
        self._exhausted_at: dict[int, float] = {}
        self._lock = RLock()

        if not self._keys:
            logger.warning(f"[KeyManager:{service_name}] No valid keys configured.")
        else:
            logger.info(f"[KeyManager:{service_name}] Loaded {len(self._keys)} key(s).")

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _is_exhausted(self, idx: int) -> bool:
        """Return True only if the key is still within its cooldown window."""
        exhausted_at = self._exhausted_at.get(idx)
        if exhausted_at is None:
            return False
        if time.time() - exhausted_at >= self._cooldown:
            del self._exhausted_at[idx]
            logger.info(
                f"[KeyManager:{self._service}] Key #{idx + 1} cooldown expired — re-activating."
            )
            return False
        return True

    def _any_available(self) -> bool:
        return any(not self._is_exhausted(i) for i in range(len(self._keys)))

    # ── Public API ────────────────────────────────────────────────────────────

    @property
    def available(self) -> bool:
        """True if at least one non-exhausted key exists."""
        with self._lock:
            return bool(self._keys) and self._any_available()

    def current(self) -> str | None:
        """Return the next available key (round-robin auto-advance), skipping ones in cooldown."""
        with self._lock:
            if not self._keys:
                return None
            
            # Start searching from the next key after the current index
            start_search = (self._index + 1) % len(self._keys)
            
            for i in range(len(self._keys)):
                idx = (start_search + i) % len(self._keys)
                if not self._is_exhausted(idx):
                    self._index = idx
                    return self._keys[idx]
                    
            logger.error(
                f"[KeyManager:{self._service}] All {len(self._keys)} key(s) "
                f"in cooldown. Will retry after {self._cooldown}s."
            )
            return None

    def rotate(self) -> str | None:
        """
        Mark current key exhausted and rotate to the next available one.
        Returns the new active key, or None if all are in cooldown.
        """
        with self._lock:
            if not self._keys:
                return None

            original = self._index
            self._exhausted_at[self._index] = time.time()
            logger.warning(f"[KeyManager:{self._service}] Key #{original + 1} exhausted (cooldown started).")

            for i in range(1, len(self._keys) + 1):
                next_idx = (original + i) % len(self._keys)
                if not self._is_exhausted(next_idx):
                    self._index = next_idx
                    logger.warning(
                        f"[KeyManager:{self._service}] Switched to key #{next_idx + 1}."
                    )
                    return self._keys[next_idx]

            logger.error(
                f"[KeyManager:{self._service}] All {len(self._keys)} key(s) exhausted."
            )
            return None

    def on_error(self, exc: Exception) -> bool:
        """
        Call this in an except block.
        If exc is a quota/rate-limit error, rotates the key and returns True
        (caller should retry). Otherwise returns False (caller should give up).
        """
        if _is_quota_error(exc):
            logger.warning(
                f"[KeyManager:{self._service}] Quota/rate-limit detected: {exc}"
            )
            new_key = self.rotate()
            if new_key:
                time.sleep(1)
                return True
        return False

    def reset(self) -> None:
        """Manually clear all exhaustion state."""
        with self._lock:
            self._exhausted_at.clear()
            self._index = 0
            logger.info(f"[KeyManager:{self._service}] Key exhaustion state reset.")

    def status(self) -> dict:
        """Return a status dict for health-check / dashboard display."""
        with self._lock:
            return {
                "service":    self._service,
                "total_keys": len(self._keys),
                "active_key": self._index + 1 if self._keys else 0,
                "exhausted":  [i + 1 for i in range(len(self._keys)) if self._is_exhausted(i)],
                "available":  self.available,
            }


# ── Singleton instances (imported by other modules) ───────────────────────────
# Populated by config.py after .env is loaded.
gemini_keys:   KeyManager | None = None
newsdata_keys: KeyManager | None = None


def init_key_managers(
    gemini_key_list:   list[str],
    newsdata_key_list: list[str],
) -> None:
    """Called once from config.py to initialise the singletons."""
    global gemini_keys, newsdata_keys
    gemini_keys   = KeyManager(gemini_key_list,   "Gemini")
    newsdata_keys = KeyManager(newsdata_key_list, "NewsData.io")
