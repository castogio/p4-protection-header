import socket
import time

SRV_IP = "10.0.2.100"
SRV_PORT = 5005
BUFF_SIZE = 1024

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((SRV_IP, SRV_PORT))

print(f'listening on port {SRV_PORT}')

while True:
    data, addr = sock.recvfrom(BUFF_SIZE)
    print(f'received seq {data} from {addr} -- {time.time()}')
    
