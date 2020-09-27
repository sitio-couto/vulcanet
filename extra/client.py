import json, inspect
from cmd import Cmd
from os import linesep
from twisted.protocols import basic
from twisted.web.error import Error
from twisted.internet import reactor, protocol, threads, stdio

# a client protocol

class Client(basic.LineReceiver):
    '''Implements methods for communicating with the server.'''
    
    def connectionMade(self):
        print("You are connected to the call center. \n>> ", end="")
        stdio.StandardIO(UserInterface(CmdInterface(self))) # Initialize stdin input protocol
        
    def sendCommand(self, message):
        "Send command to call center server."
        self.transport.write(message)

    def dataReceived(self, data):
        "Exhibit server's reply."
        print(json.loads(data)['response'], "\n>> ", end="")
    
    def disconnect(self):
        self.transport.loseConnection()

    def connectionLost(self, reason):
        print("\nConnection lost.")

class ClientFactory(protocol.ClientFactory):
    '''Implements persistent aspects among connections.'''
    protocol = Client

    def clientConnectionFailed(self, connector, reason):
        print("Connection failed!")
        reactor.stop()
    
    def clientConnectionLost(self, connector, reason):
        print("Closing Application!")
        reactor.stop()

class CmdInterface(Cmd):
    '''Implements communication between commands and the Client.'''

    def __init__(self, agent):
        Cmd.__init__(self)
        self.agent = agent

    # Auxiliary Functions

    def jsonfy(self, args):
        '''Convert command and argumets to a JSON bytearray.'''
        command = inspect.stack()[1].function.split('_')[-1]
        json_str = json.dumps({"command":command, "args":args})
        return json_str.encode('utf-8')

    def eventLaucher(self, msg):
        '''Request event from thread and print result.'''
        try: self.agent.sendCommand(msg)
        except Error as exc: print(exc)

    # List of Available Commands

    def do_call(self, args):
        self.eventLaucher(self.jsonfy(args))
    def do_answer(self, args):
        self.eventLaucher(self.jsonfy(args))
    def do_reject(self, args):
        self.eventLaucher(self.jsonfy(args))
    def do_hangup(self, args):
        self.eventLaucher(self.jsonfy(args))

    # Terminator Functions

    def do_exit(self, args):
        self.agent.disconnect()
        return True
    def do_EOF(self, args):
        self.agent.disconnect()
        return True

class UserInterface(basic.LineReceiver):
    '''Creates a protocol with stdin for in-line commands.'''
    delimiter = linesep.encode("ascii")

    def __init__(self, cmd):
        self.cmd = cmd

    def lineReceived(self, line):
        '''Read line and send it to CmdInterface for processing.'''
        self.cmd.onecmd(line.decode('utf-8'))

# this connects the protocol to a server running on port 8000
def main():
    f = ClientFactory()
    reactor.connectTCP("localhost", 5678, f) # connect localhost:5678
    reactor.run()

if __name__ == '__main__':
    main()
