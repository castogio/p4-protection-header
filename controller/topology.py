
from controller.p4switch import P4Switch, SwitchRoles, P4SwitchConnection
from typing import Dict

def specify_switch_topology(p4_dataplane_path: str, bmv2_json_path: str) -> Dict[str,P4Switch]:
    """Create switch objects matching the mininet topology in topology.json"""
    topology: Dict[str,P4Switch] = dict()

    topology['ingress_switch'] = P4Switch(
        switch_id=0,
        name='s1',
        role=SwitchRoles.INGRESS,
        uri=f'localhost:50051',
        p4_dataplane_file_path=p4_dataplane_path,
        bmv2_json_file_path=bmv2_json_path
        )

    topology['transit_top_left'] = P4Switch(
        switch_id=1,
        name='s2',
        role=SwitchRoles.TRANSIT,
        uri=f'localhost:50052',
        p4_dataplane_file_path=p4_dataplane_path,
        bmv2_json_file_path=bmv2_json_path
        )
    topology['transit_top_right'] = P4Switch(
        switch_id=2,
        name='s3',
        role=SwitchRoles.TRANSIT,
        uri=f'localhost:50053',
        p4_dataplane_file_path=p4_dataplane_path,
        bmv2_json_file_path=bmv2_json_path
        )
    
    topology['egress_switch'] = P4Switch(
        switch_id=3,
        name='s4',
        role=SwitchRoles.EGRESS,
        uri=f'localhost:50054',
        p4_dataplane_file_path=p4_dataplane_path,
        bmv2_json_file_path=bmv2_json_path
        )
    
    topology['transit_bottom_right'] = P4Switch(
        switch_id=4,
        name='s5',
        role=SwitchRoles.TRANSIT,
        uri=f'localhost:50055',
        p4_dataplane_file_path=p4_dataplane_path,
        bmv2_json_file_path=bmv2_json_path
        )

    topology['transit_bottom_left'] = P4Switch(
        switch_id=5,
        name='s6',
        role=SwitchRoles.TRANSIT,
        uri=f'localhost:50056',
        p4_dataplane_file_path=p4_dataplane_path,
        bmv2_json_file_path=bmv2_json_path
        )

    return topology
    

from controller.p4forwardingtables import SwitchTableEntryFactory
from controller.p4clonesession import CloneSession

def configure_ingress_switch(switch_connection: P4SwitchConnection, entry_factory: SwitchTableEntryFactory) -> None:
    int_to_host_entry = entry_factory.get_ingress_MAC_entry(
        mac_addr="08:00:00:00:01:00", 
        ingress_port=1
    )
    switch_connection.write_table_entry(int_to_host_entry)

    protected_session = CloneSession(clone_instance_id=1, clone_port=1, clone_session_id=500)
    switch_connection.set_clone_session(protected_session)
    protection_header_entry = entry_factory.get_traffic_protect_entry(
        source_ip="10.0.1.100",
        destination_ip="10.0.2.100",
        connection_id=protected_session.clone_instance_id,
        is_ph_ingress=True,  
        is_ph_egress=False,
        clone_session_id=protected_session.clone_session_id
    )
    switch_connection.write_table_entry(protection_header_entry)

    working_route = entry_factory.get_routing_entry(dst_network="10.0.2.0", prefix_len=24, egress_port=3)
    port2_route_rewrite = entry_factory.get_route_by_egress_entry(
        dst_network="10.0.2.0", 
        prefix_len=24, 
        egress_port=3, 
        src_mac="00:00:00:00:01:03", 
        next_hop_mac="00:00:00:00:06:03"
    )
    port3_route_rewrite = entry_factory.get_route_by_egress_entry(
        dst_network="10.0.2.0", 
        prefix_len=24, 
        egress_port=2, 
        src_mac="00:00:00:00:06:02", 
        next_hop_mac="00:00:00:00:02:02"
    )
    switch_connection.write_table_entry(working_route)
    switch_connection.write_table_entry(port2_route_rewrite)
    switch_connection.write_table_entry(port3_route_rewrite)


