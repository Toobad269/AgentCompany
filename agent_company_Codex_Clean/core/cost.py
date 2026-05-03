"""
core/cost.py — Token- und Kosten-Tracking

Sammelt pro Agent + Modell:
  - input_tokens, output_tokens
  - optionale Cache-Token, falls vom SDK gemeldet

Berechnet ungefähre USD-Kosten anhand der hinterlegten Preise.
Achtung: Preise können sich ändern — bei Bedarf in MODEL_PRICES anpassen.
"""

from __future__ import annotations

import threading
from collections import defaultdict
from typing import Any


# Preise pro 1.000.000 Tokens (Stand April 2026, Richtwerte)
MODEL_PRICES: dict[str, dict[str, float]] = {
    # OpenAI GPT-5.5
    "gpt-5.5":     {"input": 5.0,  "output": 30.0},
    "gpt-5.5-pro": {"input": 30.0, "output": 180.0},
}

# Multiplier auf den Input-Preis für Cache-Operationen
CACHE_WRITE_MULTIPLIER = 1.25  # Schreiben in Cache: 25 % Aufschlag
CACHE_READ_MULTIPLIER  = 0.10  # Lesen aus Cache:    90 % Rabatt


def _price_for(model: str) -> dict[str, float]:
    """Gibt {input, output}-Preise pro 1M Tokens zurück. Fallback: GPT-5.5."""
    return MODEL_PRICES.get(model, MODEL_PRICES["gpt-5.5"])


def cost_of(usage: Any, model: str) -> float:
    """
    Berechnet die USD-Kosten eines einzelnen API-Calls aus dem Usage-Objekt.
    `usage` ist das SDK-Usage-Objekt mit Feldern wie input_tokens und
    output_tokens.
    """
    p = _price_for(model)
    inp_per_token  = p["input"]  / 1_000_000
    out_per_token  = p["output"] / 1_000_000

    input_tokens          = getattr(usage, "input_tokens", 0) or 0
    output_tokens         = getattr(usage, "output_tokens", 0) or 0
    cache_creation_tokens = getattr(usage, "cache_creation_input_tokens", 0) or 0
    cache_read_tokens     = getattr(usage, "cache_read_input_tokens", 0) or 0

    cost  = input_tokens          * inp_per_token
    cost += output_tokens         * out_per_token
    cost += cache_creation_tokens * inp_per_token * CACHE_WRITE_MULTIPLIER
    cost += cache_read_tokens     * inp_per_token * CACHE_READ_MULTIPLIER
    return cost


# =============================================================================
# Globaler Tracker
# =============================================================================

class CostTracker:
    """Thread-safer In-Memory-Tracker für alle Agenten."""

    def __init__(self):
        self._lock = threading.Lock()
        self.by_agent: dict[str, dict[str, Any]] = defaultdict(
            lambda: {
                "calls": 0,
                "input_tokens": 0,
                "output_tokens": 0,
                "cache_creation_tokens": 0,
                "cache_read_tokens": 0,
                "usd": 0.0,
                "model": "",
            }
        )

    def record(self, agent_id: str, model: str, usage: Any) -> float:
        """Zählt einen API-Call und gibt die Kosten dieses Calls zurück."""
        usd = cost_of(usage, model)
        with self._lock:
            entry = self.by_agent[agent_id]
            entry["calls"] += 1
            entry["model"] = model
            entry["input_tokens"]          += getattr(usage, "input_tokens", 0) or 0
            entry["output_tokens"]         += getattr(usage, "output_tokens", 0) or 0
            entry["cache_creation_tokens"] += getattr(usage, "cache_creation_input_tokens", 0) or 0
            entry["cache_read_tokens"]     += getattr(usage, "cache_read_input_tokens", 0) or 0
            entry["usd"]                   += usd
        return usd

    def total_usd(self) -> float:
        with self._lock:
            return sum(e["usd"] for e in self.by_agent.values())

    def total_calls(self) -> int:
        with self._lock:
            return sum(e["calls"] for e in self.by_agent.values())

    def snapshot(self) -> dict[str, Any]:
        """Zustand für Terminal-Status / Logs."""
        with self._lock:
            total_usd = sum(e["usd"] for e in self.by_agent.values())
            total_calls = sum(e["calls"] for e in self.by_agent.values())
            return {
                "total_usd":   round(total_usd, 6),
                "total_calls": total_calls,
                "by_agent":    {k: {**v, "usd": round(v["usd"], 6)}
                                for k, v in self.by_agent.items()},
            }


# Singleton, von allen Agents geteilt
TRACKER = CostTracker()
