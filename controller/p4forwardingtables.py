from typing import Dict, Any
from dataclasses import dataclass

@dataclass
class TableEntry:
    """Entry to be injected into the dataplane of a PH swith."""

    table_name: str
    match_fields: Dict[str, Any]
    action_name: str
    action_params: Dict[str, Any]


class SwitchTableEntryFactory:

    def get_ingress_MAC_entry(self, 
                              mac_addr: str, 
                              ingress_port: int) -> TableEntry:
        match_fields = {
            "hdr.ethernet.dstAddr": mac_addr,
            "standard_metadata.ingress_port": ingress_port
        }
        action_params = {}

        return TableEntry(
            table_name="MyIngress.interface_mac_address",
            match_fields=match_fields,
            action_name="MyIngress.no_action",
            action_params=action_params
            )

    def get_routing_entry(self, 
                          dst_network: str, 
                          prefix_len: int, 
                          egress_port: int) -> TableEntry:
        
        match_fields = {
            "hdr.ipv4.dstAddr": (dst_network, prefix_len)
        }
        action_params = {
            "port": egress_port
        }

        return TableEntry(
            table_name="MyIngress.working_routing_path_table",
            match_fields=match_fields,
            action_name="MyIngress.forward",
            action_params=action_params
            )
    
    def get_traffic_protect_entry(self,
                                source_ip: str,
                                destination_ip: str, 
                                connection_id: int, 
                                is_ph_ingress: bool, 
                                is_ph_egress: bool, 
                                clone_session_id: int = 0) -> TableEntry:
        
        match_fields = {
            "hdr.ipv4.srcAddr": source_ip,
            "hdr.ipv4.dstAddr": destination_ip
        }
        action_params = {
            "connection": connection_id,
            "isPHIngressFlag": 1 if is_ph_ingress else 0,
            "isPHEgressFlag": 1 if is_ph_egress else 0,
            "sessionID": clone_session_id
        }

        return TableEntry(
            table_name="MyIngress.protected_connections",
            match_fields=match_fields,
            action_name="MyIngress.associate_protected_details",
            action_params=action_params
            )

    def get_route_by_egress_entry(self,
                              dst_network: str, 
                              prefix_len: int,
                              egress_port: int,
                              src_mac: str,
                              next_hop_mac: str
                              ) -> TableEntry:
        
        match_fields = {
            "standard_metadata.egress_port": egress_port,
            "hdr.ipv4.dstAddr": (dst_network, prefix_len)
        }
        action_params = {
            "srcAddr": src_mac,
            "dstAddr": next_hop_mac
        }

        return TableEntry(
            table_name="MyEgress.next_hop_table",
            match_fields=match_fields,
            action_name="MyEgress.set_mac",
            action_params=action_params
            )