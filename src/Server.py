# import socket
import socket
from _thread import start_new_thread
# from socket import *
# import sys  # In order to terminate the program

# import socket
# import select

# # import sys
# from threading import *

# serverSocket = socket(AF_INET, SOCK_STREAM)
serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
# serverSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
# serverSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
SERVER_ADDRESS = ('', 50010)  # this makes a tuple of the ip address and port number, the empty string in the spot of the ip means let the OS decide (normally 0.0.0.0)
serverSocket.bind(SERVER_ADDRESS)  # this sets the ip address and port number to the socket using the bind function
serverSocket.listen(15)  # this sets the max amount of clients that can use the server at once to 1

list_of_users = []
list_of_server_files = []
messages_for_users = {}


def run_server():
    print("Server ready for use!")
    while True:
        conn, addr = serverSocket.accept()

        msg_list = conn.recv(2048).decode()[1:-1].split("><")

        if msg_list[0] == "connect":
            print(msg_list[1] + " connected")
            list_of_users.append(msg_list[1])
            messages_for_users[msg_list[1]] = []
            start_new_thread(client_thread, (conn, msg_list[1]))
        else:
            print("Invalid Connection Request!")

        print(list_of_users)

    conn.close()
    server.close()


def client_thread(conn, username):
    # sends a message to the client whose user object is conn
    conn.send("Welcome to this chatroom!".encode())
    filedata_to_send = ""

    while True:
        try:
            message = conn.recv(2048)
            if message:

                msg_list = message.decode()[1:-1].split("><")

                if msg_list[0] == "disconnect":
                    list_of_users.remove(username)
                    del messages_for_users[username]
                    conn.send("<disconnected>".encode())
                    conn.close()
                    print(username + " disconnected")
                    break
                elif msg_list[0] == "get_users":
                    conn.send(f"<users_lst><{len(list_of_users)}>".encode())
                    for user in list_of_users:
                        conn.send(f"<{user}>".encode())
                    conn.send("<end>".encode())
                elif msg_list[0] == "set_msg":
                    to = msg_list[1]
                    messages_for_users.get(to).append((username, msg_list[2]))
                elif msg_list[0] == "set_msg_all":
                    for user in list_of_users:
                        messages_for_users.get(user).append((username, msg_list[1]))
                elif msg_list[0] == "get_list_file":
                    conn.send("<file_lst>".encode())
                    for file in list_of_server_files:
                        conn.send(f"<{file}>".encode())
                    conn.send("<end>".encode())
                elif msg_list[0] == "download":
                    file = msg_list[1]
                    if file in list_of_server_files:
                        try:
                            with open(file, "r") as f:
                                filedata_to_send = f.read()
                        except IOError:
                            print("Couldn't Open File!")
                elif msg_list[0] == "proceed":
                    for i in range(0, len(filedata_to_send)):
                        conn.send(filedata_to_send[i].encode())
                    conn.send("<end>".encode())
                    conn.send("OFFICIAL MESSAGE OF SOME SORT...".encode())
                elif msg_list[0] == "get_messages":
                    conn.send(f"<msg_lst><{len(messages_for_users.get(username))}>".encode())
                    for msg in messages_for_users.get(username):
                        conn.send(f"<{msg[0]}><{msg[1]}>".encode())
                    conn.send("<end>".encode())
                    messages_for_users[username] = {}
            else:
                """message may have no content if the connection
                is broken, in this case we remove the connection"""
                remove(conn)

        except:
            continue


def broadcast(message, connection):
    """Using the below function, we broadcast the message to all
    clients who's object is not the same as the one sending
    the message """
    for clients in list_of_users:
        if clients != connection:
            try:
                clients.send(message)
            except:
                clients.close()

                # if the link is broken, we remove the client
                remove(clients)


def remove(username):
    """The following function simply removes the object
    from the list that was created at the beginning of
    the program"""
    if username in list_of_users:
        list_of_users.remove(username)
        del messages_for_users[username]


    # while True:
    #     #Establish the connection
    #     print('Ready to serve...')
    #     connectionSocket, addr = serverSocket.accept()  # this returns the socket to the client and its ip address and port number
    #     try:
    #         message = connectionSocket.recv(1024).decode()
    #         filename = message.split()[1]
    #         f = open(filename[1:])
    #         print("File Exists!")
    #         outputdata = f.read()  # reads the data in the requested file
    #         f.close()
    #
    #         #Send one HTTP header line into socket
    #         #Fill in start
    #         connectionSocket.send('HTTP/1.1 200 OK\r\n\r\n'.encode())  # sends the http header to the client
    #         #Fill in end
    #
    #         #Send the content of the requested file to the client
    #         for i in range(0, len(outputdata)):
    #             connectionSocket.send(outputdata[i].encode())
    #         connectionSocket.send("\r\n".encode())
    #         connectionSocket.close()
    #
    #     except IOError:
    #         print("File Does Not Exist!")
    #
    #         # Send response message for file not found
    #         connectionSocket.send('HTTP/1.1 404 Not Found\r\n\r\n'.encode())  # sends a http header saying that the file does not exist on the server
    #         connectionSocket.send("<html><head></head><body><h1>404 Not found</h1></body></html>\r\n".encode())  # sends a short html page that says "404 Not found"
    #
    #         #Close client socket
    #         connectionSocket.close()  # closes the clients socket
    #
    # serverSocket.close()
    # sys.exit()  # Terminate the program after sending the corresponding data


if __name__ == '__main__':
    run_server()
