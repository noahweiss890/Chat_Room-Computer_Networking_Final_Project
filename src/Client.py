import socket
import threading
import time
import tkinter
from tkinter import *
import tkinter.scrolledtext as st
from tkinter.ttk import Progressbar


server_tcp = None
server_udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
connected = False
kill = False
user_name = ""
PACKET_SIZE = 2048


def connect_to_server():
    """
    This function is responsible for connecting the client to the server.
    """
    global server_tcp, connected, user_name
    if login["text"] == "Login":
        if user.get():
            login["text"] = "Logout"
            server_tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # creates a tcp connection
            ip_address = host.get()  # what is written in the host box in the GUI
            port = 50000
            server_tcp.connect((ip_address, port))  # server connects to ip_address and port
            user_name = user.get()  # what is written in the username box in the GUI
            user["state"] = "disabled"
            host["state"] = "disabled"
            server_tcp.send(f"<connect><{user_name}>".encode())  # send connection request
            connected = True
    elif login["text"] == "Logout":
        login["text"] = "Login"
        download["text"] = "Download"
        download["state"] = "normal"
        user["state"] = "normal"
        host["state"] = "normal"
        user_name = ""
        server_tcp.send("<disconnect>".encode())  # send disconnection request


def send_message():
    """
    This function is responsible for sending messages from one client to another or to all.
    """
    global server_tcp, connected
    if connected:
        to = rec.get()  # what is written in the to box in the GUI
        msg = message.get()  # what is written in the msg box in the GUI
        message.delete(0, END)
        if msg:
            if to:  # to a specific client and not to all
                server_tcp.send(f"<set_msg><{to}><{msg}>".encode())
                txt = f"(to {to}) You: {msg}\n"  # to be printed on to the GUI screen
            else:  # send to all
                server_tcp.send(f"<set_msg_all><{msg}>".encode())
                txt = f"(public) You: {msg}\n"  # to be printed on to the GUI screen
            input_box.insert(END, txt)
            input_box.see("end")
    else:
        txt = "(not logged in, please log in first)\n"
        input_box.insert(END, txt)
        input_box.see("end")


def get_user_list():
    """
    This function is responsible for sending request for the user list.
    """
    global server_tcp, connected
    if connected:
        server_tcp.send("<get_users>".encode())
    else:
        txt = "(not logged in, please log in first)\n"
        input_box.insert(END, txt)
        input_box.see("end")


def get_file_list():
    """
    This function is responsible for sending request for the file list.
    """
    global server_tcp, connected
    if connected:
        server_tcp.send("<get_list_file>".encode())
    else:
        txt = "(not logged in, please log in first)\n"
        input_box.insert(END, txt)
        input_box.see("end")


def download_file():
    """
    Thread responsible for downloading file from the server over udp connection and creating and starting the receiving_udp thread.
    The client requests to download over tcp and proceeds to udp.
    """
    global server_tcp, connected, server_udp
    if connected:
        if download["text"] == "Download":
            download["text"] = "Proceed"
            server_tcp.send(f"<download><{fileName.get()}>".encode())
        elif download["text"] == "Proceed":
            if saveAs.get():  # what is written in saveAs box in GUI
                download["state"] = "disabled"
                server_udp.sendto(f"<SYN><{user_name}>".encode(), (host.get(), 40000))  # send SYN, part 1 of handshake.
                data, addr = server_udp.recvfrom(1024)
                if data.decode()[1:-1] == "SYN ACK":  # received SYN ACK, part 2 of handshake.
                    server_udp.sendto("<ACK>".encode(), addr) # send ACK, part 3 of handshake.
                    print("\nHELLO IM HERE!\n")
                    receiving_udp = threading.Thread(target=receiving_udp_thread, args=(addr, ))
                    receiving_udp.setDaemon(True)
                    receiving_udp.start()
                server_tcp.send("<proceed>".encode())
            else:
                txt = "(ERROR: please enter a file name for the downloaded file)\n"
                input_box.insert(END, txt)
                input_box.see("end")
    else:
        txt = "(not logged in, please log in first)\n"
        input_box.insert(END, txt)
        input_box.see("end")


