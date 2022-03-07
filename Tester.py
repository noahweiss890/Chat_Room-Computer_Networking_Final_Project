import unittest
import socket


class MyTestCase(unittest.TestCase):
    """
    This is a tester that checks if the server executes the basic features of the messaging application
    To run this tester, start the server and then start the testers.
    """

    def test_connection(self):
        """
        checks if client can connect to the server
        """
        server_tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        ip_address = '0.0.0.0'
        port = 50000
        server_tcp.connect((ip_address, port))
        user_name = "tikshoret-man"
        server_tcp.send(f"<connect><{user_name}>".encode())
        message_from_server = server_tcp.recv(2048).decode()[1:-1].split("><")
        self.assertEqual(message_from_server[0], "connected")
        server_tcp.close()

    def test_users_online(self):
        """
        checks if the server returns the correct list of users
        """
        server_tcp1 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        ip_address = '0.0.0.0'
        port = 50000
        server_tcp1.connect((ip_address, port))
        user_name = "bob"
        server_tcp1.send(f"<connect><{user_name}>".encode())
        server_tcp1.recv(2048).decode()[1:-1].split("><")

        server_tcp2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        ip_address = '0.0.0.0'
        port = 50000
        server_tcp2.connect((ip_address, port))
        user_name = "alice"
        server_tcp2.send(f"<connect><{user_name}>".encode())
        server_tcp2.recv(2048).decode()[1:-1].split("><")

        server_tcp1.send("<get_users>".encode())

        message_from_server = server_tcp1.recv(2048).decode()[1:-1].split("><")
        self.assertTrue("bob" in message_from_server[1:-1])
        self.assertTrue("alice" in message_from_server[1:-1])

        server_tcp1.close()
        server_tcp2.close()

    def test_message_sent(self):
        """
        checks if the server successfully sends the message to another client
        """
        server_tcp1 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        ip_address = '0.0.0.0'
        port = 50000
        server_tcp1.connect((ip_address, port))
        user_name = "tommy"
        server_tcp1.send(f"<connect><{user_name}>".encode())
        server_tcp1.recv(2048).decode()[1:-1].split("><")

        server_tcp2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        ip_address = '0.0.0.0'
        port = 50000
        server_tcp2.connect((ip_address, port))
        user_name = "gina"
        server_tcp2.send(f"<connect><{user_name}>".encode())
        server_tcp2.recv(2048).decode()[1:-1].split("><")

        msg = "were half way there"
        server_tcp1.send(f"<set_msg><gina><{msg}>".encode())

        message_from_server = server_tcp2.recv(2048).decode()[1:-1].split("><")
        self.assertEqual(message_from_server[1], "(private) tommy: were half way there")

        server_tcp1.close()
        server_tcp2.close()


if __name__ == '__main__':
    unittest.main()
