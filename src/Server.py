import math
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
SERVER_ADDRESS_UDP = ('localhost', 40000)
serverSocketUDP.bind(SERVER_ADDRESS_UDP)

msg_lock = threading.Lock()
user_lock = threading.Lock()

kill = False
list_of_users = {}
list_of_udp_sockets = {}
requested_files = {}
flags_for_sender = {}
list_of_server_files = os.listdir('../Server_Files')
available_udp_ports = []
sent_packets = {}
timeout_seq = {}
dupack_seq = {}
window_size = {}
CC_stage = {}
ssthresh = {}
# ssthresh_locks = {}
# window_size_locks = {}
# CC_stage_locks = {}
# sent_packets_locks = {}
udp_thread_kill = {}
PACKET_SIZE = 2048


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
                flags_for_sender[msg_list[1]] = {"get_users": False, "get_list_file": False, "msg_lst": [], "disconnect": False, "msg_ERROR": False, "FileNotFound_ERROR": False, "server_down": False, "proceed": False}
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
        if msg_lst[0] == "SYN":
            port = next_available_udp_port()
            if port != -1:
                new_serverSocketUDP = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                new_SERVER_ADDRESS_UDP = ('localhost', port)
                new_serverSocketUDP.bind(new_SERVER_ADDRESS_UDP)
                send_over_udp_thread = threading.Thread(target=file_sender_thread, args=(new_serverSocketUDP, addr, msg_lst[1]))
                send_over_udp_thread.setDaemon(True)
                send_over_udp_thread.start()
            else:
                print("No available port to open")


def file_sender_thread(sockUDP: socket.socket, addr, username: str):
    print("started file_sender_thread")
    sockUDP.sendto("<SYN ACK>".encode(), addr)
    msg = sockUDP.recv(PACKET_SIZE).decode()[1:-1]
    if msg == "ACK":
        sent_packets[username] = {}
        timeout_seq[username] = -1
        dupack_seq[username] = -1
        window_size[username] = 1
        CC_stage[username] = "Slow Start"
        ssthresh[username] = 32
        # ssthresh_locks[username] = threading.Lock()
        # window_size_locks[username] = threading.Lock()
        # CC_stage_locks[username] = threading.Lock()
        # sent_packets_locks[username] = threading.Lock()
        udp_thread_kill[username] = False
        buffer = []
        with open(f"../Server_Files/{requested_files.get(username)}", "rb") as f:
            data = f.read(PACKET_SIZE)
            while data:
                buffer.append(data)
                data = f.read(PACKET_SIZE)
        print("size of buffer:", len(buffer))
        sockUDP.sendto(len(buffer).to_bytes(2, byteorder='big'), addr)
        packet_sender_thread = threading.Thread(target=packet_sender, args=(sockUDP, addr, username, buffer))
        ack_receiver_thread = threading.Thread(target=ack_receiver, args=(sockUDP, username, len(buffer)))
        timeout_checker_thread = threading.Thread(target=timeout_checker, args=(username, ))
        packet_sender_thread.setDaemon(True)
        ack_receiver_thread.setDaemon(True)
        timeout_checker_thread.setDaemon(True)
        packet_sender_thread.start()
        ack_receiver_thread.start()
        timeout_checker_thread.start()


def timeout_checker(username: str):
    print("started timeout_checker")
    # global sent_packets, timeout_seq
    timeout = 1.0
    while not udp_thread_kill[username]:
        if timeout_seq[username] == -1:
            # with sent_packets_locks[username]:
            # copy_sent_packets = sent_packets.get(username).copy().items()
            # curr_time = time.time()
            for seq, t in sent_packets.get(username).copy().items():
                if time.time() > t + timeout:
                    print("timeout occurred:", seq)
                    timeout_seq[username] = seq
                    # with ssthresh_locks[username]:
                    ssthresh[username] = window_size[username]/2
                    # with window_size_locks[username]:
                    window_size[username] = 1
                    # with CC_stage_locks[username]:
                    CC_stage[username] = "Slow Start"
                    break


