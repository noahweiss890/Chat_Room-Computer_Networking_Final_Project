import os
import socket
import threading
import time
from tkinter import *  # for gui

serverSocketTCP = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # this creates a tcp socket
SERVER_ADDRESS_TCP = ('0.0.0.0', 50000)
serverSocketTCP.bind(
    SERVER_ADDRESS_TCP)  # this sets the ip address and port number to the socket using the bind function
serverSocketTCP.listen(15)  # this sets the max amount of clients that can use the server at once to 15

serverSocketUDP = socket.socket(socket.AF_INET,
                                socket.SOCK_DGRAM)  # this creates a udp socket used to listen for initial handshake
SERVER_ADDRESS_UDP = ('0.0.0.0', 40000)
serverSocketUDP.bind(
    SERVER_ADDRESS_UDP)  # this sets the ip address and port number to the socket using the bind function

# these locks are to avoid thread racing
msg_lock = threading.Lock()
user_lock = threading.Lock()

kill = False
list_of_users = {}  # key is client's username, value is connection
# list_of_udp_sockets = {}
requested_files = {}  # key is client's username, value is the file the client requested for download
flags_for_sender = {}  # key is client's username, value is another dictionary where the keys are commands where the server must send something, and the values are true or false
list_of_server_files = os.listdir('../Server_Files')  # files that the server has access to
udp_ports_in_use = []  # list of udp ports that are in use
sent_packets = {}  # key is client's username and value is dictionary of sent packets waiting to be Acked where keys are the packet seq num and value is time it was sent out
dupack_seq = {}  # key is client's username, value is seq number of duplicate Acked packet
window_size = {}  # key is client's username, value is size of sending window to be dynamically changed with congestion control
CC_stage = {}  # key is client's username, value is congestion control stage to be changed through congestion control
ssthresh = {}  # key is client's username, value is threshold to be dynamically changed through congestion control
window_size_locks = {}  # key is the client's username, value is lock to avoid the window size being changed by multiple threads at the same time
sent_packets_locks = {}  # key is the client's username, value is lock for sent_packets to guarantee one thread has access to the dict at a time
udp_thread_kill = {}  # key is client's username, value is flag to kill thread when Ack for last packet is received
PACKET_SIZE = 2048


def run_server_tcp():
    """
    Thread that constantly listens for a TCP connection from client
    """
    print("Server ready for use!")
    while True:
        conn, addr = serverSocketTCP.accept()  # waiting to receive connection request
        msg_list = conn.recv(2048).decode()[1:-1].split("><")  # message is received and broken into parts
        if msg_list[0] == "connect":  # client wishes to connect to server
            if msg_list[1] not in list_of_users:
                print(msg_list[1] + " connected")
                with user_lock:  # to avoid thread racing
                    list_of_users[msg_list[1]] = conn
                flags_for_sender[msg_list[1]] = {"get_users": False, "get_list_file": False, "msg_lst": [],
                                                 "disconnect": False, "msg_ERROR": False, "FileNotFound_ERROR": False,
                                                 "server_down": False, "proceed": False}
                client_listening_thread = threading.Thread(target=listening_thread,
                                                           args=(conn, msg_list[1]))  # creates listening_thread
                client_sending_thread = threading.Thread(target=sending_thread,
                                                         args=(conn, msg_list[1]))  # creates sending_thread
                client_listening_thread.setDaemon(True)  # sets threads as Daemon
                client_sending_thread.setDaemon(True)
                client_listening_thread.start()  # starts listening_thread
                client_sending_thread.start()  # starts sending_thread
            else:
                conn.send("<username_ERROR>".encode())  # error
        else:
            print("Invalid Connection Request!")


def run_server_udp():
    """
    Thread that constantly listens for udp connection for downloading files
    """
    while True:
        msg, addr = serverSocketUDP.recvfrom(1024)  # receives message from client
        print("address of downloader:", addr)
        msg_lst = msg.decode()[1:-1].split("><")  # message is broken up into parts
        if msg_lst[0] == "SYN":  # initial handshake
            port = next_available_udp_port()
            if port != -1:  # there are available ports
                new_serverSocketUDP = socket.socket(socket.AF_INET,
                                                    socket.SOCK_DGRAM)  # separate udp socket created (and eventually closed) for each download request
                new_SERVER_ADDRESS_UDP = ("0.0.0.0", port)
                new_serverSocketUDP.bind(new_SERVER_ADDRESS_UDP)
                send_over_udp_thread = threading.Thread(target=file_sender_thread, args=(
                new_serverSocketUDP, addr, msg_lst[1]))  # creates thread for sending packets over the udp connection
                send_over_udp_thread.setDaemon(True)  # sets thread as daemon
                send_over_udp_thread.start()  # starts thread
            else:  # no available ports
                print("No available port to open")


