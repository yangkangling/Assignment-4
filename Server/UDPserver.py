import socket
import threading
import random
import base64
import os

class UDPServer:
    def __init__(self, port):
    #Initialize UDP server with welcome port
        self.welcome_port = port
        self.welcome_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.welcome_socket.bind(('0.0.0.0', self.welcome_port))
        print(f"Server started on port {self.welcome_port}")

    def start(self):
        while True:
            try:
                data, client_addr = self.welcome_socket.recvfrom(1024)
                client_request = data.decode().strip()
                print(f"Received from {client_addr}: {client_request}")

                if client_request.startswith("DOWNLOAD"):
                    parts = client_request.split()
                    if len(parts) != 2:
                        continue
                    
                    filename = parts[1]
                    if not os.path.exists(filename):
                        self.welcome_socket.sendto(f"ERR {filename} NOT_FOUND".encode(), client_addr)
                        continue
                    
                    file_size = os.path.getsize(filename)
                    data_port = random.randint(50000, 51000)
                    
                    # Spin up a new thread for file transfer to avoid blocking main server
                    threading.Thread(
                        target=self.handle_file_transfer,
                        args=(filename, client_addr, data_port, file_size)
                    ).start()
                    
                    self.welcome_socket.sendto(
                        f"OK {filename} SIZE {file_size} PORT {data_port}".encode(),
                        client_addr
                    )
            except Exception as e:
                print(f"Server error: {e}")

    def handle_file_transfer(self, filename, client_addr, data_port, file_size):
        try:
            data_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            data_socket.bind(('0.0.0.0', data_port))
            print(f"Data channel started on port {data_port} for {filename}")

            with open(filename, 'rb') as file:
                while True:
                    data, addr = data_socket.recvfrom(2048)
                    request = data.decode().strip()
                    parts = request.split()
                    
                    if not parts:
                        continue
                        
                    if parts[0] == "FILE" and parts[2] == "GET":
                        try:
                            start = int(parts[4])
                            end = int(parts[6])
                            file.seek(start)
                            chunk = file.read(end - start + 1)
                            encoded = base64.b64encode(chunk).decode()
                            response = f"FILE {filename} OK START {start} END {end} DATA {encoded}"
                            data_socket.sendto(response.encode(), client_addr)
                        except Exception as e:
                            print(f"File transfer error: {e}")
                            
                    elif parts[0] == "FILE" and parts[2] == "CLOSE":
                        data_socket.sendto(f"FILE {filename} CLOSE_OK".encode(), client_addr)
                        break
                        
        except Exception as e:
            print(f"File transfer thread error: {e}")
        finally:
            data_socket.close()
            print(f"Closed data channel for {filename}")

if __name__ == "__main__":
    # Validate command line arguments before starting server
    import sys
    if len(sys.argv) != 2:
        print("Usage: python UDPserver.py <port>")
        sys.exit(1)
    
    server = UDPServer(int(sys.argv[1]))
    server.start()
