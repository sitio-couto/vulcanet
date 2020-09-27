
# Copyright (c) Twisted Matrix Laboratories.
# See LICENSE for details.
import json, inspect
from cmd import Cmd
from twisted.internet import reactor, protocol, threads, stdio
from twisted.protocols import basic
from twisted.web.client import Agent
from twisted.web.error import Error
from os import linesep
from twisted.python import threadable
threadable.init()

# a client protocol

class EchoClient(basic.LineReceiver):
    """Once connected, send a message, then print the result."""
    
    def connectionMade(self):
        print("You are connected to the call center.")
        stdio.StandardIO(UserInterface(CmdInterface(self)))
        
    def sendCommand(self, message):
        "Send command to call center server."
        self.transport.write(message)

    def dataReceived(self, data):
        "Exhibit server's reply and enable cmd."
        print(json.loads(data)['response'], "\n>> ", end="")
    
    def connectionLost(self, reason):
        print("\nConnection lost.")

    def disconnect(self):
        reactor.callLater(0, self.transport.loseConnection)

class EchoFactory(protocol.ClientFactory):
    protocol = EchoClient

    def clientConnectionFailed(self, connector, reason):
        print("Connection failed!")
        reactor.stop()
    
    def clientConnectionLost(self, connector, reason):
        print("Closing Application!")
        reactor.stop()

class CmdInterface(Cmd):
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
        self.cmd.onecmd(line.decode('utf-8'))

# this connects the protocol to a server running on port 8000
def main():
    f = EchoFactory()
    reactor.connectTCP("localhost", 5678, f)
    reactor.run()

# this only runs if the module was *not* imported
if __name__ == '__main__':
    main()
