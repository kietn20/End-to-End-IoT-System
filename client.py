import socket

VALID_QUERIES = [
    "What is the average moisture inside my kitchen fridge in the past three hours?",
    "What is the average water consumption per cycle in my smart dishwasher?",
    "Which device consumed more electricity among my three IoT devices (two refrigerators and a dishwasher)?"
]


def display_valid_queries():
    print("\nValid queries:")
    for i, query in enumerate(VALID_QUERIES, 1):
        print(f"{i}. {query}")


def main():
    while True:
        server_ip = input("Enter server IP address: ")
        server_port = input("Enter server port number: ")

        try:
            server_port = int(server_port)

            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
                client_socket.connect((server_ip, server_port))
                print(f"Connected to server at {server_ip}:{server_port}")

                while True:
                    print("\nChoose your query:")
                    display_valid_queries()
                    print("\nEnter 'q' to quit")

                    choice = input(
                        "\nEnter your choice (1-3 or full query text): ")

                    if choice.lower() == 'q':
                        break

                    if choice.isdigit() and 1 <= int(choice) <= 3:
                        query = VALID_QUERIES[int(choice) - 1]

                    if query not in VALID_QUERIES:
                        print(
                            "\nSorry, this query cannot be processed. Please try one of the following:")
                        display_valid_queries()
                        continue

                    # Send query to server
                    client_socket.sendall(query.encode())

                    # Receive and display response
                    data = client_socket.recv(1024)
                    print(f"\nServer response: {data.decode()}")

                print("Disconnected from server.")
                break

        except ValueError:
            print("Error: Please enter a valid integer for port number.")
        except socket.gaierror:
            print("Error: Invalid IP address. Please enter a valid IP address.")
        except ConnectionRefusedError:
            print(
                "Error: Connection refused. Make sure the server is running and the IP and port are correct.")
        except Exception as e:
            print(f"An error occurred: {e}")


if __name__ == "__main__":
    main()
