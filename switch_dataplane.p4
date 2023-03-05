/* -*- P4_16 -*- */
#include <core.p4>
#include <v1model.p4>

/* ************************************************************************
*  *********************** H E A D E R S **********************************
*  ************************************************************************
*/

/* P4 PACKET TYPE FLAGS */
#define PKT_INSTANCE_TYPE_NORMAL 0
#define PKT_INSTANCE_TYPE_INGRESS_CLONE 1
#define PKT_INSTANCE_TYPE_RESUBMIT 6

// Ethernet EtherType header numbers
const bit<16> ETHERTYPE_IPV4 = 0x0800;

// IP Protocol header numbers
const bit<8> PROTOCOL_PROTECTION_HEADER = 0xFA;
// const bit<8> TYPE_TCP                = 0x06;
// const bit<8> TYPE_UDP                = 0x17;


// Protection Header metadata const
#define MAX_CLONE_ID           65536
#define PH_MAX_NUM_CONNECTIONS 256


// type definitions
typedef bit<9>   egressSpec_t;
typedef bit<48>  macAddr_t;
typedef bit<32>  ip4Addr_t;
typedef bit<32>  cloneId_t;
typedef bit<32>  connectionID_t;
typedef bit<32>   sessionID_t;

header ethernet_t {
    macAddr_t dstAddr;
    macAddr_t srcAddr;
    bit<16>   etherType;
}

header ipv4_t {
    bit<4>    version;
    bit<4>    ihl;
    bit<8>    diffserv;
    bit<16>   totalLen;
    bit<16>   identification;
    bit<3>    flags;
    bit<13>   fragOffset;
    bit<8>    ttl;
    bit<8>    protocol;
    bit<16>   hdrChecksum;
    ip4Addr_t srcAddr;
    ip4Addr_t dstAddr;
}

header protection_t {
    cloneId_t cloneId;
    bit<8>    upperProtocol;
    bit<8>    flags;
}

struct headers {
    ethernet_t   ethernet;
    ipv4_t       ipv4;
    protection_t ph;
}

struct metadata {
    @field_list(1)
    bool isProtected;

    @field_list(1)
    cloneId_t current_cloneId;

    connectionID_t connectionId;
    bool isIngress;
    bool isEgress;
    sessionID_t cloneSessionId;
}

/* ************************************************************************
*  *********************** P A R S E R ************************************
*  ************************************************************************
*/

parser MyParser(packet_in packet,
                out headers hdr,
                inout metadata meta,
                inout standard_metadata_t standard_metadata) {

    state start {
        transition parse_ethernet;
    }

    state parse_ethernet {
        packet.extract(hdr.ethernet);
        transition select(hdr.ethernet.etherType) {
            ETHERTYPE_IPV4: parse_ipv4;
            default:   accept;
        }
    }

    state parse_ipv4 {
        packet.extract(hdr.ipv4);
        transition select(hdr.ipv4.protocol) {
            PROTOCOL_PROTECTION_HEADER: parse_protection_header;
            default:                    accept;
        }
    }

    state parse_protection_header {
        packet.extract(hdr.ph);
        transition accept;
    }

}

/* ************************************************************************
*  ***********   C H E C K S U M    V E R I F I C A T I O N  **************
*  ************************************************************************
*/

control MyVerifyChecksum(inout headers hdr, inout metadata meta) {
    apply {
        verify_checksum(
        hdr.ipv4.isValid(), { hdr.ipv4.version,
        		 hdr.ipv4.ihl,
        		 hdr.ipv4.diffserv,
        		 hdr.ipv4.totalLen,
        		 hdr.ipv4.identification,
        		 hdr.ipv4.flags,
        		 hdr.ipv4.fragOffset,
        		 hdr.ipv4.ttl,
        		 hdr.ipv4.protocol,
        		 hdr.ipv4.srcAddr,
        		 hdr.ipv4.dstAddr },
        hdr.ipv4.hdrChecksum,
        HashAlgorithm.csum16);
    }
}


/*************************************************************************
**************  I N G R E S S   P R O C E S S I N G   *******************
*************************************************************************/