def file_sender_thread(sockUDP: socket.socket, addr, username: str):
    """

    :param sockUDP:
    :param addr:
    :param username:
    Thread that is responsible for sending the file to the client over udp
    """
    sockUDP.sendto("<SYN ACK>".encode(), addr)  # tells client that connection was successful
    msg = sockUDP.recv(PACKET_SIZE).decode()[1:-1]
    if msg == "ACK":  # client ACKED the SYN ACK and packet sending can begin
        sent_packets[username] = {}
        dupack_seq[username] = -1
        window_size[username] = 1
        print("CC STAGE STARTING AT Slow Start")
        CC_stage[username] = "Slow Start"
        ssthresh[username] = 16
        window_size_locks[username] = threading.Lock()  # lock enabled
        sent_packets_locks[username] = threading.Lock()  # lock enabled
        udp_thread_kill[username] = False
        buffer = []  # file is read into buffer
        with open(f"../Server_Files/{requested_files.get(username)}", "rb") as f:
            data = f.read(PACKET_SIZE)  # split into packets
            while data:
                buffer.append(data)  # added to buffer
                data = f.read(PACKET_SIZE)  # split into packets
        print("size of buffer:", len(buffer))
        sockUDP.sendto(len(buffer).to_bytes(2, byteorder='big'), addr)  # turns length of buffer into byte code
        packet_sender_thread = threading.Thread(target=packet_sender, args=(sockUDP, addr, username, buffer))
        ack_receiver_thread = threading.Thread(target=ack_receiver, args=(sockUDP, username, len(buffer)))
        packet_sender_thread.setDaemon(True)
        ack_receiver_thread.setDaemon(True)
        packet_sender_thread.start()
        ack_receiver_thread.start()
        packet_sender_thread.join()
        ack_receiver_thread.join()
        # wait at this line until packet_sender and ack_receiver threads are done
        udp_ports_in_use.remove(sockUDP.getsockname()[1]-55000)  # removes port from ports_in_use
        sockUDP.close()  # close the udp socket


def ack_receiver(sockUDP: socket.socket, username: str, buffer_size: int):
    """

    :param sockUDP:
    :param username:
    :param buffer_size:
    Thread responsible for listening for acks from clients
    """
    last_ack_seq = -1
    dupAckcount = 0
    while not udp_thread_kill[username]:  # still more packets to be sent
        ack = sockUDP.recv(PACKET_SIZE).decode()[1:-1].split(
            "><")  # receive ack messaage and split up into parts: "ack" and seq num
        if ack[0] == "ack":
            # print("got ack for:", int(ack[1]))
            if int(ack[1]) >= buffer_size:  # ack for last packet was received
                udp_thread_kill[username] = True
            if int(ack[1]) == last_ack_seq:  # duplicate ack
                if CC_stage[username] == "Fast Recovery":
                    with window_size_locks[username]:
                        window_size[username] += 1  # window size increases by 1
                        # print("window size:", window_size[username])
                else:
                    dupAckcount += 1
                    if dupAckcount == 3:
                        print("*** 3 duplicate acks occurred")
                        dupack_seq[username] = int(ack[1])
                        ssthresh[username] = window_size[username] / 2  # threshold is reduced to window_size / 2
                        with window_size_locks[username]:
                            window_size[username] = window_size[
                                                        username] / 2 + 3  # window_size is reduced to threshold + 3
                            # print("window size:", window_size[username])
                        CC_stage[username] = "Fast Recovery"  # congestion control stage is now Fast Recovery which will later trigger the retransmitting of the packet
                        print("CC STAGE CHANGED TO Fast Recovery")
            else:
                last_ack_seq = int(ack[1])  # new ack
                dupAckcount = 0
                if CC_stage[username] == "Slow Start":
                    with window_size_locks[username]:
                        window_size[username] += 1  # window size increases by 1
                        # print("window size:", window_size[username])
                    if window_size[username] >= ssthresh[username]:  # once the window size has passed the threshold, the CC stage turned to congestion avoidance
                        CC_stage[username] = "Congestion Avoidance"
                        print("CC STAGE CHANGED TO Congestion Avoidance")
                elif CC_stage[username] == "Congestion Avoidance":
                    with window_size_locks[username]:
                        window_size[username] += 1 / window_size[username]  # window size increases by 1/window_size
                        # print("window size:", window_size[username])
                elif CC_stage[username] == "Fast Recovery":
                    with window_size_locks[username]:
                        window_size[username] = ssthresh[username]  # window size equals the threshold
                        # print("window size:", window_size[username])
                    CC_stage[username] = "Congestion Avoidance"
                    print("CC STAGE CHANGED TO Congestion Avoidance")
                for i in sent_packets[username].copy().keys():
                    if i < int(ack[1]):  # i is less than the seq num of the acked packet just received
                        with sent_packets_locks[username]:
                            del sent_packets.get(username)[i]  # delete from sent packets
        else:
            print("RECEIVED ERROR ON UDP!", ack[0])


