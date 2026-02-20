"""Standard protocol base class."""
from __future__ import annotations

from typing import Any


class StandardProtocol:
    name: str = ""
    description: str = ""

    def to_procedure(self) -> Any:
        raise NotImplementedError

    def to_yaml(self) -> str:
        raise NotImplementedError
