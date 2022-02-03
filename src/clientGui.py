import tkinter
from tkinter import *
import tkinter.scrolledtext as st
from tkinter.ttk import Progressbar

root = Tk()
root.title("Client")


def login():
    if login["text"] == "Login":
        login["text"] = "Logout"
        tempLabel = Label(root, text=user.get() + " connected to server " + host.get())
        tempLabel.grid(row=2, column=0)
    elif login["text"] == "Logout":
        login["text"] = "Login"
        tempLabel = Label(root, text=user.get() + " diconnected from server " + host.get())
        tempLabel.grid(row=2, column=0)



def send():
    tempLabel2 = Label(root, text=rec.get() + " should receive the following message " + message.get())
    tempLabel2.grid(row=2, column=0)


def downLoad():
    download["text"] = "proceed"
    import time
    progress['value'] = 20
    root.update_idletasks()
    time.sleep(0.5)

    progress['value'] = 40
    root.update_idletasks()
    time.sleep(0.5)

    progress['value'] = 50
    root.update_idletasks()
    time.sleep(0.5)

    progress['value'] = 60
    root.update_idletasks()
    time.sleep(0.5)

    progress['value'] = 80
    root.update_idletasks()
    time.sleep(0.5)

    progress['value'] = 100
    root.update_idletasks()
    time.sleep(0.5)

    progress['value'] = 80
    root.update_idletasks()
    time.sleep(0.5)

    progress['value'] = 60
    root.update_idletasks()
    time.sleep(0.5)

    progress['value'] = 50
    root.update_idletasks()
    time.sleep(0.5)

    progress['value'] = 40
    root.update_idletasks()
    time.sleep(0.5)

    progress['value'] = 20
    root.update_idletasks()
    time.sleep(0.5)
    progress['value'] = 0

#frames
topframe = LabelFrame(root)
topframe.grid(padx=15, pady=15)

messageframe = LabelFrame(root)
messageframe.grid(padx=15, pady=15)

txtframe = LabelFrame(root)
txtframe.grid(padx=30, pady=30)

fileframe = LabelFrame(root)
fileframe.grid(padx=15, pady=15)

#labels and buttons and entries
login = Button(topframe, text="Login", command=login)
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
user_list = Button(topframe, text="Current Online Users")
user_list.grid(row=0, column=5)
file_list = Button(topframe, text="Current Server Files")
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
sendm = Button(messageframe, text="Send", command=send)
sendm.grid(row=4, column=2)

input_box = st.ScrolledText(txtframe, width=85, height=25, font=("Times New Roman", 15))
input_box.grid(column=0, padx=10, pady=10)
input_box.insert(tkinter.INSERT,
                 "1. This \n will \n be \n changed \n to \n input \n incoming \n messages \n 2. This \n will \n be \n "
                 "changed \n to \n input \n incoming \n messages \n 3. This \n will \n be \n changed \n to \n input "
                 "\n incoming \n messages \n 4. This \n will \n be \n changed \n to \n input \n incoming \n messages")
input_box.configure(state='disabled')
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

root.mainloop()
