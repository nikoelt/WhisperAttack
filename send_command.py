import socket
import sys
import ctypes

HOST = '127.0.0.1'
PORT = 65432

# Ensure the script is running with admin privileges
def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

if not is_admin():
    ctypes.windll.shell32.ShellExecuteW(
        None, "runas", sys.executable, " ".join(sys.argv), None, 1
    )
    sys.exit()

cmd = sys.argv[1] if len(sys.argv) > 1 else "start"

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.connect((HOST, PORT))
    s.sendall(cmd.encode('utf-8'))
