#!/usr/bin/env python3
import argparse
import os
import logging
from typing import Dict

import controller.topology as tp
from controller.p4forwardingtables import SwitchTableEntryFactory
from controller.p4switch import P4Switch


# type aliases
Path = str

def main(p4_dataplane_info: Path, bmv2_json: Path) -> None:
    
    switch_topology: Dict[str, P4Switch] = tp.specify_switch_topology(p4_dataplane_info, bmv2_json)
    logging.info(f'created switch topology')

    entry_factory = SwitchTableEntryFactory()

    ingress_switch = switch_topology['ingress_switch']
    with ingress_switch.connect() as conn:
        tp.configure_ingress_switch(conn, entry_factory)
    
    egress_switch = switch_topology['egress_switch']
    with egress_switch.connect() as conn:
        tp.configure_egress_switch(conn, entry_factory)

    egress_switch = switch_topology['transit_top_left']
    with egress_switch.connect() as conn:
        tp.configure_transit_top_left_switch(conn, entry_factory)

    egress_switch = switch_topology['transit_top_right']
    with egress_switch.connect() as conn:
        tp.configure_transit_top_right_switch(conn, entry_factory)

    egress_switch = switch_topology['transit_bottom_left']
    with egress_switch.connect() as conn:
        tp.configure_transit_bottom_left_switch(conn, entry_factory)

    egress_switch = switch_topology['transit_bottom_right']
    with egress_switch.connect() as conn:
        tp.configure_transit_bottom_right_switch(conn, entry_factory)


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