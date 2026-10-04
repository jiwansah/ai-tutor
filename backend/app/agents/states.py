from enum import Enum

class TutorState(str, Enum):
    IDLE = "idle"
    DIAGNOSING = "diagnosing"
    PLANNING = "planning"
    TEACHING = "teaching"
    CHECKING = "checking"
    ADAPTING = "adapting"
    UPDATING = "updating"