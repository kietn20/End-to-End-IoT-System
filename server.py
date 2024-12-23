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

        db_uri = os.getenv('MONGO_URI')
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

    def convert_moisture_to_rh(self, moisture_value, current_unit):
        """Convert moisture reading to Relative Humidity percentage"""
        if current_unit == 'absolute':
            # Convert absolute moisture to RH%
            rh = (moisture_value / 100) * 100
            return min(100, max(0, rh))
        return moisture_value

    def convert_liters_to_gallons(self, liters):
        """Convert liters to gallons"""
        return liters * 0.264172

    def get_fridge_moisture(self, device_id, device_name):
        """Get average moisture for the past 3 hours"""

        current_time = datetime.now(timezone.utc)
        three_hours_ago = current_time - timedelta(hours=3)
        three_hours_ago_timestamp = int(three_hours_ago.timestamp())
        print(f"Checking data from {three_hours_ago} to {current_time}")

        print(f"Querying fridge_virtual collection for device ID: {
            device_id}")
        moisture_data = self.db.fridge_virtual.find({
            'payload.parent_asset_uid': device_id,
            'payload.timestamp': {'$gte': str(three_hours_ago_timestamp)}
        })

        readings = []
        for data in moisture_data:
            if device_name == 'garage_fridge':
                sensor_key = 'garage_fridge Moisture Sensor'
            elif device_name == 'kitchen_fridge':
                sensor_key = 'kitchen_fridge Moisture Sensor'
            else:
                print(f"Skipping unknown device: {device_name}")
                continue

            print(f"Looking for sensor key: {sensor_key}")
            if sensor_key in data['payload']:
                sensor_value = float(data['payload'][sensor_key])
                moisture_value = self.convert_moisture_to_rh(
                    sensor_value,
                    self.device_metadata[device_name]['moisture_unit']
                )
                readings.append(moisture_value)
                print(f"Found reading: {moisture_value}% RH")
            else:
                print(f"Sensor key not found in payload")

        print(f"Found {len(readings)} valid readings")
        if readings:
            avg = sum(readings) / len(readings)
            print(f"Average moisture: {avg:.1f}% RH")
            return avg
        else:
            print("No readings found, returning 0")
            return 0

    def get_dishwasher_consumption(self):
        """Get average water consumption per cycle"""
        device_id = self.device_metadata['dishwasher']['id']
        print(f"\n=== Getting dishwasher consumption data ===")
        print(f"Querying fridge_virtual collection for device ID: {device_id}")

        # Query the data
        cycles = self.db.fridge_virtual.find({
            'payload.parent_asset_uid': device_id
        })

        total_consumption = 0
        cycle_count = 0

        sensor_key = 'dishwasher Water Sensor'
        print(f"Looking for sensor key: {sensor_key}")

        for cycle in cycles:
            if sensor_key in cycle['payload']:
                try:
                    liters = float(cycle['payload'][sensor_key])
                    gallons = self.convert_liters_to_gallons(liters)
                    total_consumption += gallons
                    cycle_count += 1
                    print(f"Found water consumption: {gallons:.2f} gallons")
                except ValueError:
                    print(f"Invalid water consumption reading in document")

        print(f"\nProcessed {cycle_count} cycles")

        if cycle_count > 0:
            avg_consumption = total_consumption / cycle_count
            print(f"Average water consumption: {
                  avg_consumption:.2f} gallons per cycle")
            return avg_consumption
        else:
            print("No cycles found, returning 0")
            return 0

    def get_power_consumption(self):
        """Compare power consumption between devices"""
        devices = ['kitchen_fridge', 'garage_fridge', 'dishwasher']
        consumption = {}

        for device in devices:
            device_id = self.device_metadata[device]['id']
            power_data = self.db.fridge_virtual.find({
                'payload.parent_asset_uid': device_id
            })

            total_watts = 0
            doc_count = 0
            print(f"\n=== Getting power data for {device} ===")

            sensor_key = f"{device} Power Sensor"
            print(f"Looking for sensor key: {sensor_key}")

            for data in power_data:
                if sensor_key in data['payload']:
                    try:
                        watts = float(data['payload'][sensor_key])
                        total_watts += watts
                        doc_count += 1
                        print(f"Found power reading: {watts} watts")
                    except ValueError:
                        print(f"Invalid power reading in document")

            kwh = total_watts / 1000 if doc_count > 0 else 0
            consumption[device] = kwh
            print(f"Total for {device}: {kwh:.2f} kWh")

        max_device = max(consumption.items(), key=lambda x: x[1])
        return max_device[0], consumption

    def convert_to_pst(self, utc_time):
        """Convert UTC time to PST"""
        utc = pytz.timezone('UTC')
        pst = pytz.timezone('America/Los_Angeles')
        # Make sure input time is UTC aware if not already
        if not utc_time.tzinfo:
            utc_time = utc.localize(utc_time)
        return utc_time.astimezone(pst)

    def process_query(self, query):
        """Process incoming queries and return appropriate responses"""
        try:
            if "moisture inside my kitchen fridge" in query:
                avg_moisture = self.get_fridge_moisture(
                    self.device_metadata['kitchen_fridge']['id'],
                    'kitchen_fridge'
                )
                current_time_pst = self.convert_to_pst(
                    datetime.now(timezone.utc))
                return f"Average moisture in kitchen fridge: {avg_moisture:.1f}% RH (PST: {current_time_pst.strftime('%I:%M %p')})"

            elif "water consumption per cycle in my smart dishwasher" in query:
                avg_consumption = self.get_dishwasher_consumption()
                current_time_pst = self.convert_to_pst(
                    datetime.now(timezone.utc))
                return f"Average water consumption per cycle: {avg_consumption:.2f} gallons (PST: {current_time_pst.strftime('%I:%M %p')})"

            elif "consumed more electricity among my three IoT devices" in query:
                max_device, consumption = self.get_power_consumption()
                current_time_pst = self.convert_to_pst(
                    datetime.now(timezone.utc))
                consumption_str = ", ".join(
                    f"{dev}: {cons:.2f} kWh" for dev, cons in consumption.items()
                )
                return f"Highest consumption: {max_device} ({consumption_str}) (PST: {current_time_pst.strftime('%I:%M %p')})"

            else:
                return "Invalid query. Please try one of the supported queries."

        except Exception as e:
            return f"Error processing query: {str(e)}"

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