def receiving_udp_thread(addr):
    """
    Thread responsible for receiving packets over udp from the server in order to download files.
    """
    progress['value'] = 0
    root.update_idletasks()
    size_data = server_udp.recv(2)
    size = size_data[0]*16**2 + size_data[1]  # converts bytes from base 16 to base 10 number
    print("\nSIZE:")
    # print(size)
    print()
    print("size", size)
    buffer = [None]*size
    print("progress:", progress['value'])
    # once1 = True
    # once2 = True
    while True:
        print("gonna receive")
        data = server_udp.recv(PACKET_SIZE+2)  # added 2 bytes for seq number
        seq = data[0]*16**2 + data[1]
        # activate this to check if duplicate ack protocol works
        # if seq == 16 and once1:
        #     once1 = False
        #     continue
        # activate this to check if timeout protocol works
        # if seq == 50 and once2:
        #     once2 = False
        #     time.sleep(1.1)
        #     continue
        print("got data seq:", seq)
        if not buffer[seq]:
            buffer[seq] = data[2:]  # start at 2 to pass seq num
            progress['value'] += 100/int(size)
            print("progress:", progress['value'])
            root.update_idletasks()
        ack_seq = -1
        for i, data in enumerate(buffer):  # discovers proper ack number
            if data is None:  # lowest spot with no data
                ack_seq = i
                break
        if ack_seq == -1:  # received all packets
            server_udp.sendto(f"<ack><{size}>".encode(), addr)
            print("sent ack for:", size)
            break
        server_udp.sendto(f"<ack><{ack_seq}>".encode(), addr)  # send ack
        print("sent ack for:", ack_seq)
    with open(f"../Downloaded_Files_From_Server/{saveAs.get()}", "wb") as f:
        for data_info in buffer:  # take info from buffer and write in saveAs file
            f.write(data_info)
    download["state"] = "normal"
    download["text"] = "Download"
    txt = f"({saveAs.get()} was successfully downloaded from the server, the last byte was {buffer[-1][-1]})\n"
    input_box.insert(END, txt)
    input_box.see("end")


def listening_thread():
    """
    Thread responsible for listening for messages from the server and activating the corresponding parts of the GUI in return.
    """
    global server_tcp, connected
    while True:
        if connected:
            message_from_server = server_tcp.recv(2048).decode()[1:-1].split("><")
            if message_from_server[0] == "connected":
                txt = f"({user.get()} logged in)\n"
                input_box.insert(END, txt)
            elif message_from_server[0] == "disconnected":
                server_tcp.close()
                server_tcp = None
                connected = False
                # txt = f"({user.get()} logged out)\n"
                # input_box.insert(END, txt)
            elif message_from_server[0] == "server_down":
                login["text"] = "Login"
                user["state"] = "normal"
                host["state"] = "normal"
                download["text"] = "Download"
                download["state"] = "normal"
                txt = "(ERROR: Server is down)\n"
                input_box.insert(END, txt)
                server_tcp = None
                connected = False
            elif message_from_server[0] == "users_lst":
                txt = "\n-- online list --\n"
                for username in message_from_server[1:-1]:
                    txt += f"{username}\n"
                txt += "-- end list --\n\n"
                input_box.insert(END, txt)
            elif message_from_server[0] == "file_lst":
                txt = "\n-- Server File List --\n"
                for file in message_from_server[1:-1]:
                    txt += f"{file}\n"
                txt += "-- End Server File List --\n\n"
                input_box.insert(END, txt)
            elif message_from_server[0] == "msg_lst":
                txt = ""
                for msg in message_from_server[1:-1]:
                    txt += f"{msg}\n"
                input_box.insert(END, txt)
            elif message_from_server[0] == "user_updates":
                txt = ""
                for updt in message_from_server[1:-1]:
                    txt += f"{updt}\n"
                input_box.insert(END, txt)
            elif message_from_server[0] == "username_ERROR":
                login["text"] = "Login"
                user["state"] = "normal"
                host["state"] = "normal"
                txt = "(ERROR: Username already in use! Choose a different one)\n"
                input_box.insert(END, txt)
                server_tcp.close()
                server_tcp = None
                connected = False
            elif message_from_server[0] == "msg_ERROR":
                txt = "(ERROR: there is no user with that username signed in! Try again)\n"
                input_box.insert(END, txt)
            elif message_from_server[0] == "FileNotFound_ERROR":
                txt = "(ERROR: there is no file with that name on the server)\n"
                input_box.insert(END, txt)
                download["text"] = "Download"
            input_box.see("end")


