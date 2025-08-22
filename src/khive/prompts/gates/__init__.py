"""Quality gate prompts for orchestrated validations"""

from .design import DESIGN_GATE_PROMPT
from .documentation import DOCUMENTATION_GATE_PROMPT
from .factory import get_gate_prompt, list_available_gates
from .performance import PERFORMANCE_GATE_PROMPT
from .security import SECURITY_GATE_PROMPT
from .testing import TESTING_GATE_PROMPT

__all__ = [
    "DESIGN_GATE_PROMPT",
    "DOCUMENTATION_GATE_PROMPT",
    "PERFORMANCE_GATE_PROMPT",
    "SECURITY_GATE_PROMPT",
    "TESTING_GATE_PROMPT",
    "get_gate_prompt",
    "list_available_gates",
]
