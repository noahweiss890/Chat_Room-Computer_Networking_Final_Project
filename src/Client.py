import socket
import threading

lock = threading.Lock()
server = None
connected = False


def connect_to_server():
    global server, connected
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    ip_address = "localhost"
    port = 50005
    server.connect((ip_address, port))
    username = input("Enter Username: ")
    server.send(f"<connect><{username}>".encode())
    connected = True


def send_message():
    global server
    to = input("Who would you like to send a message to? ")
    msg = input("Enter message: ")
    server.send(f"<set_msg><{to}><{msg}>".encode())
    print(f"You: {msg}")


def broadcast_message():
    global server
    msg = input("Enter message: ")
    server.send(f"<set_msg_all><{msg}>".encode())
    print(f"You: {msg}")


def sending_thread():
    global server, connected

    while True:
        print("\nChoose an option:\n"
              "1. Connect to server\n"
              "2. Disconnect from server\n"
              "3. Send message to a user\n"
              "4. Send message to all users\n"
              "5. See who is signed in\n"
              "6. See what files are on the server\n"
              "7. Request to download file\n"
              "8. Download file from server\n")

        opt = input("Option: ")

        if connected or opt == "1":
            if opt == "1":
                if not server:
                    connect_to_server()
                else:
                    print("Already connected to server!")
            elif opt == "2":
                server.send("<disconnect>".encode())
            elif opt == "3":
                send_message()
            elif opt == "4":
                broadcast_message()
            elif opt == "5":
                server.send("<get_users>".encode())
            elif opt == "6":
                server.send("<get_list_file>".encode())
            elif opt == "7":
                file = input("Enter name of file to download: ")
                server.send(f"<download><{file}>".encode())
            elif opt == "8":
                server.send("<proceed>".encode())
            else:
                print("INVALID INPUT! TRY AGAIN!")
        else:
            print("Not connected to server! Please connect to server")


def listening_thread():
    global server, connected
    while True:
        if connected:
            message = server.recv(2048).decode()[1:-1].split("><")

            if message[0] == "connected":
                print("Signed In")
            elif message[0] == "disconnected":
                server.close()
                server = None
                connected = False
                print("Signed Out")
            elif message[0] == "users_lst":
                print("-- online list --")
                for user in message[1:-1]:
                    print(user)
                print("-- end list --")
            elif message[0] == "file_lst":
                print("-- Server File List --")
                for file in message[1:-1]:
                    print(file)
                print("-- End Server File List --")
            elif message[0] == "msg_lst":
                for msg in message[1:-1]:
                    print(msg)
            elif message[0] == "username_ERROR":
                print("ERROR: Username already in use! Choose a different one")
                server.close()
                server = None
                connected = False
            elif message[0] == "msg_ERROR":
                print("ERROR: there is no user with that username! Try again")
            elif message[0] == "server_closed":
                server.close()
                server = None
                connected = False
                print("ERROR: Server down")


if __name__ == '__main__':
    server_sending_thread = threading.Thread(target=sending_thread)
    server_listening_thread = threading.Thread(target=listening_thread)
    server_sending_thread.start()
    server_listening_thread.start()