def packet_sender(sockUDP: socket.socket, addr, username: str, buffer: list):
    """

    :param sockUDP:
    :param addr:
    :param username:
    :param buffer:
    Thread responsible for sending packets to the client. regularly and retransmission due to timeout or 3 dup acks
    """
    next_packet = 0
    timeout = 1.0  # if after 1 sec, ack for packet is not received, packet is retransmitted
    while not udp_thread_kill[username]:
        copy_sent_packets = sent_packets.get(username).copy()  # copy in order to avoid thread hogging
        curr_time = time.time()
        for seq, t in copy_sent_packets.items():
            if curr_time > t + timeout:  # timeout occurred
                print("*** timeout occurred:", seq)
                CC_stage[username] = "Slow Start"
                print("CC STAGE CHANGED TO Slow Start")
                with window_size_locks[username]:
                    ssthresh[username] = max(window_size[username] / 2, 1)  # threshold is reduced
                    window_size[username] = 1  # window size reduced to 1
                    # print("window size:", window_size[username])
                # print("sent timeout data seq:", seq)
                sockUDP.sendto(seq.to_bytes(2, byteorder='big') + buffer[seq], addr) #retransmit packet
                with sent_packets_locks[username]:
                    sent_packets.get(username)[seq] = time.time()  # reset time
        if dupack_seq[username] != -1: # 3 dup acks for the seq num
            # print("sent duplicate data seq:", dupack_seq[username])
            sockUDP.sendto(dupack_seq[username].to_bytes(2, byteorder='big') + buffer[dupack_seq[username]], addr)  #retransmit packet
            with sent_packets_locks[username]:
                sent_packets.get(username)[dupack_seq[username]] = time.time()  # reset time
            dupack_seq[username] = -1
        with sent_packets_locks[username]:
            with window_size_locks[username]:
                while next_packet < len(buffer) and len(sent_packets[username]) < int(window_size[username]):  # there is packet to be sent and not yet at window_size
                    # print("sent data seq:", next_packet)
                    sockUDP.sendto(next_packet.to_bytes(2, byteorder='big') + buffer[next_packet], addr)  # transmit packet
                    sent_packets.get(username)[next_packet] = time.time()  # set time
                    next_packet += 1


def next_available_udp_port() -> int:
    """
    This function determines the next available udp port to be used
    :return: next available port, a number between 55800-5815, or -1 if no ports are available
    """
    for i in range(16):
        if i not in udp_ports_in_use:
            udp_ports_in_use.append(i)
            return 55000 + i
    return -1


def sending_thread(conn: socket.socket, username: str):
    """

    :param conn:
    :param username:
    Thread responsible for sending messages to the client through the tcp connection.
    When a request comes in from a client, the listening_thread raises a flag in the flags_for_sender dict at the appropriate spot.
    The sending thread constantly checks the dict and sends what was requested to the client.
    """
    conn.send("<connected>".encode())
    while True:
        if flags_for_sender.get(username).get("get_users"):
            with user_lock:
                flags_for_sender.get(username)["get_users"] = False
                users = "<users_lst>"
                for user in list_of_users:  # go through list of users
                    users += f"<{user}>"
                users += "<end>"
                conn.send(users.encode())  # send list of users
        if flags_for_sender.get(username).get("get_list_file"):
            flags_for_sender.get(username)["get_list_file"] = False
            files = "<file_lst>"
            for file in list_of_server_files:  # go through list of files
                files += f"<{file}>"
            files += "<end>"
            conn.send(files.encode())  # send list of files
        if flags_for_sender.get(username).get("msg_lst"):
            with msg_lock:
                msgs = "<msg_lst>"
                for msg in flags_for_sender.get(username).get("msg_lst"):  # go through messages
                    msgs += f"<{msg}>"
                msgs += "<end>"
                conn.send(msgs.encode())  # send messages
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
    """

    :param conn:
    :param username:
    Thread responsible for listening to incoming requests from clients.
    Depending on the request, a flag is raised in the flags_for_sender dict at the appropriate spot.
    This then causes the sending_thread to send what is requested to client.
    """
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
                        with msg_lock:  # add msg to list
                            flags_for_sender.get(msg_list[1]).get("msg_lst").append(
                                f"(private) {username}: {msg_list[2]}")
                    else:
                        flags_for_sender.get(username)["msg_ERROR"] = True
                elif msg_list[0] == "set_msg_all":
                    with msg_lock:
                        for user in list_of_users:  # go through users and add msg to their lists
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
        except:
            continue


def start_server():
    """
    This function starts the server by creating and starting threads that are responsible for running the server's tcp and udp sockets.
    """
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
    """
    This function is called when the server window is exited.
    """
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

    # closes the tcp and udp sockets
    serverSocketTCP.close()
    serverSocketUDP.close()
