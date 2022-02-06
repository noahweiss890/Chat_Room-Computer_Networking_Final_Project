import socket
import threading
import tkinter
from tkinter import *
import tkinter.scrolledtext as st
from tkinter.ttk import Progressbar


flags = {"login": False, }
# lock = threading.Lock()
server = None
connected = False


def connect_to_server():
    global server, connected
    if login["text"] == "Login":
        login["text"] = "Logout"
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        ip_address = host.get()
        port = 50004
        server.connect((ip_address, port))
        username = user.get()
        server.send(f"<connect><{username}>".encode())
        connected = True
    elif login["text"] == "Logout":
        login["text"] = "Login"
        server.send("<disconnect>".encode())


def send_message():
    global server, connected
    if connected:
        to = rec.get()
        msg = message.get()
        if to:
            server.send(f"<set_msg><{to}><{msg}>".encode())
        else:
            server.send(f"<set_msg_all><{msg}>".encode())
        txt = f"You: {msg}\n"
    else:
        txt = "(not logged in, please log in first)\n"
    input_box.insert(END, txt)


def get_user_list():
    global server, connected
    if connected:
        server.send("<get_users>".encode())
    else:
        txt = "(not logged in, please log in first)\n"
        input_box.insert(END, txt)


def get_file_list():
    global server, connected
    if connected:
        server.send("<get_list_file>".encode())
    else:
        txt = "(not logged in, please log in first)\n"
        input_box.insert(END, txt)


# def sending_thread():
#     global server, connected
#
#     while True:
#         print("\nChoose an option:\n"
#               "1. Connect to server\n"
#               "2. Disconnect from server\n"
#               "3. Send message to a user\n"
#               "4. Send message to all users\n"
#               "5. See who is signed in\n"
#               "6. See what files are on the server\n"
#               "7. Request to download file\n"
#               "8. Download file from server\n")
#
#         opt = input("Option: ")
#
#         if connected or opt == "1":
#             if opt == "1":
#                 if not server:
#                     connect_to_server()
#                 else:
#                     print("Already connected to server!")
#             elif opt == "2":
#                 server.send("<disconnect>".encode())
#             elif opt == "3":
#                 send_message()
#             elif opt == "4":
#                 broadcast_message()
#             elif opt == "5":
#                 server.send("<get_users>".encode())
#             elif opt == "6":
#                 server.send("<get_list_file>".encode())
#             elif opt == "7":
#                 file = input("Enter name of file to download: ")
#                 server.send(f"<download><{file}>".encode())
#             elif opt == "8":
#                 server.send("<proceed>".encode())
#             else:
#                 print("INVALID INPUT! TRY AGAIN!")
#         else:
#             print("Not connected to server! Please connect to server")


def listening_thread():
    global server, connected
    while True:
        if connected:
            message_from_server = server.recv(2048).decode()[1:-1].split("><")
            if message_from_server[0] == "connected":
                txt = f"({user.get()} logged in)\n"
                input_box.insert(END, txt)
            elif message_from_server[0] == "disconnected":
                server.close()
                server = None
                connected = False
                txt = f"({user.get()} logged out)\n"
                input_box.insert(END, txt)
            elif message_from_server[0] == "users_lst":
                txt = "-- online list --\n"
                for username in message_from_server[1:-1]:
                    txt += f"{username}\n"
                txt += "-- end list --\n"
                input_box.insert(END, txt)
            elif message_from_server[0] == "file_lst":
                print("-- Server File List --")
                for file in message_from_server[1:-1]:
                    print(file)
                print("-- End Server File List --")
            elif message_from_server[0] == "msg_lst":
                txt = ""
                for msg in message_from_server[1:-1]:
                    txt += f"{msg}\n"
                input_box.insert(END, txt)
            elif message_from_server[0] == "username_ERROR":
                txt = "(ERROR: Username already in use! Choose a different one)"
                input_box.insert(END, txt)
                server.close()
                server = None
                connected = False
            elif message_from_server[0] == "msg_ERROR":
                txt = "(ERROR: there is no user with that username! Try again)"
                input_box.insert(END, txt)
            elif message_from_server[0] == "server_closed":
                server.close()
                server = None
                connected = False
                txt = "(ERROR: Server down)"
                input_box.insert(END, txt)


def downLoad():
    download["text"] = "proceed"


if __name__ == '__main__':
    root = Tk()
    root.title("Client")

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
    login = Button(topframe, text="Login", command=connect_to_server)
    login.grid(row=0, column=0)
    name = Label(topframe, text="Enter Username")
    name.grid(row=0, column=1)
    user = Entry(topframe, width=15)
    # user.insert(0, "Enter username here:")
    # user.configure(foreground="grey")
    user.grid(row=0, column=2)
    addr = Label(topframe, text="Enter host address")
    addr.grid(row=0, column=3)
    host = Entry(topframe, width=15)
    # host.insert(0, "host:")
    # host.configure(foreground="grey")
    host.grid(row=0, column=4)
    user_list = Button(topframe, text="Current Online Users", command=get_user_list)
    user_list.grid(row=0, column=5)
    file_list = Button(topframe, text="Current Server Files", command=get_file_list)
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
    sendm = Button(messageframe, text="Send", command=send_message)
    sendm.grid(row=4, column=2)

    input_box = st.ScrolledText(txtframe, width=85, height=25, font=("Times New Roman", 15))
    input_box.grid(column=0, padx=10, pady=10)
    input_box.insert(tkinter.INSERT, "Welcome!\n")
    # input_box.configure(state='disabled')
    clear_button = Button(txtframe, text="Clear Inbox")
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
    download = Button(fileframe, text="Download", command=downLoad)
    download.grid(row=8, column=2)
    progress = Progressbar(fileframe, orient=HORIZONTAL, length=100, mode='indeterminate')
    progress.grid(row=9, column=0)

    # server_sending_thread = threading.Thread(target=sending_thread)
    server_listening_thread = threading.Thread(target=listening_thread)
    # server_sending_thread.start()
    server_listening_thread.start()

    root.mainloop()
