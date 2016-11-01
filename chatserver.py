from asyncore import dispatcher
from asynchat import async_chat
import asyncore,socket

PORT = 5005
NAME = 'TestChat'

class EndSession(Exception):pass

class CommandHandler:
    '''处理命令的超类'''

    '''处理未知命令'''
    def unknown(self,session,cmd):
        session.push(('Unknown command: %s\r\n' % cmd).encode())

    '''处理命令，然后调用子类处理命令的方法'''
    def handle(self,session,line):
        if not line.strip():return
        part = line.spit(' ',1)
        cmd = part[0]
        try:line = part[1].strip()
        except IndexError:
            line = ''

        method = getattr(self,'do_'+cmd,None)
        try:
            method(session,line)
        except TypeError:
            self.unknown(session,cmd)

class Room(CommandHandler):
    def __init__(self,server):
        self.server = server
        self.sessions = []

    '''单用户进入房间'''
    def add(self,session):
        self.sessions.append(session)

    '''单用户离开房间'''
    def remove(self,session):
        self.sessions.remove(session)

    '''发送用户消息'''
    def broadcast(self,line):
        for session in self.sessions:
            session.push(line.encode())

    '''处理logout命令，退出房间'''
    def do_logout(self,session,line):
        raise EndSession

class LoginRoom(Room):
    '''为连接上的用户准备的房间'''

    def add(self,session):
        Room.add(self,session)
        self.broadcast(('Welcome to %s\r\n' % self.server.name))

    '''处理未知命令（除login和logout）'''
    def unknown(self,session,cmd):
        session.push(('Please log in \nUse "login"\r\n').encode())

    def do_login(self,session,line):
        name = line.strip()
        if not name:
            session.push(('Please enter a name\r\n').encode())
        elif name in self.server.users:
            session.push(('The name "%s" is taken.\r\n' % name).encode())
            session.push(('Please try again.\r\n').encode())
        else:
            session.name = name
            session.enter(self.server.main_room)

class ChatRoom(Room):
    '''为用户准备的聊天室'''

    def add(self,session):
        Room.add(self,session)
        self.broadcast(session.name + ' has entered the room.\r\n')
        self.server.users[session.name] = session

    def remove(self,session):
        Room.remove(self,session)
        self.broadcast(session.name + ' has left the room.\r\n')

    '''say命令，处理用户发送的信息'''
    def do_say(self,session,line):
        self.broadcast(session.name + ':' + line + '\r\n')

    '''look命令，查看谁在房间'''
    def do_look(self,session,line):
        session.push(('The following are in this room:\r\n').encode())
        for other in self.sessions:
            session.push((other.name + '\r\n').encode())

    '''who命令，查看谁在服务器'''
    def do_who(self,session,line):
        session.push(('The following are logged in:\r\n').encode())
        for name in self.server.users:
            session.push((name + '\r\n').encode())

class LogoutRoom(Room):
    '''单用户准备的房间，将用户从服务器移除'''

    def add(self,session):
        try:
            del self.server.users[session.name]
        except:pass

class ChatServer(dispatcher):
    '''启动服务器，负责客户端连接'''
    def __init__(self,port,name):
        dispatcher.__init__(self)
        self.create_socket(socket.AF_INET,socket.SOCK_STREAM)
        self.set_reuse_addr()
        self.bind(('',port))
        self.listen(5)
        self.users = {}
        self.name =name
        '''创建一个房间'''
        self.main_room = ChatRoom(self)

    '''处理客户端连接（session）'''
    def handle_accept(self):
        conn,addr = self.accept()
        print('connnection attemnpt from:',conn,addr)
        ChatSession(self,conn)

class ChatSession(async_chat):
    '''单会话，负责和单用户通信'''

    def __init__(self,server,sock):
        async_chat.__init__(self,sock)
        self.set_terminator('\r\n'.encode())
        self.data = []
        self.server = server
        '''会话开始于LoginRoom中'''
        self.enter(LoginRoom(server))

    '''从当前房间移除自身，并将自身添加到下一个房间'''
    def enter(self,room):
        try:
            cur = self.room
        except:pass
        else:cur.remove(self)
        self.room = room
        room.add(self)

    '''收集用户输入'''
    def collect_incoming_data(self, data):
        self.data.append(data.decode())

    '''处理用户输入'''
    def found_terminator(self):
        line = ''.join(self.data)
        self.data = []
        try:self.room.handle(self,line)
        except EndSession:
            self.handle_close()

    '''处理用户退出'''
    def handle_close(self):
        async_chat.handle_close(self)
        self.enter(LogoutRoom(self.server))

if __name__ == '__main__':
    s = ChatServer(PORT,NAME)
    try:
        asyncore.loop()
    except KeyboardInterrupt:pass