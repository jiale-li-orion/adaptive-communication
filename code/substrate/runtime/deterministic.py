#!/usr/bin/env python3
"""
deterministic.py — order-free pseudo-random draws addressed by a key.

A draw must depend on WHAT is being drawn, never on how many draws happened before it. With a
running stream, a runtime that sends two more queries consumes two more samples and meets
different channel weather in every later hour, so a comparison between runtimes silently becomes
a comparison between channels.

One implementation, shared by the mechanism-isolation layer and the business-layer simulator. Two
implementations of "the same" sampling would drift, and the drift would be invisible: both would
look random and both would be reproducible.

Deps: standard library only.
"""
from __future__ import annotations

import hashlib

__all__ = ["stable_uniform"]


def stable_uniform(seed: int, *key) -> float:
    """A deterministic uniform in [0, 1) addressed by `key`.

    The key should name the thing being drawn in full: the entity, the time, the message kind,
    the attempt ordinal and the logical identity of the operation. Omitting the logical identity
    is the mistake this exists to prevent — two different operations at the same entity, hour,
    kind and attempt would then share one outcome and be bound to the same fate.
    """
    payload = ("%d|" % seed + "|".join(map(str, key))).encode()
    digest = hashlib.blake2b(payload, digest_size=8).digest()
    return int.from_bytes(digest, "big") / 2.0 ** 64
