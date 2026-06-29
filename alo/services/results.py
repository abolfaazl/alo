from dataclasses import dataclass
from typing import Any, Optional

@dataclass
class ServiceResult:
    success: bool
    error: Optional[str] = None
    error_code: Optional[str] = None
    payload: Optional[Any] = None