control MyIngress(inout headers hdr,
                  inout metadata meta,
                  inout standard_metadata_t standard_metadata) {

    register<cloneId_t>(PH_MAX_NUM_CONNECTIONS) ph_expected_next_clone_ids;


    action associate_protected_details(connectionID_t connection, bit<1> isPHIngressFlag, bit<1> isPHEgressFlag, sessionID_t sessionID) {
        meta.isProtected = true;
        meta.connectionId = connection;
        meta.isIngress = (bool) isPHIngressFlag;
        meta.isEgress  = (bool) isPHEgressFlag;
        meta.cloneSessionId = sessionID;
    }
    // hits in this table mean that the packet flow between (src, dst) needs to be procted
    // this table associates a (src, dst) to a session ID as specified by the controller
    table protected_connections {
        key = {
            hdr.ipv4.srcAddr: exact;
            hdr.ipv4.dstAddr: exact;
        }
        actions = {
            associate_protected_details;
            NoAction;
        }
        size = 1024;
        default_action = NoAction();
    }

    action forward(egressSpec_t port) {
        standard_metadata.egress_spec = port;
        hdr.ipv4.ttl = hdr.ipv4.ttl - 1; // decrement TTL
    }

    action drop() {
        mark_to_drop(standard_metadata);
    }

    action no_action() {}


    // regular IPV4 routing table
    table working_routing_path_table {
        key = {
            hdr.ipv4.dstAddr: lpm;
        }
        actions = {
            forward;
            drop;
            NoAction;
        }
        size = 1024;
        default_action = drop();
    }

    // hits if the MAC address matches the port 
    table interface_mac_address {
        key = {
            hdr.ethernet.dstAddr: exact;
            standard_metadata.ingress_port: exact;
        }
        actions = {
            no_action;
        }
        size = 1024;
    }

    apply {

        bool isResubmit = (standard_metadata.instance_type == PKT_INSTANCE_TYPE_RESUBMIT);
        bool isForInterface = interface_mac_address.apply().hit;

        if ((isForInterface || isResubmit) && hdr.ipv4.isValid()) {

            bool isProtectedTraffic = protected_connections.apply().hit;

            if (!hdr.ph.isValid()) { // payload is NOT already protected
                if (isProtectedTraffic) { // check if protection has to be applied
                    if (meta.isIngress) {

                        cloneId_t previous_cloneId;
                        ph_expected_next_clone_ids.read(previous_cloneId, meta.connectionId);
                        meta.current_cloneId = (previous_cloneId + 1) % MAX_CLONE_ID;
                        ph_expected_next_clone_ids.write(meta.connectionId, meta.current_cloneId);

                        clone_preserving_field_list(CloneType.I2E, meta.cloneSessionId, 1);
                    }
                }
                working_routing_path_table.apply();
            }
            else { // packet has PH already

                if (standard_metadata.instance_type == PKT_INSTANCE_TYPE_RESUBMIT) {
                    // if it is a resubmit, just remove the PH
                    bit<8> upperProt = hdr.ph.upperProtocol;
                    hdr.ph.setInvalid();
                    hdr.ipv4.setValid();
                    hdr.ipv4.protocol = upperProt;
                    isProtectedTraffic = false;
                }

                if (isProtectedTraffic) {
                    cloneId_t received_cloneId = hdr.ph.cloneId;
                    cloneId_t expected_cloneId;
                    ph_expected_next_clone_ids.read(expected_cloneId, meta.connectionId);

                    // cloneId_t next_difference    = (expected_cloneId - received_cloneId) % MAX_CLONE_ID;
                    // cloneId_t reverse_difference = (received_cloneId - expected_cloneId) % MAX_CLONE_ID;
                    bool initial = (received_cloneId >= expected_cloneId) && ((received_cloneId - expected_cloneId) <= (MAX_CLONE_ID / 2)); 
                    bool final   = (received_cloneId < expected_cloneId)  && ((expected_cloneId - received_cloneId) >= (MAX_CLONE_ID /2));

                    if (initial || final) { // else silently drop if CLONE-ID already seen
                        cloneId_t next_cloneId = (received_cloneId + 1) % MAX_CLONE_ID;
                        ph_expected_next_clone_ids.write(meta.connectionId, next_cloneId);
                        resubmit_preserving_field_list(0);
                    }
                }
                else {
                    working_routing_path_table.apply(); // perform regular routing
                }
            }            
        }

    }
}

/* ************************************************************************
*  ***************  E G R E S S   P R O C E S S I N G   *******************
*  ************************************************************************
*/

control MyEgress(inout headers hdr,
                 inout metadata meta,
                 inout standard_metadata_t standard_metadata) {

    

    action drop() {
        mark_to_drop(standard_metadata);
    }

    action set_mac(macAddr_t srcAddr, macAddr_t dstAddr) {
		hdr.ethernet.srcAddr = srcAddr;
		hdr.ethernet.dstAddr = dstAddr;
	}

    table next_hop_table {

        key = {
            standard_metadata.egress_port: exact;
            hdr.ipv4.dstAddr: lpm;
        }

        actions = {
            set_mac;
            drop;
            NoAction;
        }

        default_action = drop();
    }

    apply { 

        if (meta.isIngress || standard_metadata.instance_type == PKT_INSTANCE_TYPE_INGRESS_CLONE) {
            hdr.ph.setValid();
            hdr.ph.cloneId = meta.current_cloneId;
            hdr.ph.upperProtocol = hdr.ipv4.protocol;
            hdr.ipv4.protocol = PROTOCOL_PROTECTION_HEADER;
            hdr.ph.flags = 0x00; // set all the flags to 0
        }

        next_hop_table.apply();
    }
}

/* ************************************************************************
*  ************   C H E C K S U M    C O M P U T A T I O N   **************
*  ************************************************************************
*/

control MyComputeChecksum(inout headers  hdr, inout metadata meta) {

    apply {
        update_checksum(
        hdr.ipv4.isValid(),
            { hdr.ipv4.version,
                hdr.ipv4.ihl,
                hdr.ipv4.diffserv,
                hdr.ipv4.totalLen,
                hdr.ipv4.identification,
                hdr.ipv4.flags,
                hdr.ipv4.fragOffset,
                hdr.ipv4.ttl,
                hdr.ipv4.protocol,
                hdr.ipv4.srcAddr,
                hdr.ipv4.dstAddr },
            hdr.ipv4.hdrChecksum,
            HashAlgorithm.csum16);
    }
}

/* ************************************************************************
*  **********************  D E P A R S E R  *******************************
*  ************************************************************************
*/

control MyDeparser(packet_out packet, in headers hdr) {
    apply {
        packet.emit(hdr.ethernet);
        packet.emit(hdr.ipv4);
        packet.emit(hdr.ph);
    }
}

/* ************************************************************************
*  **********************  S W I T C H  ***********************************
*  ************************************************************************
*/

V1Switch(
MyParser(),
MyVerifyChecksum(),
MyIngress(),
MyEgress(),
MyComputeChecksum(),
MyDeparser()
) main;