def configure_egress_switch(switch_connection: P4SwitchConnection, entry_factory: SwitchTableEntryFactory) -> None:
    mac_to_primary = entry_factory.get_ingress_MAC_entry(
        mac_addr="00:00:00:00:04:02", 
        ingress_port=2
    )
    mac_to_backup = entry_factory.get_ingress_MAC_entry(
        mac_addr="00:00:00:00:04:03", 
        ingress_port=3
    )
    switch_connection.write_table_entry(mac_to_primary)
    switch_connection.write_table_entry(mac_to_backup)

    protected_session = CloneSession(clone_instance_id=1, clone_port=1, clone_session_id=500)
    switch_connection.set_clone_session(protected_session)
    protection_header_entry = entry_factory.get_traffic_protect_entry(
        source_ip="10.0.1.100",
        destination_ip="10.0.2.100",
        connection_id=protected_session.clone_instance_id,
        is_ph_ingress=False,  
        is_ph_egress=True,
        clone_session_id=protected_session.clone_session_id
    )
    switch_connection.write_table_entry(protection_header_entry)

    destination_route = entry_factory.get_routing_entry(dst_network="10.0.2.0", prefix_len=24, egress_port=1)
    forward_destination_entry = entry_factory.get_route_by_egress_entry(
        dst_network="10.0.2.0", 
        prefix_len=24, 
        egress_port=1, 
        src_mac="08:00:00:00:02:01", 
        next_hop_mac="08:00:00:00:02:22"
    )
    switch_connection.write_table_entry(destination_route)
    switch_connection.write_table_entry(forward_destination_entry)


def configure_transit_top_left_switch(switch_connection: P4SwitchConnection, entry_factory: SwitchTableEntryFactory) -> None:
    int_to_ingress_sw = entry_factory.get_ingress_MAC_entry(
        mac_addr="00:00:00:00:02:02", 
        ingress_port=2
    )
    route_to_destination = entry_factory.get_routing_entry(dst_network="10.0.2.0", prefix_len=24, egress_port=3)
    port2_route_rewrite = entry_factory.get_route_by_egress_entry(
        dst_network="10.0.2.0", 
        prefix_len=24, 
        egress_port=3, 
        src_mac="00:00:00:00:02:03", 
        next_hop_mac="00:00:00:00:03:03"
    )

    switch_connection.write_table_entry(int_to_ingress_sw)
    switch_connection.write_table_entry(route_to_destination)
    switch_connection.write_table_entry(port2_route_rewrite)


def configure_transit_top_right_switch(switch_connection: P4SwitchConnection, entry_factory: SwitchTableEntryFactory) -> None:
    int_to_previous_switch = entry_factory.get_ingress_MAC_entry(
        mac_addr="00:00:00:00:03:03", 
        ingress_port=3
    )
    route_to_destination = entry_factory.get_routing_entry(dst_network="10.0.2.0", prefix_len=24, egress_port=2)
    port2_route_rewrite = entry_factory.get_route_by_egress_entry(
        dst_network="10.0.2.0", 
        prefix_len=24, 
        egress_port=2, 
        src_mac="00:00:00:00:02:03", 
        next_hop_mac="00:00:00:00:03:03"
    )

    switch_connection.write_table_entry(int_to_previous_switch)
    switch_connection.write_table_entry(route_to_destination)
    switch_connection.write_table_entry(port2_route_rewrite)


def configure_transit_bottom_left_switch(switch_connection: P4SwitchConnection, entry_factory: SwitchTableEntryFactory) -> None:
    int_to_ingress_switch = entry_factory.get_ingress_MAC_entry(
        mac_addr="00:00:00:00:06:03", 
        ingress_port=3
    )
    route_to_destination = entry_factory.get_routing_entry(dst_network="10.0.2.0", prefix_len=24, egress_port=2)
    port2_route_rewrite = entry_factory.get_route_by_egress_entry(
        dst_network="10.0.2.0", 
        prefix_len=24, 
        egress_port=2, 
        src_mac="00:00:00:00:06:02", 
        next_hop_mac="00:00:00:00:05:02"
    )

    switch_connection.write_table_entry(int_to_ingress_switch)
    switch_connection.write_table_entry(route_to_destination)
    switch_connection.write_table_entry(port2_route_rewrite)


def configure_transit_bottom_right_switch(switch_connection: P4SwitchConnection, entry_factory: SwitchTableEntryFactory) -> None:
    int_to_previous_switch = entry_factory.get_ingress_MAC_entry(
        mac_addr="00:00:00:00:05:02", 
        ingress_port=2
    )
    route_to_destination = entry_factory.get_routing_entry(dst_network="10.0.2.0", prefix_len=24, egress_port=3)
    port2_route_rewrite = entry_factory.get_route_by_egress_entry(
        dst_network="10.0.2.0", 
        prefix_len=24, 
        egress_port=3, 
        src_mac="00:00:00:00:05:03", 
        next_hop_mac="00:00:00:00:04:03"
    )

    switch_connection.write_table_entry(int_to_previous_switch)
    switch_connection.write_table_entry(route_to_destination)
    switch_connection.write_table_entry(port2_route_rewrite)

