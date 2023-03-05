import logging
from dataclasses import dataclass
from typing import Dict, Any
from enum import Enum

from utils.p4runtime_lib.bmv2 import Bmv2SwitchConnection
from utils.p4runtime_lib.helper import P4InfoHelper

from controller.p4forwardingtables import TableEntry
from controller.p4clonesession import CloneSession

class P4SwitchConnection:
    """
    Context manager for the Bmv2SwitchConnection.
    Guarantee that the connection is closed at the end.
    """

    def __init__(self, switch: 'P4Switch') -> None:
        self.switch = switch

        logging.warn(f'connecting to {self.switch}')
        p4_logfile= f'logs/{self.switch.name}-p4runtime-requests.txt'
        logging.info(f'storing p4 logs for {self.switch.name} in {p4_logfile}')
        self.connection = Bmv2SwitchConnection(
            name=self.switch.name,
            address=self.switch.uri,
            device_id=self.switch.id,
            proto_dump_file=p4_logfile)
    
    def __enter__(self) -> 'P4SwitchConnection':
        self.connection.MasterArbitrationUpdate()
        self.connection.SetForwardingPipelineConfig(
            p4info=self.switch.p4_api.p4info,
            bmv2_json_file_path=self.switch.bmv2_json
        )
        return self
    
    def __exit__(self, exc_type, exc_value, exc_traceback):
        if self.connection is not None:
            self.connection.shutdown()
        logging.warn(f'closing connection to {self.switch}')
    
    def write_table_entry(self, entry_info: TableEntry) -> None:
        entry = self.switch.p4_api.buildTableEntry(
            table_name=entry_info.table_name,
            match_fields=entry_info.match_fields,
            action_name=entry_info.action_name,
            action_params=entry_info.action_params
        )
        self.connection.WriteTableEntry(entry)
        logging.warn(f'wrote table entry on {self.switch}')

    def set_clone_session(self, clone_session: CloneSession) -> None:
        replicas = [
            {
                "egress_port": clone_session.clone_port, 
                "instance": clone_session.clone_instance_id
            }
        ]
        clone_entry = self.switch.p4_api.buildCloneSessionEntry(
            clone_session.clone_session_id, 
            replicas, 
            0) # never truncate
        self.connection.WritePREEntry(clone_entry)
        logging.warn(f'created clone session {clone_session.clone_instance_id} on {self.switch}')


class SwitchRoles(str, Enum):
    INGRESS = 'ingress'
    TRANSIT = 'transit'
    EGRESS = 'egress'


class P4Switch:
    """Keep the data for a P4 switch"""

    def __init__(self, 
                 switch_id: int, 
                 name: str,
                 role: SwitchRoles,
                 uri: str, 
                 p4_dataplane_file_path: str,
                 bmv2_json_file_path: str) -> None:
        self.id = switch_id
        self.name = name
        self.role = role
        self.uri = uri
        self.p4_api = P4InfoHelper(p4_dataplane_file_path)
        self.bmv2_json = bmv2_json_file_path

    def connect(self) -> P4SwitchConnection:
        return P4SwitchConnection(self)

    def __str__(self) -> str:
        return f'Switch {self.name}, id {self.id}, role {self.role}'


