import logging
import time
import asyncio
import socket
from threading import Thread
from datetime import datetime
from asyncua import ua, uamethod, Server

#######################################
# INSTALL PACKAGES : 
# pip install asyncua

class DoorAccess:

    def __init__(self, schleuse, door_in, door_out, idx, tick_wait = 2):
        self._door_in = door_in
        self._door_out = door_out
        self._schleuse = schleuse
        self._idx = idx

        self._schleuse_time = None
        self._schleuse_machine = None
        self._schleuse_error = None
        self._schleuse_busy = None

        self._move_in = False
        self._move_out = False
        self._state = 0

        self._tick_count = 0
        self._tick_wait = tick_wait

    async def initialize(self):
        self._schleuse_time = await self._schleuse.get_child(["{}:time".format(self._idx)]) 
        self._schleuse_machine = await self._schleuse.get_child(["{}:machine".format(self._idx)])
        self._schleuse_busy = await self._schleuse.get_child(["{}:busy".format(self._idx)])
        self._schleuse_state = await self._schleuse.get_child(["{}:state".format(self._idx)])

        await self._schleuse_machine.set_value(str(socket.gethostname()))
        await self._schleuse.add_method(self._idx, "AccessIn", self.access_in)
        await self._schleuse.add_method(self._idx, "AccessOut", self.access_out)


    @property
    async def busy(self):
        return await self._schleuse_busy.get_value()


    @uamethod
    async def access_in(self, parent):
        if not await self.busy:
            self._tick_count = 0
            self._move_in = True
            self._move_out = False
            await self._schleuse_busy.set_value(True)
            await self._door_in.open_door()
            self._state = 0

    @uamethod
    async def access_out(self, parent):
        if not await self.busy:
            self._tick_count = 0
            self._move_in = False
            self._move_out = True
            await self._schleuse_busy.set_value(True)
            await self._door_out.open_door()
            self._state = 0

    async def loop(self, tick):
        await self._door_in.loop(tick)
        await self._door_out.loop(tick)

        await self._schleuse_time.set_value(str(datetime.now()))

        if self._move_in:

            if(self._state == 0):
                if not await self._door_in.busy:
                    self._tick_count += 1
                    if self._tick_count > self._tick_wait:
                        self._tick_count = 0
                        self._state = 1

            elif(self._state == 1):
                await self._door_in.close_door()
                self._state = 2

            elif(self._state == 2):
                if not await self._door_in.busy:
                    await self._door_out.open_door()
                    self._state = 3

            elif(self._state == 3):
                if not await self._door_out.busy:
                    self._tick_count += 1
                    if self._tick_count > self._tick_wait:
                        self._tick_count = 0
                        await self._door_out.close_door()
                        self._state = 4
                
            elif(self._state == 4):
                if not await self._door_out.busy:
                    await self._schleuse_busy.set_value(False)
                    self._move_in = False
                    self._state = 0
            
        elif self._move_out:

            if(self._state == 0):
                if not await self._door_out.busy:
                    self._tick_count += 1
                    if self._tick_count > self._tick_wait:
                        self._tick_count = 0
                        self._state = 1

            elif(self._state == 1):
                await self._door_out.close_door()
                self._state = 2

            elif(self._state == 2):
                if not await self._door_out.busy:
                    await self._door_in.open_door()
                    self._state = 3

            elif(self._state == 3):
                if not await self._door_in.busy:
                    self._tick_count += 1
                    if self._tick_count > self._tick_wait:
                        await self._door_in.close_door()
                        self._tick_count = 0
                        self._state = 4
                
            elif(self._state == 4):
                if not await self._door_in.busy:
                    await self._schleuse_busy.set_value(False)
                    self._move_out = False
                    self._state = 0

        await self._schleuse_state.set_value(self._state)

