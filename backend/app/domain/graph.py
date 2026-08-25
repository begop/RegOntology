from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True, slots=True)
class GraphProjectionStatus:
    status: Literal["healthy", "stale", "unavailable"]
    publication_id: str | None

    @property
    def healthy(self) -> bool:
        return self.status == "healthy"
