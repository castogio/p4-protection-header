#!/usr/bin/env python3
import argparse
import os

import grpc
from utils.p4runtime_lib.bmv2 import Bmv2SwitchConnection
from utils.p4runtime_lib.helper import P4InfoHelper
from utils.p4runtime_lib.switch import ShutdownAllSwitchConnections

SWITCH_TO_HOST_PORT = 1
SWITCH_TO_SWITCH_PORT = 2


def build_switch_connection(name: str, id: int) -> Bmv2SwitchConnection:
    print(f'localhost:5005{name[1]}')
    return Bmv2SwitchConnection(
            name=name,
            address=f'localhost:5005{name[1]}',
            device_id=id,
            proto_dump_file=f'logs/{name}-p4runtime-requests.txt')


def writeIngressMACEntry(p4info_helper: P4InfoHelper, switch: Bmv2SwitchConnection, mac_addr: str, ingress_port: int) -> None:
    table_entry = p4info_helper.buildTableEntry(
        table_name="MyIngress.interface_mac_address",  
        match_fields={
            "hdr.ethernet.dstAddr": mac_addr,
            "standard_metadata.ingress_port": ingress_port
        },
        action_name="MyIngress.no_action",
        action_params={})
    switch.WriteTableEntry(table_entry)
    print(f"Set MAC {mac_addr} for port {ingress_port} on {switch.name}")


def writeWorkingRoutingPathEntry(p4info_helper: P4InfoHelper, switch: Bmv2SwitchConnection, dst_network: str, prefix_len: int, egress_port: int) -> None:
    table_entry = p4info_helper.buildTableEntry(
        table_name="MyIngress.working_routing_path_table",  
        match_fields={
            "hdr.ipv4.dstAddr": (dst_network, prefix_len)
        },
        action_name="MyIngress.forward",
        action_params={
            "port": egress_port
        })
    switch.WriteTableEntry(table_entry)
    print(f"Traffic to {dst_network}\{prefix_len} routed via port {egress_port} on {switch.name}")

def writeProtectedTrafficEntry(p4info_helper: P4InfoHelper, 
                                switch: Bmv2SwitchConnection, 
                                source_ip: str,
                                destination_ip: str, 
                                connection_id: int, 
                                is_ph_ingress: bool, 
                                is_ph_egress: bool, 
                                clone_session_id: int = 0) -> None:
    table_entry = p4info_helper.buildTableEntry(
        table_name="MyIngress.protected_connections",  
        match_fields={
            "hdr.ipv4.srcAddr": source_ip,
            "hdr.ipv4.dstAddr": destination_ip
        },
        action_name="MyIngress.associate_protected_details",
        action_params={
            "connection": connection_id,
            "isPHIngressFlag": int(is_ph_ingress),
            "isPHEgressFlag": int(is_ph_egress),
            "sessionID": clone_session_id
        })
    switch.WriteTableEntry(table_entry)
    print(f"Protected pair ({source_ip},{destination_ip}) with ID {connection_id} created on {switch.name}")
    print(f"INGRESS {is_ph_ingress}, EGRESS {is_ph_egress}, CLONE SESSION {clone_session_id}")

def writeCloneSession(p4info_helper: P4InfoHelper, switch: Bmv2SwitchConnection, clone_session_id: int, clone_port: int) -> None:
    replicas = [{"egress_port": clone_port, "instance": 1}]
    clone_entry = p4info_helper.buildCloneSessionEntry(clone_session_id, replicas, 0) # never truncate
    switch.WritePREEntry(clone_entry)
    print(f"Clone session ID {clone_session_id} via Port {clone_port} created on {switch.name}")

def writeRoutingByEgressEntry(p4info_helper: P4InfoHelper, switch: Bmv2SwitchConnection, dst_network: str, prefix_len: int, egress_port: int, src_mac: str, next_hop_mac: str) -> None:
    table_entry = p4info_helper.buildTableEntry(
        table_name="MyEgress.next_hop_table", 
        match_fields={
            "standard_metadata.egress_port": egress_port,
            "hdr.ipv4.dstAddr": (dst_network, prefix_len)
        },
        action_name="MyEgress.set_mac",
        action_params={
            "srcAddr": src_mac,
            "dstAddr": next_hop_mac
        })
    switch.WriteTableEntry(table_entry)
    print(f"Traffic to {dst_network}\{prefix_len} exiting via PORT {egress_port} is routed to {next_hop_mac} on {switch.name}")

def writePortMACAddr(p4info_helper: P4InfoHelper, switch: Bmv2SwitchConnection, mac: str, port: int) -> None:
    table_entry = p4info_helper.buildTableEntry(
        table_name="MyEgress.port_mac_table", 
        match_fields={
            "standard_metadata.egress_port": port
        },
        action_name="MyEgress.set_smac",
        action_params={
            "mac": mac
        })
    switch.WriteTableEntry(table_entry)
    print(f"Installed MAC address {mac} on {switch.name} port {port}")