class Door:

    def __init__(self, door, idx, tick_move = 2):
        self._idx = idx
        self._door = door
        self._action_open = False
        self._action_close = False
        self._tick_move = tick_move
        self._tick_count = 0
        self._door_open = None
        self._door_closed = None
        self._door_busy = None

    async def initialize(self):
        self._door_open = await self._door.get_child(["{}:open".format(self._idx)]) 
        self._door_closed = await self._door.get_child(["{}:closed".format(self._idx)])
        self._door_busy = await self._door.get_child(["{}:busy".format(self._idx)])
        await self.close_door()

    async def open_door(self):
        await self._door_busy.set_value(True)
        self._action_open = True
        self._action_close = False

    async def close_door(self):
        await self._door_busy.set_value(True)
        self._action_close = True
        self._action_open = False

    @property
    async def open(self):
        return await self._door_open.get_value()

    @property
    async def close(self):
        return await self._door_closed.get_value()

    @property
    async def busy(self):
        return await self._door_busy.get_value()

    async def loop(self, tick):

        if self._action_open:
            self._tick_count += 1
            await self._door_closed.set_value(False)

            if self._tick_count >= self._tick_move:
                self._action_open = False
                await self._door_busy.set_value(False)
                await self._door_open.set_value(True)
                self._tick_count = 0

        elif self._action_close:
            self._tick_count += 1
            await self._door_open.set_value(False)

            if self._tick_count >= self._tick_move:
                self._action_close = False
                await self._door_busy.set_value(False)
                await self._door_closed.set_value(True)
                self._tick_count = 0


class CyclicValueUpdater(Thread):
    """
    This class serves as a simple standalone thread
    to update defined values based on the defined interval.
    """
    def __init__(self, interval):
        """
        Parameters:
        interval (int): interval in seconds [s]
        """
        Thread.__init__(self)
        super().setDaemon(True)
        self.interval = interval
        self.stopthread = False
        self.varlist = [1]
        
    def stop(self):
        self.stopthread = True

    def insert_variable(self, var, getterfunc):
        self.varlist.append((var, getterfunc))

    def run(self):
        while not self.stopthread:
            for e in self.varlist:
                e[0].set_value(e[1]())

            time.sleep(self.interval)

async def main():
    # optional: setup logging
    # logging.basicConfig(level=logging.ERROR)

    # now setup our server
    server = Server()
    await server.init()

    ENDPOINT = "opc.tcp://localhost:5050"
    SERVER_NAME = "ZugangskontrolleUA"

    server.set_endpoint(ENDPOINT)
    server.set_server_name(SERVER_NAME)
    
    # set all possible endpoint policies for clients to connect through
    server.set_security_policy([
                ua.SecurityPolicyType.NoSecurity,
                ua.SecurityPolicyType.Basic256Sha256_SignAndEncrypt,
                ua.SecurityPolicyType.Basic256Sha256_Sign])

    # setup our own namespace
    uri = "http://veri.fhnw/opcua"
    idx = await server.register_namespace(uri)

    # create a new node type we can instantiate in our address space
    schleuse_type = await server.nodes.base_object_type.add_object_type(idx, "SchleusenType")
    await (await schleuse_type.add_variable(idx, "time", "")).set_modelling_rule(True)
    await (await schleuse_type.add_variable(idx, "state", 0)).set_modelling_rule(True)
    await (await schleuse_type.add_variable(idx, "machine", "no_type")).set_modelling_rule(True)
    await (await schleuse_type.add_variable(idx, "busy", False)).set_modelling_rule(True)
    
    door_Type = await server.nodes.base_object_type.add_object_type(idx, "DoorType")
    await (await door_Type.add_variable(idx, "closed", False)).set_modelling_rule(True)
    await (await door_Type.add_variable(idx, "open", False)).set_modelling_rule(True)
    await (await door_Type.add_variable(idx, "busy", False)).set_modelling_rule(True)

    # instanciate one instance of our system data
    schleuse_opcua = await server.nodes.objects.add_object(idx, "Schleuse", schleuse_type)
    door_in_opcua = await server.nodes.objects.add_object(idx, "DoorIn", door_Type)
    door_out_opcua = await server.nodes.objects.add_object(idx, "DoorOut", door_Type)

    door_in = Door(door_in_opcua, 2)
    await door_in.initialize()
    door_out = Door(door_out_opcua, 2)
    await door_out.initialize()
    schleuse = DoorAccess(schleuse_opcua, door_in, door_out, idx)
    await schleuse.initialize()
    
    print("Server running on ", ENDPOINT)
    async with server:
        while True:
            await schleuse.loop(1)
            await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())

