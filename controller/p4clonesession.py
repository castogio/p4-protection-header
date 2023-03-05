from dataclasses import dataclass

@dataclass
class CloneSession:
    clone_instance_id: int
    clone_port: int
    clone_session_id: int
