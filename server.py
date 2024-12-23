import socket
from dotenv import load_dotenv
import os
import pymongo
from datetime import datetime, timedelta, timezone
import pytz


class IoTServer:
    def __init__(self, host, port):
        self.host = host
        self.port = port

        load_dotenv()

        db_uri = os.getenv('MONGODB_URI')
        if not db_uri:
            raise ValueError("MongoDB URI not found in environment variables")

        self.client = pymongo.MongoClient(db_uri)
        self.db = self.client['test']

        # Load device metadata from the collection
        self.device_metadata = self.load_device_metadata()

    def load_device_metadata(self):
        """Load device metadata from MongoDB collection"""
        device_name_mapping = {
            'fridge1': 'kitchen_fridge',
            'fridge2': 'garage_fridge',
            'dishwasher': 'dishwasher'
        }

        metadata = {}

        # Query devices from 'fridge_metadata' collection
        devices = self.db.fridge_metadata.find({})

        for device in devices:
            collection_name = device['customAttributes']['name']
            device_name = device_name_mapping.get(collection_name)

            if not device_name:
                continue

            device_id = device['assetUid']
            device_type = device['customAttributes']['type']

            if device_type == 'DEVICE':
                # Determine if it's a fridge or dishwasher
                if device_name in ['kitchen_fridge', 'garage_fridge']:
                    device_type = 'refrigerator'
                    metadata[device_name] = {
                        'id': device_id,
                        'type': device_type,
                        'timezone': 'UTC',
                        'moisture_unit': 'absolute',
                        'power_unit': 'watts'
                    }
                elif device_name == 'dishwasher':
                    device_type = 'dishwasher'
                    metadata[device_name] = {
                        'id': device_id,
                        'type': device_type,
                        'timezone': 'UTC',
                        'water_unit': 'liters',
                        'power_unit': 'watts'
                    }

        return metadata



    def process_query(self, query):
        return "Response"

    def start(self):
        """Start the TCP server"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
            server_socket.bind((self.host, self.port))
            server_socket.listen()
            print(f"Server is listening on {self.host}:{self.port}")

            while True:
                client_socket, client_address = server_socket.accept()
                print(f"New connection from {client_address}")

                try:
                    with client_socket:
                        while True:
                            data = client_socket.recv(1024)
                            if not data:
                                break

                            query = data.decode()
                            print(f"Received query from {
                                  client_address}: {query}")

                            # Process the query and get response
                            response = self.process_query(query)

                            # Send response back to client
                            client_socket.send(response.encode())

                except Exception as e:
                    print(f"Error handling client {client_address}: {e}")
                finally:
                    print(f"Connection closed with client: {client_address}")


if __name__ == "__main__":
    host = input("Enter the server IP address: ")
    port = int(input("Enter the server port number: "))

    server = IoTServer(host, port)
    server.start()
