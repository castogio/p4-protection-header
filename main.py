#!/usr/bin/env python3
import argparse
import os
import logging
from typing import Dict

from controller.p4switch import P4Switch, SwitchRoles

# type aliases
Path = str

def specify_switch_topology(p4_dataplane: Path, bmv2_json: Path) -> Dict[str,P4Switch]:
    """Create switch objects matching the mininet topology in topology.json"""
    topology: Dict[str,P4Switch] = dict()

    topology['ingress_switch'] = P4Switch(
        switch_id=0,
        name='s1',
        role=SwitchRoles.INGRESS,
        uri=f'localhost:50051',
        p4_dataplane_file_path=p4_dataplane,
        bmv2_json_file_path=bmv2_json
        )

    topology['transit_up_left'] = P4Switch(
        switch_id=1,
        name='s2',
        role=SwitchRoles.TRANSIT,
        uri=f'localhost:50052',
        p4_dataplane_file_path=p4_dataplane,
        bmv2_json_file_path=bmv2_json
        )
    topology['transit_up_right'] = P4Switch(
        switch_id=2,
        name='s3',
        role=SwitchRoles.TRANSIT,
        uri=f'localhost:50053',
        p4_dataplane_file_path=p4_dataplane,
        bmv2_json_file_path=bmv2_json
        )
    
    topology['egress_switch'] = P4Switch(
        switch_id=3,
        name='s4',
        role=SwitchRoles.EGRESS,
        uri=f'localhost:50054',
        p4_dataplane_file_path=p4_dataplane,
        bmv2_json_file_path=bmv2_json
        )
    
    topology['transit_bottom_right'] = P4Switch(
        switch_id=4,
        name='s5',
        role=SwitchRoles.TRANSIT,
        uri=f'localhost:50055',
        p4_dataplane_file_path=p4_dataplane,
        bmv2_json_file_path=bmv2_json
        )

    topology['transit_bottom_left'] = P4Switch(
        switch_id=5,
        name='s6',
        role=SwitchRoles.TRANSIT,
        uri=f'localhost:50056',
        p4_dataplane_file_path=p4_dataplane,
        bmv2_json_file_path=bmv2_json
        )

    return topology
    

def main(p4_dataplane_info: Path, bmv2_json: Path) -> None:

    # info_help = P4InfoHelper(p4_dataplane_info)
    
    switch_topology = specify_switch_topology(p4_dataplane_info, bmv2_json)
    logging.info(f'created switch topology')

    ingress_switch = switch_topology['ingress_switch']
    with ingress_switch.connect() as conn:
        conn.write_entry()


if __name__ == '__main__':



    parser = argparse.ArgumentParser(description='P4Runtime Controller')
    parser.add_argument('--p4info', help='p4info proto in text format from p4c',
                        type=str, action="store", required=False,
                        default='./build/switch_dataplane.p4.p4info.txt')
    parser.add_argument('--bmv2-json', help='BMv2 JSON file from p4c',
                        type=str, action="store", required=False,
                        default='./build/switch_dataplane.json')
    parser.add_argument('--debug', help='BMv2 JSON file from p4c',
                        type=bool, action="store", required=False,
                        default=False)
    args = parser.parse_args()

    if args.debug:
        logging.basicConfig(level=logging.DEBUG)

    if not os.path.exists(args.p4info):
        parser.print_help()
        logging.critical(f"p4info file not found: {args.p4info}; have you run 'make'?")
        parser.exit(1)
    if not os.path.exists(args.bmv2_json):
        parser.print_help()
        logging.critical("fBMv2 JSON file not found: {args.bmv2_json}; have you run 'make'?")
        parser.exit(1)
    
    main(args.p4info, args.bmv2_json)