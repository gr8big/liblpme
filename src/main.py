import os
import time
import typing
import asyncio
from nacl import bindings
from argon2 import PasswordHasher
from hashlib import sha3_256, sha3_512

# general classes

class Session:
    def __init__(self, lifetime:float=30):
        self.__token = os.urandom(64)
        self.__token_str = bytes(self.__token.hex(), "utf8")
        self.__expiry = time.perf_counter() + lifetime
        self.__on_expire = []
        self.__expire_event = asyncio.Event()
        self.__lifetime = lifetime
        self.__expiry_task = asyncio.create_task(self.expiry_loop())

    def on_expire(self, callback:typing.Callable[[typing.Self],typing.Awaitable[None]]):
        self.__on_expire.append(callback)
        return callback
    
    async def expiry_loop(self):
        while True:
            try:
                await asyncio.wait_for(self.__expire_event.wait(), self.__lifetime)
                self.__expire_event.clear()
            except asyncio.TimeoutError:
                break

        self.__expiry = 0
        for i in self.__on_expire:
            await i(self)

        asyncio.ensure_future(self.teardown(), asyncio.get_running_loop())

    async def bump(self) -> float:
        self.__expiry = time.time() + self.__lifetime
        self.__expire_event.set()
        return self.__expiry
    
    async def validate(self, cpt:str|bytes) -> bool:
        if isinstance(cpt, str):
            cpt = bytes(cpt, "utf8")

        res = await asyncio.to_thread(bindings.sodium_memcmp, cpt, self.__token_str)
        if time.perf_counter() >= self.__expiry:
            return False
        return res

    async def teardown(self):
        self.__on_expire.clear()
        self.__expiry_task.cancel()
        self.__token = b""
        self.__token_str = b""
        self.__expiry = 0
        self.__lifetime = -1

    async def get_user_token(self) -> str:
        return str(self.__token_str, "utf8")

class SessionManager:
    def __init__(self, key:str, hasher:PasswordHasher|None=None):
        if hasher is None:
            hasher = PasswordHasher()

        self.__sessions = {}
        self.__key = key
        self.__hasher = hasher

    def get_session(self, token:str) -> Session|None:
        if token in self.__sessions:
            return self.__sessions[token]
        return None
    
    async def start_session(self, lifetime:float=30) -> Session:
        ses = Session(lifetime)
        self.__sessions[await ses.get_user_token] = ses
        return ses

    async def authenticate(self, key:str, lifetime:float=30) -> Session:
        if await asyncio.to_thread(self.__hasher.verify, self.__key, key) is True:
            return await self.start_session(lifetime)
        
        # literally impossible
        raise RuntimeError("Verify failed")
