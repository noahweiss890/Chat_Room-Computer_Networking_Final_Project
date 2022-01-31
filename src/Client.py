import socket
import select
import sys

# server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#
# if len(sys.argv) != 3:
#     print("Correct usage: script, IP address, port number")
#     exit()
# IP_address = str(sys.argv[1])
# Port = int(sys.argv[2])
# server.connect((IP_address, Port))
#
# while True:
#
#     # maintains a list of possible input streams
#     sockets_list = [sys.stdin, server]
#
#     """ There are two possible input situations. Either the
#     user wants to give manual input to send to other people,
#     or the server is sending a message to be printed on the
#     screen. Select returns from sockets_list, the stream that
#     is reader for input. So for example, if the server wants
#     to send a message, then the if condition will hold true
#     below.If the user wants to send a message, the else
#     condition will evaluate as true"""
#     read_sockets,write_socket, error_socket = select.select(sockets_list,[],[])
#
#     for socks in read_sockets:
#         if socks == server:
#             message = socks.recv(2048)
#             print (message)
#         else:
#             message = sys.stdin.readline()
#             server.send(message)
#             sys.stdout.write("<You>")
#             sys.stdout.write(message)
#             sys.stdout.flush()
# server.close()


def connect_to_server(server: socket.socket):
    if not server:
        con_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        ip_address = "0.0.0.0"
        port = 50000
        server.connect((ip_address, port))
        username = input("Enter Username: ")
        to_send = f"<connect><{username}>"
        server.send(to_send.encode())
        print(server.recv(2048).decode())
        return con_server
    else:
        print("Already connected to server!")
        return server


def disconnect_from_server(server: socket.socket):
    server.send("<disconnect>".encode())
    rec = server.recv(2048).decode()
    if rec == "<disconnected>":
        print("Signed Out")
    server.close()


def send_message(server: socket.socket, to, msg):
    to_send = f"<set_msg><{to}><{msg}>"
    server.send(to_send.encode())


if __name__ == '__main__':

    server = None

    while True:
        print("Choose an option:\n"
              "1. Connect to server\n"
              "2. Disconnect from server\n"
              "3. Send message to a user\n"
              "4. Send message to all users\n"
              "5. See who is signed in\n"
              "6. See what files are on the server\n"
              "7. Request to download file\n"
              "8. Download file from server\n")

        opt = input("Option: ")

        if opt == 1:
            server = connect_to_server(server)
        elif opt == 2:
            disconnect_from_server(server)
            server = None
        elif opt == 3:
            to = input("Who would you like to send a message to? ")
            msg = input("Enter message: ")
            to_send = f"<set_msg><{to}><{msg}>"
            server.send(to_send.encode())
            print(f"You: {msg}")
        elif opt == 4:
            msg = input("Enter message: ")
            to_send = f"<set_msg_all><{msg}>"
            server.send(to_send.encode())
            print(f"You: {msg}")
        elif opt == 5:
            server.send("<get_users>".encode())
            print("-- online list --")
            amount_of_users = server.recv(2048).decode()
            for i in range(int(amount_of_users)):
                user = server.recv(2048).decode()
                print(f"{i+1}. {user}")
            print("-- end list --")
        elif opt == 6:
            server.send("<get_list_file>".encode())
            response = server.recv(2048).decode()
            if response == "<file_lst>":
                print("-- Server File List --")
                file = server.recv(2048).decode()
                while file != "<end>":
                    print(file[1:-1])
                    file = server.recv(2048).decode()
                print("-- End Server File List --")
        elif opt == 7:
            file = input("Enter name of file to download: ")
            server.send(f"<download><{file}>".encode())
        elif opt == 8:
            server.send("<proceed>".encode())
        else:
            messages = server.send("<get_messages>".encode())
            msg = server.recv(2048).decode()[1:-1].split("><")
            while msg[0] != "end":
                print(f"{msg[0]}: {msg[1]}")
                msg = server.recv(2048).decode()[1:-1].split("><")