def ack_receiver(sockUDP: socket.socket, username: str, buffer_size: int):
    print("started ack_receiver")
    last_ack_seq = -1
    dupAckcount = 0
    # packets_amount = math.ceil(os.path.getsize(f"../Server_Files/{requested_files.get(username)}")/PACKET_SIZE)
    while not udp_thread_kill[username]:
        ack = sockUDP.recv(PACKET_SIZE).decode()[1:-1].split("><")
        if ack[0] == "ack":
            print("got ack for:", int(ack[1]))
            if int(ack[1]) >= buffer_size:
                udp_thread_kill[username] = True
            if int(ack[1]) == last_ack_seq:
                if CC_stage[username] == "Fast Recovery":
                    # with window_size_locks[username]:
                    window_size[username] += 1
                else:
                    dupAckcount += 1
                    if dupAckcount == 3:
                        dupack_seq[username] = int(ack[1])
                        # with ssthresh_locks[username]:
                        ssthresh[username] = window_size[username]/2
                        # with window_size_locks[username]:
                        window_size[username] = window_size[username]/2 + 3
                        # with CC_stage_locks[username]:
                        CC_stage[username] = "Fast Recovery"
            else:
                last_ack_seq = int(ack[1])
                dupAckcount = 0
                if CC_stage[username] == "Slow Start":
                    # with window_size_locks[username]:
                    window_size[username] += 1
                    if window_size[username] >= ssthresh[username]:
                        # with CC_stage_locks[username]:
                        CC_stage[username] = "Congestion Avoidance"
                elif CC_stage[username] == "Congestion Avoidance":
                    # with window_size_locks[username]:
                    window_size[username] += 1/window_size[username]
                elif CC_stage[username] == "Fast Recovery":
                    # with window_size_locks[username]:
                    window_size[username] = ssthresh[username]
                    # with CC_stage_locks[username]:
                    CC_stage[username] = "Congestion Avoidance"
                # with sent_packets_locks[username]:
                print("send packets keys:", sent_packets[username].keys())
                for i in sent_packets[username].copy().keys():
                    if i < int(ack[1]):
                        print(f"ack is {int(ack[1])}, gonna delete seq: {i}")
                        # with sent_packets_locks[username]:
                        del sent_packets.get(username)[i]
        else:
            print("RECEIVED ERROR ON UDP!")


def packet_sender(sockUDP: socket.socket, addr, username: str, buffer: list):
    print("started packet_sender")
    next_packet = 0
    while not udp_thread_kill[username]:
        if timeout_seq[username] != -1:
            # with sent_packets_locks[username]:
            print("sent timeout data seq:", timeout_seq[username])
            sockUDP.sendto(timeout_seq[username].to_bytes(2, byteorder='big')+buffer[timeout_seq[username]], addr)
            sent_packets.get(username)[timeout_seq[username]] = time.time()
            timeout_seq[username] = -1
            time.sleep(0.2)
        if dupack_seq[username] != -1:
            # with sent_packets_locks[username]:
            print("sent duplicate data seq:", dupack_seq[username])
            sockUDP.sendto(dupack_seq[username].to_bytes(2, byteorder='big')+buffer[dupack_seq[username]], addr)
            sent_packets.get(username)[dupack_seq[username]] = time.time()
            dupack_seq[username] = -1
            time.sleep(0.2)
        # with sent_packets_locks[username]:
        #     with window_size_locks[username]:
        while len(sent_packets[username]) < int(window_size[username]):
            if next_packet < len(buffer):
                print("sent data seq:", next_packet)
                sockUDP.sendto(next_packet.to_bytes(2, byteorder='big')+buffer[next_packet], addr)
                sent_packets.get(username)[next_packet] = time.time()
                next_packet += 1
        time.sleep(0.2)


def next_available_udp_port() -> int:
    for i in range(16):
        if i not in available_udp_ports:
            available_udp_ports.append(i)
            return 55000 + i
    return -1


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
                        requested_files[username] = msg_list[1]
                    else:
                        flags_for_sender.get(username)["FileNotFound_ERROR"] = True
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
    print('Shutting down server')
    root.quit()
    root.destroy()
    kill = True


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
