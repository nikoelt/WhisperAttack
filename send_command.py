import socket
import sys

HOST = '127.0.0.1'
PORT = 65432

cmd = sys.argv[1] if len(sys.argv) > 1 else "start"

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.connect((HOST, PORT))
    s.sendall(cmd.encode('utf-8'))
