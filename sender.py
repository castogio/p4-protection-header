"""Send 10 to H2 10.0.2.100"""

import socket
import time


DST_IP = "10.0.2.100"
DST_PORT = 5005

NUM_MESSAGES = 100

if __name__ == '__main__':
    print(f'STARTING -- send {NUM_MESSAGES} UDP to {DST_IP}:{DST_PORT}')
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # open UDP socket
    for sequence in range(NUM_MESSAGES):
        # send a datagram with incrementing sequence number
        print(f'sending seq {sequence} -- {time.time()}')
        bytes_seq = str(sequence).encode('utf-8')
        sock.sendto(bytes_seq, (DST_IP, DST_PORT))
        time.sleep(1) # wait 1 sec

    print(f'DONE!')