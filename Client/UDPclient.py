import socket
import base64
import sys
import os

class UDPClient:
    def __init__(self, server_host, server_port, file_list):
        self.server_host = server_host
        self.server_port = server_port
        self.file_list = file_list
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.settimeout(1.0)  # Initial timeout 1 second
        self.max_retries = 5

    def send_and_receive(self, message, address, timeout=None):
        retries = 0
        current_timeout = timeout or self.socket.gettimeout()
        
        while retries < self.max_retries:
            try:
                self.socket.settimeout(current_timeout)
                self.socket.sendto(message.encode(), address)
                response, _ = self.socket.recvfrom(4096)
                return response.decode().strip()
            except socket.timeout:
                retries += 1
                current_timeout *= 2  # Exponential backoff
                print(f"Timeout, retry {retries} with timeout {current_timeout:.1f}s")
            except Exception as e:
                print(f"Communication error: {e}")
                break
                
        return None

    def download_file(self, filename):
        print(f"\nRequesting file: {filename}")
        
        # Step 1: Send DOWNLOAD request
        response = self.send_and_receive(
            f"DOWNLOAD {filename}",
            (self.server_host, self.server_port)
        )
        
        if not response:
            print("Failed to get response from server")
            return False
            
        if response.startswith("ERR"):
            print(response)
            return False
            
        # Parse OK response
        parts = response.split()
        if len(parts) < 6 or parts[0] != "OK":
            print("Invalid server response")
            return False
            
        file_size = int(parts[3])
        data_port = int(parts[5])
        print(f"File size: {file_size} bytes, Data port: {data_port}")

        # Step 2: Connect to data port and download chunks
        try:
            with open(filename, 'wb') as file:
                bytes_received = 0
                chunk_size = 1000  # Request 1000 bytes at a time
                
                while bytes_received < file_size:
                    start = bytes_received
                    end = min(start + chunk_size - 1, file_size - 1)
                    
                    # Request chunk
                    chunk_response = self.send_and_receive(
                        f"FILE {filename} GET START {start} END {end}",
                        (self.server_host, data_port)
                    )
                    
                    if not chunk_response:
                        print("Failed to receive chunk")
                        return False
                        
                    if not chunk_response.startswith(f"FILE {filename} OK"):
                        print("Invalid chunk response")
                        return False
                        
                    # Extract and decode data
                    data_start = chunk_response.find("DATA") + 5
                    encoded_data = chunk_response[data_start:]
                    chunk_data = base64.b64decode(encoded_data)
                    
                    # Write to file
                    file.seek(start)
                    file.write(chunk_data)
                    bytes_received += len(chunk_data)
                    print("*", end='', flush=True)
                
                # Finalize transfer
                close_response = self.send_and_receive(
                    f"FILE {filename} CLOSE",
                    (self.server_host, data_port)
                )
                
                if close_response != f"FILE {filename} CLOSE_OK":
                    print("Close confirmation failed")
                    return False
                    
            print(f"\nSuccessfully downloaded {filename}")
            return True
            
        except Exception as e:
            print(f"\nDownload error: {e}")
            return False

    def run(self):
        try:
            with open(self.file_list, 'r') as f:
                files = [line.strip() for line in f if line.strip()]
                
            for filename in files:
                self.download_file(filename)
                
        except FileNotFoundError:
            print(f"File list {self.file_list} not found")
        except Exception as e:
            print(f"Client error: {e}")
        finally:
            self.socket.close()

if __name__ == "__main__":

    if len(sys.argv) != 4:
        print("Usage: python UDPclient.py <server_host> <server_port> <file_list>")
        sys.exit(1)
    
    client = UDPClient(sys.argv[1], int(sys.argv[2]), sys.argv[3])
    client.run()