def clear_inbox():
    """
    This function clears the client's inbox screen
    """
    input_box.delete(1.0, END)


def quit_me():
    """
    This function is called when the client window is exited.
    """
    global kill
    if connected:
        server_tcp.send("<disconnect>".encode())
    root.quit()
    root.destroy()
    kill = True


if __name__ == '__main__':
    root = Tk()
    root.title("Client")
    root.protocol("WM_DELETE_WINDOW", quit_me)

    # frames
    topframe = LabelFrame(root)
    topframe.grid(padx=15, pady=10)

    messageframe = LabelFrame(root)
    messageframe.grid(padx=15, pady=10)

    txtframe = LabelFrame(root)
    txtframe.grid(padx=30, pady=15)

    fileframe = LabelFrame(root)
    fileframe.grid(padx=15, pady=10)

    # labels and buttons and entries
    login = Button(topframe, text="Login", command=connect_to_server, fg='blue', background="yellow")
    login.pack()
    login.grid(row=0, column=0)
    name = Label(topframe, text="Username")
    name.grid(row=0, column=1)
    user = Entry(topframe, width=15)
    user.grid(row=0, column=2)
    addr = Label(topframe, text="Host Address")
    addr.grid(row=0, column=3)
    defaulthost = StringVar(root, value='0.0.0.0')
    host = Entry(topframe, width=15, textvariable=defaulthost)
    host.grid(row=0, column=4)
    user_list = Button(topframe, text="Current Online Users", command=get_user_list, fg='blue')
    user_list.grid(row=0, column=5)
    file_list = Button(topframe, text="Current Server_Files", command=get_file_list, fg='blue')
    file_list.grid(row=0, column=6)

    sendTo = Label(messageframe, text="Send to: (blank if all)")
    sendTo.grid(row=3, column=0)
    rec = Entry(messageframe, width=15)
    rec.grid(row=4, column=0)
    messagelabel = Label(messageframe, text="Message")
    messagelabel.grid(row=3, column=1)
    message = Entry(messageframe, width=50)
    message.grid(row=4, column=1)
    sendm = Button(messageframe, text="Send", command=send_message, fg='blue')
    sendm.grid(row=4, column=2)

    input_box = st.ScrolledText(txtframe, width=85, height=15, font=("Times New Roman", 15))
    input_box.grid(column=0, padx=10, pady=10)
    input_box.insert(tkinter.INSERT, "Welcome!\n")
    clear_button = Button(txtframe, text="Clear Inbox", command=clear_inbox, fg='blue')
    clear_button.grid(row=5, column=0)

    fileNameL = Label(fileframe, text="Server File Name")
    fileNameL.grid(row=7, column=0)
    fileName = Entry(fileframe, width=15)
    fileName.grid(row=8, column=0)
    SaveAsLabel = Label(fileframe, text="Save File As:")
    SaveAsLabel.grid(row=7, column=1)
    saveAs = Entry(fileframe, width=15)
    saveAs.grid(row=8, column=1)
    download = Button(fileframe, text="Download", command=download_file, fg='blue')
    download.grid(row=8, column=2)
    progress = Progressbar(fileframe, orient=HORIZONTAL, length=200, mode='determinate')
    progress.grid(row=9, column=0)

    server_listening_thread = threading.Thread(target=listening_thread)  # create server_listening_thread
    server_listening_thread.setDaemon(True)  # set thread as Daemon
    server_listening_thread.start()  # start thread

    root.mainloop()

    while not kill:
        pass
