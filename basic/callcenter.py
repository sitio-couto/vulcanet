from enum import Enum
from cmd import Cmd
from collections import deque
import sys

class Operator():
    # These states are limited to the operator class
    States = Enum("state", "AVAILABLE RINGING BUSY")
    
    def __init__(self, id):
        self.id = id
        self.state = Operator.States.AVAILABLE
        self.call = None

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

    def set_state(self, state):
        self.state = Operator.States[state]
    def is_available(self):
        return self.state == Operator.States.AVAILABLE
    def is_ringing(self):
        return self.state == Operator.States.RINGING
    def is_busy(self):
        return self.state == Operator.States.BUSY

class Operators():
    def __init__(self, operators):
        self.operators = {op.id:op for op in operators}

    def ring_operators(self, call):
        # Try calling Operators, if none available, put on hold (end of queue)
        for op in self.operators.values():
            if op.ring(call) : return op
        return None
    
    def search_call(self, call):
        for op in self.operators.values():
            if op.call == call : return op
        return None

    def get(self, op_id):
        return self.operators.get(op_id, None)

class Queue():
    def __init__(self)     : self.queue = deque()
    def hold(self, call)   : self.queue.appendleft(call)
    def next(self)         : return self.queue.pop()
    def has(self, call)    : return call in self.queue
    def remove(self, call) : self.queue.remove(call)
    def not_empty(self)    : return bool(self.queue)
    def first(self, call)  : self.queue.append(call)

class CallManager():
    def __init__(self, operators):
        self.operators = Operators(operators)
        self.queue = Queue() 

    def do_call(self, call=None):
        # Check if it's a new or queue call
        if call:
            call = int(call)
            print(f"Call {call} received")
        else:    
            call = self.queue.next()
        
        # Try to contact a operator
        operator = self.operators.ring_operators(call)
        if operator:
            print(f"Call {call} ringing for operator {operator.id}")
        else:
            self.queue.hold(call)
            print(f"Call {call} waiting in queue")
            
    def do_answer(self, op_id):
        operator = self.operators.get(op_id)
        if operator.answer():
            print(f"Call {operator.call} answered by operator {op_id}")

    def do_reject(self, op_id):
        operator = self.operators.get(op_id)
        call = operator.reject()
        print(f"Call {call} rejected by operator {op_id}")
        self.queue.first(call) # Return rejected call to the front of the queue
        self.do_call()

    def do_hangup(self, call):
        call = int(call)
        # Check if call is either on queue or with an operator and end it
        if self.queue.has(call):
            self.queue.remove(call)
            print(f"Call {call} missed")
        else:
            op = self.operators.search_call(call)
            if op:
                if op.is_busy():
                    print(f"Call {call} finished and operator {op.id} available")
                elif op.is_ringing():
                    print(f"Call {call} missed")
                op.hangup()
            if self.queue.not_empty() : self.do_call()

class CmdInterface(Cmd):
    def __init__(self, manager):
        Cmd.__init__(self)
        self.manager = manager

    def do_call(self, args):
        self.manager.do_call(args)

    def do_answer(self, args):
        self.manager.do_answer(args)

    def do_reject(self, args):
        self.manager.do_reject(args)

    def do_hangup(self, args):
        self.manager.do_hangup(args)

    def do_exit(self, args):
        return True
    def do_EOF(self, args):
        return True

operators = [Operator("A"), Operator("B")]
manager = CallManager(operators)
interface = CmdInterface(manager)

if __name__ == "__main__":
    interface.cmdloop("You are connected to the call center.")