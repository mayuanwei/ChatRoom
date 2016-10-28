from asyncore import dispatcher
from asynchat import async_chat
import asyncore,socket

PORT = 5005

class ChatServer(dispatcher):
    def __init__(self,port):
        dispatcher.__init__(self)
        self.create_socket(socket.AF_INET,socket.SOCK_STREAM)
        self.set_reuse_addr()
        self.bind(('',port))
        self.listen(5)
        self.session = []

    def handle_accept(self):
        conn,addr = self.accept()
        print('connnection attemnpt from:',conn,addr)
        #self.session.append(ChatSession(conn))

class ChatSession(async_chat):
    def __init__(self,sock):
        async_chat.__init__(self)
        self.set_terminator('\r\n')
        self.data = []

    def collect_incoming_data(self, data):
        self.data.append(data)

    def found_terminator(self):
        line = ''.join(self.data)
        self.data = []
        print(line)

if __name__ == '__main__':
    s = ChatServer(PORT)
    try:
        asyncore.loop()
    except KeyboardInterrupt:pass