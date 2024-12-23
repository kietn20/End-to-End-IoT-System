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


if __name__ == "__main__":
    host = input("Enter the server IP address: ")
    port = int(input("Enter the server port number: "))

    server = IoTServer(host, port)
    server.start()
