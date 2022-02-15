import os
import socket
import threading
import time
from tkinter import *

serverSocketTCP = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
SERVER_ADDRESS_TCP = ('localhost', 50001)  # this makes a tuple of the ip address and port number, the empty string in the spot of the ip means let the OS decide (normally 0.0.0.0)
serverSocketTCP.bind(SERVER_ADDRESS_TCP)  # this sets the ip address and port number to the socket using the bind function
serverSocketTCP.listen(15)  # this sets the max amount of clients that can use the server at once to 1

serverSocketUDP = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
SERVER_ADDRESS_UDP = ('localhost', 40002)
serverSocketUDP.bind(SERVER_ADDRESS_UDP)

msg_lock = threading.Lock()
user_lock = threading.Lock()

kill = False
list_of_users = {}
list_of_udp_sockets = {}
requested_files = {}
flags_for_sender = {}
list_of_server_files = os.listdir('../Server_Files')


def run_server_tcp():
    print("Server ready for use!")
    while True:
        conn, addr = serverSocketTCP.accept()
        msg_list = conn.recv(2048).decode()[1:-1].split("><")
        if msg_list[0] == "connect":
            if msg_list[1] not in list_of_users:
                print(msg_list[1] + " connected")
                with user_lock:
                    list_of_users[msg_list[1]] = conn
                flags_for_sender[msg_list[1]] = {"get_users": False, "get_list_file": False, "msg_lst": [], "disconnect": False, "msg_ERROR": False, "FileNotFound_ERROR": False, "server_down": False, "file_sent": False, "proceed": False}
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


def run_server_udp():
    while True:
        msg, addr = serverSocketUDP.recvfrom(1024)
        msg_lst = msg.decode()[1:-1].split("><")
        if msg_lst[0] == "connect":
            send_over_udp_thread = threading.Thread(target=file_sender_thread, args=(addr, msg_lst[1]))
            send_over_udp_thread.setDaemon(True)
            send_over_udp_thread.start()


def file_sender_thread(addr, username: str):
    path = f"../Server_Files/{requested_files.get(username)}"
    serverSocketUDP.sendto(str(os.path.getsize(path)).encode(), addr)
    while True:
        if requested_files.get(username) and flags_for_sender.get(username)["proceed"]:
            try:
                with open(f"../Server_Files/{requested_files.get(username)}", "rb") as f:
                    data = f.read(1024)
                    while data:
                        if serverSocketUDP.sendto(data, addr):
                            data = f.read(1024)
                            time.sleep(0.02)
                print("FILE FULLY SENT!")
            except IOError:
                print("Couldn't Open File!")
            requested_files[username] = ""
            break
    flags_for_sender.get(username)["file_sent"] = True


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
        if flags_for_sender.get(username).get("file_sent"):
            conn.send("<file_sent>".encode())
            flags_for_sender.get(username)["file_sent"] = False


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
                        requested_files[username] = msg_list[1]
                        # file_download_thread = threading.Thread(target=send_file_thread, args=(username, msg_list[1]))
                        # file_download_thread.setDaemon(True)
                        # file_download_thread.start()
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
                    flags_for_sender.get(username)["proceed"] = True
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
    run_server_tcp_thread = threading.Thread(target=run_server_tcp)
    run_server_tcp_thread.setDaemon(True)
    run_server_tcp_thread.start()
    run_server_udp_thread = threading.Thread(target=run_server_udp)
    run_server_udp_thread.setDaemon(True)
    run_server_udp_thread.start()


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

    serverSocketTCP.close()
    serverSocketUDP.close()