def main(p4info_file_path: str, bmv2_file_path: str):
    # Instantiate a P4Runtime helper from the p4info file
    info_help = P4InfoHelper(p4info_file_path)

    try:
        sw: List[Bmv2SwitchConnection] = list()
        sw.append(build_switch_connection("s1", 0))
        sw.append(build_switch_connection("s2", 1))
        sw.append(build_switch_connection("s3", 2))
        sw.append(build_switch_connection("s4", 3))
        sw.append(build_switch_connection("s5", 4))
        sw.append(build_switch_connection("s6", 5))

        for s in sw:
            s.MasterArbitrationUpdate()
            s.SetForwardingPipelineConfig(p4info=info_help.p4info, bmv2_json_file_path=bmv2_file_path)
            print(f"Installed P4 Program using SetForwardingPipelineConfig on {s.name}")


        ############# INGRESS SWITCH #################
        ingress_switch = sw[0]
        writeIngressMACEntry(info_help, ingress_switch, mac_addr="08:00:00:00:01:00", ingress_port=1)

        writeCloneSession(info_help, ingress_switch, clone_session_id=500, clone_port=2)
        writeProtectedTrafficEntry(info_help, ingress_switch, 
                                    source_ip="10.0.1.100", 
                                    destination_ip="10.0.2.100", 
                                    connection_id=1, 
                                    is_ph_ingress=True,  
                                    is_ph_egress=False,
                                    clone_session_id=500)
        writeWorkingRoutingPathEntry(info_help, ingress_switch, dst_network="10.0.2.0", prefix_len=24, egress_port=3)        
        writeRoutingByEgressEntry(info_help, ingress_switch, dst_network="10.0.2.0", prefix_len=24, egress_port=3, src_mac="00:00:00:00:01:03", next_hop_mac="00:00:00:00:06:03")
        writeRoutingByEgressEntry(info_help, ingress_switch, dst_network="10.0.2.0", prefix_len=24, egress_port=2, src_mac="00:00:00:00:01:02", next_hop_mac="00:00:00:00:02:02")

       
        ############ PRIMARY ROUTE ############
        # Configure SW 6
        switch_6 = sw[5]
        writeIngressMACEntry(info_help, switch_6, mac_addr="00:00:00:00:06:03", ingress_port=3)
        writeWorkingRoutingPathEntry(info_help, switch_6, dst_network="10.0.2.0", prefix_len=24, egress_port=2)
        writeRoutingByEgressEntry(info_help, switch_6, dst_network="10.0.2.0", prefix_len=24, egress_port=2, src_mac="00:00:00:00:06:02", next_hop_mac="00:00:00:00:05:02")

        # Configure SW 5
        switch_5 = sw[4]
        writeIngressMACEntry(info_help, switch_5, mac_addr="00:00:00:00:05:02", ingress_port=2)
        writeWorkingRoutingPathEntry(info_help, switch_5, dst_network="10.0.2.0", prefix_len=24, egress_port=3)
        writeRoutingByEgressEntry(info_help, switch_5, dst_network="10.0.2.0", prefix_len=24, egress_port=3, src_mac="00:00:00:00:05:03", next_hop_mac="00:00:00:00:04:03")

        ############ SECONDARY ROUTE ############
        # Configure SW 2
        switch_2 = sw[1]
        writeIngressMACEntry(info_help, switch_2, mac_addr="00:00:00:00:02:02", ingress_port=2)
        writeWorkingRoutingPathEntry(info_help, switch_2, dst_network="10.0.2.0", prefix_len=24, egress_port=3)
        writeRoutingByEgressEntry(info_help, switch_2, dst_network="10.0.2.0", prefix_len=24, egress_port=3, src_mac="00:00:00:00:02:03", next_hop_mac="00:00:00:00:03:03")

        # Configure SW 3
        switch_3 = sw[2]
        writeIngressMACEntry(info_help, switch_3, mac_addr="00:00:00:00:03:03", ingress_port=3)
        writeWorkingRoutingPathEntry(info_help, switch_3, dst_network="10.0.2.0", prefix_len=24, egress_port=2)
        writeRoutingByEgressEntry(info_help, switch_3, dst_network="10.0.2.0", prefix_len=24, egress_port=2, src_mac="00:00:00:00:03:02", next_hop_mac="00:00:00:00:04:02")

        ############# EGRESS SWITCH #################
        egress_switch = sw[3]
        writeIngressMACEntry(info_help, egress_switch, mac_addr="00:00:00:00:04:02", ingress_port=2)
        writeIngressMACEntry(info_help, egress_switch, mac_addr="00:00:00:00:04:03", ingress_port=3)
        writeWorkingRoutingPathEntry(info_help, egress_switch, dst_network="10.0.2.0", prefix_len=24, egress_port=1)
        writeRoutingByEgressEntry(info_help, egress_switch, dst_network="10.0.2.100", prefix_len=32, egress_port=1, src_mac="08:00:00:00:02:00", next_hop_mac="08:00:00:00:02:22")
        writeRoutingByEgressEntry(info_help, egress_switch, dst_network="10.0.2.101", prefix_len=32, egress_port=1, src_mac="08:00:00:00:02:00", next_hop_mac="08:00:00:00:02:23")
        writeProtectedTrafficEntry(info_help, egress_switch, 
                                    source_ip="10.0.1.100", 
                                    destination_ip="10.0.2.100", 
                                    connection_id=1, 
                                    is_ph_ingress=False,  
                                    is_ph_egress=True)
    except KeyboardInterrupt:
        print(" Shutting down.")
    except grpc.RpcError as e:
        print(e)

    ShutdownAllSwitchConnections()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='P4Runtime Controller')
    parser.add_argument('--p4info', help='p4info proto in text format from p4c',
                        type=str, action="store", required=False,
                        default='./build/switch_dataplane.p4.p4info.txt')
    parser.add_argument('--bmv2-json', help='BMv2 JSON file from p4c',
                        type=str, action="store", required=False,
                        default='./build/switch_dataplane.json')
    args = parser.parse_args()

    if not os.path.exists(args.p4info):
        parser.print_help()
        print("\np4info file not found: %s\nHave you run 'make'?" % args.p4info)
        parser.exit(1)
    if not os.path.exists(args.bmv2_json):
        parser.print_help()
        print("\nBMv2 JSON file not found: %s\nHave you run 'make'?" % args.bmv2_json)
        parser.exit(1)

    main(args.p4info, args.bmv2_json)