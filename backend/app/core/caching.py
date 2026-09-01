"""
Deterministic, Thread-Safe In-Memory Caching Layer for RoleRadar Pipeline.
Caches stable intermediate artifacts using SHA-256 content hashing to eliminate redundant computation.
"""
from collections import OrderedDict
import hashlib
import json
import threading
from typing import Any, TypeVar

T = TypeVar("T")

PARSER_CACHE_VERSION = "v7_structured"
JD_TAXONOMY_VERSION = "v1"
TAILORING_CACHE_VERSION = "v8_compact_fast"


def compute_sha256(content: str | bytes | dict | list) -> str:
    """Computes a deterministic SHA-256 hex digest for any string, bytes, or serializable JSON structure."""
    if isinstance(content, bytes):
        raw = content
    elif isinstance(content, str):
        raw = content.encode("utf-8")
    else:
        raw = json.dumps(content, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


class LRUCache:
    """Thread-safe LRU cache with configurable capacity."""

    def __init__(self, capacity: int = 128):
        self._capacity = capacity
        self._cache: OrderedDict[str, Any] = OrderedDict()
        self._lock = threading.Lock()

    def get(self, key: str) -> Any | None:
        with self._lock:
            if key not in self._cache:
                return None
            self._cache.move_to_end(key)
            return self._cache[key]

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
            self._cache[key] = value
            if len(self._cache) > self._capacity:
                self._cache.popitem(last=False)

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()

    def size(self) -> int:
        with self._lock:
            return len(self._cache)


# Global singleton pipeline caches
profile_cache = LRUCache(capacity=64)
jd_requirements_cache = LRUCache(capacity=128)
evidence_mapping_cache = LRUCache(capacity=128)
tailoring_plan_cache = LRUCache(capacity=64)


def get_cached_candidate_profile(raw_text: str) -> Any | None:
    key = f"{compute_sha256(raw_text)}:{PARSER_CACHE_VERSION}"
    return profile_cache.get(key)


def set_cached_candidate_profile(raw_text: str, profile: Any) -> None:
    key = f"{compute_sha256(raw_text)}:{PARSER_CACHE_VERSION}"
    profile_cache.set(key, profile)


def get_cached_jd_requirements(jd_text: str, role_title: str = "") -> Any | None:
    key = f"{compute_sha256(jd_text + '|' + role_title)}:{JD_TAXONOMY_VERSION}"
    return jd_requirements_cache.get(key)


def set_cached_jd_requirements(jd_text: str, role_title: str, reqs: Any) -> None:
    key = f"{compute_sha256(jd_text + '|' + role_title)}:{JD_TAXONOMY_VERSION}"
    jd_requirements_cache.set(key, reqs)


def get_cached_tailoring_plan(profile_hash: str, jd_hash: str, model_name: str) -> Any | None:
    key = f"{profile_hash}:{jd_hash}:{model_name}:{TAILORING_CACHE_VERSION}"
    return tailoring_plan_cache.get(key)


def set_cached_tailoring_plan(profile_hash: str, jd_hash: str, model_name: str, plan: Any) -> None:
    key = f"{profile_hash}:{jd_hash}:{model_name}:{TAILORING_CACHE_VERSION}"
    tailoring_plan_cache.set(key, plan)
