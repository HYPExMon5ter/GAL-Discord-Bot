"""Lightweight metrics recording helpers used across services."""

from __future__ import annotations

import os
import threading
import time
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, Mapping, MutableMapping, Tuple

from utils.logging_utils import SecureLogger

logger = SecureLogger(__name__)


def _freeze_labels(labels: Mapping[str, str] | None) -> Tuple[Tuple[str, str], ...]:
    """Convert labels into a sorted tuple for use as a dict key."""
    if not labels:
        return ()
    return tuple(sorted((str(key), str(value)) for key, value in labels.items()))


@dataclass
class RunningStats:
    """Track aggregate statistics for timing metrics."""

    count: int = 0
    total: float = 0.0
    maximum: float = 0.0

    def add(self, value: float) -> None:
        self.count += 1
        self.total += value
        if value > self.maximum:
            self.maximum = value

    def to_dict(self) -> Dict[str, float]:
        average = self.total / self.count if self.count else 0.0
        return {
            "count": float(self.count),
            "total": self.total,
            "average": average,
            "max": self.maximum,
        }


class _MetricStore:
    """Thread-safe store for counters and timers."""

    def __init__(self) -> None:
        self._counters: MutableMapping[
            Tuple[str, Tuple[Tuple[str, str], ...]],
            int,
        ] = defaultdict(int)
        self._timings: MutableMapping[
            Tuple[str, Tuple[Tuple[str, str], ...]],
            RunningStats,
        ] = defaultdict(RunningStats)
        self._lock = threading.Lock()
        self._thresholds: Dict[str, float] = {
            "api.request.duration": float(os.getenv("METRIC_THRESHOLD_API_REQUEST_SECONDS", "0.5")),
            "command.duration": float(os.getenv("METRIC_THRESHOLD_COMMAND_SECONDS", "1.5")),
            "sheets.operation.duration": float(os.getenv("METRIC_THRESHOLD_SHEETS_SECONDS", "2.0")),
        }

    def set_threshold(self, metric: str, threshold_seconds: float) -> None:
        with self._lock:
            self._thresholds[metric] = threshold_seconds

    def increment_counter(
        self,
        metric: str,
        amount: int = 1,
        labels: Mapping[str, str] | None = None,
    ) -> None:
        key = (metric, _freeze_labels(labels))
        with self._lock:
            self._counters[key] += amount

    def record_duration(
        self,
        metric: str,
        seconds: float,
        labels: Mapping[str, str] | None = None,
    ) -> None:
        key = (metric, _freeze_labels(labels))
        with self._lock:
            stats = self._timings[key]
            stats.add(seconds)
            threshold = self._thresholds.get(metric)
        if threshold is not None and seconds > threshold:
            label_repr = ", ".join(f"{k}={v}" for k, v in (labels or {}).items())
            logger.warning(
                f"Metric '{metric}' exceeded threshold {threshold:.3f}s "
                f"(observed {seconds:.3f}s; labels: {label_repr or 'none'})"
            )

    def snapshot(self) -> Dict[str, Dict[str, Dict[str, float]]]:
        with self._lock:
            counters: Dict[str, Dict[str, float]] = defaultdict(dict)
            for (metric, labels), count in self._counters.items():
                label_key = "|".join(f"{k}={v}" for k, v in labels)
                counters[metric][label_key or ""] = float(count)

            timings: Dict[str, Dict[str, Dict[str, float]]] = defaultdict(dict)
            for (metric, labels), stats in self._timings.items():
                label_key = "|".join(f"{k}={v}" for k, v in labels)
                timings[metric][label_key or ""] = stats.to_dict()

        return {"counters": dict(counters), "timings": dict(timings)}

    def timer(self, metric: str, labels: Mapping[str, str] | None = None):
        return _TimingContext(self, metric, labels or {})


class _TimingContext:
    """Context manager used to record timing metrics."""

    def __init__(self, store: _MetricStore, metric: str, labels: Mapping[str, str]):
        self._store = store
        self._metric = metric
        self._labels = dict(labels)
        self._start = 0.0

    def __enter__(self):
        self._start = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc, _tb):
        elapsed = time.perf_counter() - self._start
        status = "error" if exc else "success"
        labels = dict(self._labels)
        labels.setdefault("status", status)
        self._store.record_duration(self._metric, elapsed, labels)
        return False


_STORE = _MetricStore()


def increment_counter(metric: str, amount: int = 1, **labels: str) -> None:
    """Increase a named counter."""
    _STORE.increment_counter(metric, amount, labels)


def record_duration(metric: str, seconds: float, **labels: str) -> None:
    """Record the duration of an operation."""
    _STORE.record_duration(metric, seconds, labels)


def time_block(metric: str, **labels: str):
    """Context manager to time an operation."""
    return _STORE.timer(metric, labels)


def set_threshold(metric: str, threshold_seconds: float) -> None:
    """Register or update a threshold for a timing metric."""
    _STORE.set_threshold(metric, threshold_seconds)


def export_metrics() -> Dict[str, Dict[str, Dict[str, float]]]:
    """Return a snapshot of recorded counters and timings."""
    return _STORE.snapshot()
