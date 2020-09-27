from enum import Enum
import json
from collections import deque
from twisted.internet import reactor, protocol

class Operator():
    '''Implements individual Operator actions and states.'''
    States = Enum("state", "AVAILABLE RINGING BUSY")
    
    def __init__(self, id):
        self.id = id
        self.state = Operator.States.AVAILABLE
        self.call       = None # ID of the current assingned call
        self.timeout_id = None # Reference to timeout callback when ringing

    # State Transition Fuctions

    def ring(self, call):
        if self.is_available():
            self.state = Operator.States.RINGING
            self.call = call
            return True
        return False

    def hangup(self):
        if self.is_busy() or self.is_ringing():
            self.state = Operator.States.AVAILABLE
            self.call = None
            return True
        return False

    def reject(self):
        if self.is_ringing():
            self.state = Operator.States.AVAILABLE
            call = self.call
            self.call = None
            return call
        return False

    def answer(self):
        if self.is_ringing():
            self.state = Operator.States.BUSY
            return True
        return False

    # State Evaluation Functions

    def is_available(self):
        return self.state == Operator.States.AVAILABLE
    def is_ringing(self):
        return self.state == Operator.States.RINGING
    def is_busy(self):
        return self.state == Operator.States.BUSY

class Operators():
    '''Implements methods for a set of operators.'''
    def __init__(self, operators):
        self.operators = {op.id:op for op in operators}

    def ring_operators(self, call):
        '''Attempt to call operators and assign/hold a call.'''
        for op in self.operators.values():
            if op.ring(call) : return op
        return None
    
    def search_call(self, call):
        '''Return if an Operator has <call> assigned to it.'''
        for op in self.operators.values():
            if op.call == call : return op
        return None

    def get(self, op_id):
        return self.operators.get(op_id, None)

class Queue():
    ''''Wrapper for collections.deque Class.'''
    def __init__(self)     : self.queue = deque()
    def hold(self, call)   : self.queue.appendleft(call)
    def next(self)         : return self.queue.pop()
    def has(self, call)    : return call in self.queue
    def remove(self, call) : self.queue.remove(call)
    def not_empty(self)    : return bool(self.queue)
    def first(self, call)  : self.queue.append(call)

class CallManager():
    '''Coordinate call-operator assignments and responses to client side.'''
    def __init__(self, operators):
        self.operators = Operators(operators) # Working Operators
        self.protocol = None # Reference to client communication protocol
        self.queue = Queue() # Calls pool

    def set_timeout(self, call_id, op):
        '''Register count-down based call back to terminate call.'''
        op.timeout_id = reactor.callLater(
            10, self.protocol.checkTimeout, call_id)

    def do_timeout(self, call_id, msg=""):
        '''Terminate call if it has been ringing for more than 10s.'''
        operator = self.operators.search_call(call_id)
        if operator and operator.is_ringing():
            msg += f"Call {operator.call} ignored by operator {operator.id}"
            operator.hangup()
            if self.queue.not_empty() : msg += f"\n{self.do_call(None)}"
        return msg

    def do_call(self, call, msg=""):
        '''Initiate, unqueue or queue a call.'''
        # Check if it's a new or queue call
        if call:
            call = int(call)
            msg += f"Call {call} received\n"
        else:    
            call = self.queue.next()
        
        # Try to contact a operator
        operator = self.operators.ring_operators(call)
        if operator:
            msg += f"Call {call} ringing for operator {operator.id}"
            self.set_timeout(call, operator)
        else:
            self.queue.hold(call)
            msg += f"Call {call} waiting in queue"
        
        return msg
            
    def do_answer(self, op_id, msg=""):
        '''Answer ringing call for Operator <op_id>.'''
        operator = self.operators.get(op_id)
        if operator.answer():
            msg += f"Call {operator.call} answered by operator {op_id}"
        return msg

    def do_reject(self, op_id, msg=""):
        '''Reject ringing call for Operator <op_id>.'''
        operator = self.operators.get(op_id)
        operator.timeout_id.cancel() # Cancel timeout callback
        call = operator.reject()
        msg += f"Call {call} rejected by operator {op_id}\n"
        self.queue.first(call) # Return rejected call to the front of the queue
        msg += self.do_call(None)
        return msg

    def do_hangup(self, call, msg=""):
        '''Hangup ongoing of queued call <call>.'''
        call = int(call)
        # Check if call is either on queue or with an operator and end it
        if self.queue.has(call):
            self.queue.remove(call)
            msg += f"Call {call} missed"
        else:
            op = self.operators.search_call(call)
            if op:
                if op.is_busy():
                    msg += f"Call {call} finished and operator {op.id} available"
                elif op.is_ringing():
                    msg += f"Call {call} missed"
                op.hangup()
            if self.queue.not_empty() : msg += f"\n{self.do_call(None)}"
        
        return msg

class CallCenterProtocol(protocol.Protocol):
    '''Implements interface between the CallManager and the Client.'''

    def __init__(self, factory):
        self.factory = factory
        factory.manager.protocol = self # Allows manager to access protocol functions

    def jsonfy(self, args):
        '''Convert reply to a JSON bytearray.'''
        json_str = json.dumps({"response":args})
        return json_str.encode('utf-8')

    def checkTimeout(self, call_id):
        '''Function for setting up countdown-based callbacks'''
        msg = self.factory.manager.do_timeout(call_id)
        if msg : self.transport.write(self.jsonfy(msg))

    def dataReceived(self, data):
        '''Process command received from client.'''
        data = json.loads(data)
        method = getattr(self.factory.manager, "do_"+data['command']) # retrive method addr
        msg = method(data['args'])
        self.transport.write(self.jsonfy(msg))

class CallCenterFactory(protocol.ServerFactory):
    "Factory to mantain persistent data across connections"
    manager = CallManager([Operator("A"), Operator("B")])

    def buildProtocol(self, data):
        return CallCenterProtocol(self)

if __name__ == '__main__':
    factory = CallCenterFactory()
    reactor.listenTCP(5678, factory)
    reactor.run()