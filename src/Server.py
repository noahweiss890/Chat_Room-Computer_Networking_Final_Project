import os
import socket
import threading
from tkinter import *

serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
SERVER_ADDRESS = ('localhost', 50001)  # this makes a tuple of the ip address and port number, the empty string in the spot of the ip means let the OS decide (normally 0.0.0.0)
serverSocket.bind(SERVER_ADDRESS)  # this sets the ip address and port number to the socket using the bind function
serverSocket.listen(15)  # this sets the max amount of clients that can use the server at once to 1

msg_lock = threading.Lock()
user_lock = threading.Lock()

kill = False
list_of_users = {}
list_of_server_files = os.listdir('Server_Files')
flags_for_sender = {}


def run_server():
    # global kill
    print("Server ready for use!")
    while True:
        conn, addr = serverSocket.accept()
        msg_list = conn.recv(2048).decode()[1:-1].split("><")
        if msg_list[0] == "connect":
            if msg_list[1] not in list_of_users:
                print(msg_list[1] + " connected")
                with user_lock:
                    list_of_users[msg_list[1]] = conn
                flags_for_sender[msg_list[1]] = {"get_users": False, "get_list_file": False, "msg_lst": [], "disconnect": False, "msg_ERROR": False, "FileNotFound_ERROR": False, "server_down": False}
                client_listening_thread = threading.Thread(target=listening_thread, args=(conn, msg_list[1]))
                client_sending_thread = threading.Thread(target=sending_thread, args=(conn, msg_list[1]))
                client_listening_thread.setDaemon(True)
                client_sending_thread.setDaemon(True)
                client_listening_thread.start()
                client_sending_thread.start()
            else:
                conn.send("<username_ERROR>".encode())
        else:
            print("Invalid Connection Request!")


def sending_thread(conn: socket.socket, username: str):
    conn.send("<connected>".encode())
    while True:
        if flags_for_sender.get(username).get("get_users"):
            with user_lock:
                flags_for_sender.get(username)["get_users"] = False
                users = "<users_lst>"
                for user in list_of_users:
                    users += f"<{user}>"
                users += "<end>"
                conn.send(users.encode())
        if flags_for_sender.get(username).get("get_list_file"):
            flags_for_sender.get(username)["get_list_file"] = False
            files = "<file_lst>"
            for file in list_of_server_files:
                files += f"<{file}>"
            files += "<end>"
            conn.send(files.encode())
        if flags_for_sender.get(username).get("msg_lst"):
            with msg_lock:
                msgs = "<msg_lst>"
                for msg in flags_for_sender.get(username).get("msg_lst"):
                    msgs += f"<{msg}>"
                msgs += "<end>"
                conn.send(msgs.encode())
                flags_for_sender.get(username)["msg_lst"] = []
        if flags_for_sender.get(username).get("disconnect"):
            del list_of_users[username]
            del flags_for_sender[username]
            conn.send("<disconnected>".encode())
            conn.close()
            print(username + " disconnected")
            break
        if flags_for_sender.get(username).get("msg_ERROR"):
            conn.send("<msg_ERROR>".encode())
            flags_for_sender.get(username)["msg_ERROR"] = False
        if flags_for_sender.get(username).get("FileNotFound_ERROR"):
            conn.send("<FileNotFound_ERROR>".encode())
            flags_for_sender.get(username)["FileNotFound_ERROR"] = False
        if flags_for_sender.get(username).get("server_down"):
            conn.send("<server_down>".encode())
            flags_for_sender.get(username)["server_down"] = False


def listening_thread(conn: socket.socket, username: str):
    while True:
        try:
            message = conn.recv(2048)
            if message:
                msg_list = message.decode()[1:-1].split("><")
                if msg_list[0] == "disconnect":
                    flags_for_sender.get(username)["disconnect"] = True
                    break
                elif msg_list[0] == "get_users":
                    flags_for_sender.get(username)["get_users"] = True
                elif msg_list[0] == "set_msg":
                    if msg_list[1] in list_of_users:
                        with msg_lock:
                            flags_for_sender.get(msg_list[1]).get("msg_lst").append(f"(private) {username}: {msg_list[2]}")
                    else:
                        flags_for_sender.get(username)["msg_ERROR"] = True
                elif msg_list[0] == "set_msg_all":
                    with msg_lock:
                        for user in list_of_users:
                            if user != username:
                                flags_for_sender.get(user).get("msg_lst").append(f"(public) {username}: {msg_list[1]}")
                elif msg_list[0] == "get_list_file":
                    flags_for_sender.get(username)["get_list_file"] = True
                elif msg_list[0] == "download":
                    if msg_list[1] in list_of_server_files:
                        pass
                    else:
                        flags_for_sender.get(username)["FileNotFound_ERROR"] = True

                    # NOT DONE
                    # file = msg_list[1]
                    # if file in list_of_server_files:
                    #     try:
                    #         with open(file, "r") as f:
                    #             filedata_to_send = f.read()
                    #     except IOError:
                    #         print("Couldn't Open File!")
                    # NOT DONE
                elif msg_list[0] == "proceed":
                    pass
                    # NOT DONE
                    # for i in range(0, len(filedata_to_send)):
                    #     conn.send(filedata_to_send[i].encode())
                    # conn.send("<end>".encode())
                    # conn.send("OFFICIAL MESSAGE OF SOME SORT...".encode())
                    # NOT DONE
            # else:
            #     flags_for_sender.get(username)["disconnect"] = True
            #     break
        except:
            continue


def start_server():
    start_button["state"] = DISABLED
    start_label = Label(root, text="Server Started")
    start_label.pack()
    run_server_thread = threading.Thread(target=run_server)
    run_server_thread.setDaemon(True)
    run_server_thread.start()


def quit_me():
    global kill
    for username in list_of_users:
        flags_for_sender.get(username)["server_down"] = True
    kill = True
    print('Shutting down server')
    root.quit()
    root.destroy()


if __name__ == '__main__':
    root = Tk()
    root.title("Server")
    root.protocol("WM_DELETE_WINDOW", quit_me)
    start_button = Button(root, text="Start Server", padx=100, pady=50, command=start_server)
    start_button.pack()
    root.mainloop()

    while not kill:
        pass

    serverSocket.close()
