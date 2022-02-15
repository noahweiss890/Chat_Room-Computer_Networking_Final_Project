import select
import socket
import threading
import tkinter
from tkinter import *
import tkinter.scrolledtext as st
from tkinter.ttk import Progressbar


server_tcp = None
server_udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
connected = False
kill = False
user_name = ""


def connect_to_server():
    global server_tcp, connected, user_name
    if login["text"] == "Login":
        if user.get():
            login["text"] = "Logout"
            server_tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            ip_address = host.get()
            port = 50001
            server_tcp.connect((ip_address, port))
            user_name = user.get()
            server_tcp.send(f"<connect><{user_name}>".encode())
            connected = True
    elif login["text"] == "Logout":
        login["text"] = "Login"
        download["text"] = "Download"
        user_name = ""
        server_tcp.send("<disconnect>".encode())


def send_message():
    global server_tcp, connected
    if connected:
        to = rec.get()
        msg = message.get()
        if msg:
            if to:
                server_tcp.send(f"<set_msg><{to}><{msg}>".encode())
                txt = f"(to {to}) You: {msg}\n"
            else:
                server_tcp.send(f"<set_msg_all><{msg}>".encode())
                txt = f"(public) You: {msg}\n"
            input_box.insert(END, txt)
            input_box.see("end")
    else:
        txt = "(not logged in, please log in first)\n"
        input_box.insert(END, txt)
        input_box.see("end")


def get_user_list():
    global server_tcp, connected
    if connected:
        server_tcp.send("<get_users>".encode())
    else:
        txt = "(not logged in, please log in first)\n"
        input_box.insert(END, txt)
        input_box.see("end")


def get_file_list():
    global server_tcp, connected
    if connected:
        server_tcp.send("<get_list_file>".encode())
    else:
        txt = "(not logged in, please log in first)\n"
        input_box.insert(END, txt)
        input_box.see("end")


def download_file():
    global server_tcp, connected, server_udp
    if connected:
        if download["text"] == "Download":
            download["text"] = "Proceed"
            server_tcp.send(f"<download><{fileName.get()}>".encode())
        elif download["text"] == "Proceed":
            download["state"] = "disabled"
            server_udp.sendto(f"<connect><{user_name}>".encode(), ("localhost", 40002))
            receiving_udp = threading.Thread(target=receiving_udp_thread)
            receiving_udp.setDaemon(True)
            receiving_udp.start()
            server_tcp.send("<proceed>".encode())
    else:
        txt = "(not logged in, please log in first)\n"
        input_box.insert(END, txt)
        input_box.see("end")


def receiving_udp_thread():
    progress['value'] = 0
    root.update_idletasks()
    data = server_udp.recv(1024).decode()
    filesize = int(data)
    timeout = 3
    with open(f"../Downloaded_Files_From_Server/{saveAs.get()}", "wb") as f:
        while True:
            print(progress['value'])
            ready = select.select([server_udp], [], [], timeout)
            if ready[0]:
                data = server_udp.recv(1024)
                progress['value'] += len(data)*100/filesize
                root.update_idletasks()
                f.write(data)
            else:
                break


def listening_thread():
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
                txt = f"({user.get()} logged out)\n"
                input_box.insert(END, txt)
            elif message_from_server[0] == "server_down":
                login["text"] = "Login"
                download["text"] = "Download"
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
            elif message_from_server[0] == "username_ERROR":
                login["text"] = "Login"
                txt = "(ERROR: Username already in use! Choose a different one)\n"
                input_box.insert(END, txt)
                server_tcp.close()
                server_tcp = None
                connected = False
            elif message_from_server[0] == "msg_ERROR":
                txt = "(ERROR: there is no user with that username! Try again)\n"
                input_box.insert(END, txt)
            elif message_from_server[0] == "FileNotFound_ERROR":
                txt = "(ERROR: there is no file with that name on the server)\n"
                input_box.insert(END, txt)
                download["text"] = "Download"
            elif message_from_server[0] == "file_sent":
                download["state"] = "normal"
                download["text"] = "Download"
                txt = "(File was successfully downloaded from the server)\n"
                input_box.insert(END, txt)
            input_box.see("end")


def clear_inbox():
    input_box.delete(1.0, END)


def quit_me():
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
    topframe.grid(padx=15, pady=15)

    messageframe = LabelFrame(root)
    messageframe.grid(padx=15, pady=15)

    txtframe = LabelFrame(root)
    txtframe.grid(padx=30, pady=30)

    fileframe = LabelFrame(root)
    fileframe.grid(padx=15, pady=15)

    # labels and buttons and entries
    login = Button(topframe, text="Login", command=connect_to_server, fg='blue', background="yellow")
    login.pack()
    login.grid(row=0, column=0)
    name = Label(topframe, text="Username")
    name.grid(row=0, column=1)
    user = Entry(topframe, width=15)
    # user.insert(0, "Enter username here:")
    # user.configure(foreground="grey")
    user.grid(row=0, column=2)
    addr = Label(topframe, text="Host Address")
    addr.grid(row=0, column=3)
    localhost = StringVar(root, value='localhost')
    host = Entry(topframe, width=15, textvariable=localhost)
    # host.insert(0, "host:")
    # host.configure(foreground="grey")
    host.grid(row=0, column=4)
    user_list = Button(topframe, text="Current Online Users", command=get_user_list, fg='blue')
    user_list.grid(row=0, column=5)
    file_list = Button(topframe, text="Current Server_Files", command=get_file_list, fg='blue')
    file_list.grid(row=0, column=6)

    sendTo = Label(messageframe, text="Send to: (blank if all)")
    sendTo.grid(row=3, column=0)
    rec = Entry(messageframe, width=15)
    # rec.insert(0, "Enter client name:")
    # rec.configure(foreground="grey")
    rec.grid(row=4, column=0)
    messagelabel = Label(messageframe, text="Message")
    messagelabel.grid(row=3, column=1)
    message = Entry(messageframe, width=50)
    # message.insert(0, "Enter message here:")
    # message.configure(foreground="grey")
    message.grid(row=4, column=1)
    sendm = Button(messageframe, text="Send", command=send_message, fg='blue')
    sendm.grid(row=4, column=2)

    input_box = st.ScrolledText(txtframe, width=85, height=25, font=("Times New Roman", 15))
    input_box.grid(column=0, padx=10, pady=10)
    input_box.insert(tkinter.INSERT, "Welcome!\n")
    # input_box.configure(state='disabled')
    clear_button = Button(txtframe, text="Clear Inbox", command=clear_inbox, fg='blue')
    clear_button.grid(row=5, column=0)

    fileNameL = Label(fileframe, text="Server File Name")
    fileNameL.grid(row=7, column=0)
    fileName = Entry(fileframe, width=15)
    # fileName.insert(0, "file name:")
    # fileName.configure(foreground="grey")
    fileName.grid(row=8, column=0)
    SaveAsLabel = Label(fileframe, text="Save File As:")
    SaveAsLabel.grid(row=7, column=1)
    saveAs = Entry(fileframe, width=15)
    # saveAs.insert(0, "save as:")
    # saveAs.configure(foreground="grey")
    saveAs.grid(row=8, column=1)
    download = Button(fileframe, text="Download", command=download_file, fg='blue')
    download.grid(row=8, column=2)
    progress = Progressbar(fileframe, orient=HORIZONTAL, length=200, mode='determinate')
    progress.grid(row=9, column=0)

    server_listening_thread = threading.Thread(target=listening_thread)
    server_listening_thread.setDaemon(True)
    server_listening_thread.start()

    root.mainloop()

    while not kill:
        pass
