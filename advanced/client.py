
# Copyright (c) Twisted Matrix Laboratories.
# See LICENSE for details.
import json, inspect
from cmd import Cmd
from twisted.internet import reactor, protocol, threads, defer
from twisted.web.client import Agent
from twisted.web.error import Error
from twisted.python import threadable
threadable.init()

# a client protocol

class EchoClient(protocol.Protocol):
    """Once connected, send a message, then print the result."""
    
    def connectionMade(self):
        print("You are connected to the call center.")
        # Call cmdloop after connection was stabilished, otherwise the 
        # transport attribute might be None(= "no connection")
        reactor.callInThread(CmdInterface(self).cmdloop)
        
    def sendCommand(self, message):
        "Send command to call center server."
        self.transport.write(message)

    def dataReceived(self, data):
        "Exhibit server's reply and enable cmd."
        print(json.loads(data)['response'])
    
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
        self.wait = False

    # Auxiliary Functions

    def jsonfy(self, args):
        '''Convert command and argumets to a JSON bytearray.'''
        command = inspect.stack()[1].function.split('_')[-1]
        json_str = json.dumps({"command":command, "args":args})
        return json_str.encode('utf-8')

    def eventLaucher(self, msg):
        '''Request event from thread and print result.'''
        try:
            threads.blockingCallFromThread(
                reactor, self.agent.sendCommand, msg)
        except Error as exc:
            print(exc)
    
    def disconnect(self):
        try:
            threads.blockingCallFromThread(
                reactor, self.agent.disconnect)
        except Error as exc:
            print(exc)

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
        self.disconnect()
        return True
    def do_EOF(self, args):
        self.disconnect()
        return True

# this connects the protocol to a server running on port 8000
def main():
    f = EchoFactory()
    reactor.connectTCP("localhost", 5678, f)
    reactor.run()

# this only runs if the module was *not* imported
if __name__ == '__main__':
    main()
