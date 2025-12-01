import os
import time
import typing
import asyncio
from nacl import bindings
from argon2 import PasswordHasher
from hashlib import sha3_256, sha3_512

# general classes

class Session:
    """Class representing a single active session.

    When a session is constructed, a lifetime is passed. This denotes
    how long the session is allowed to live, and is used when
    `Session.bump()` is called.
    """

    def __init__(self, lifetime:float=30):
        """Session constructor.

        The `lifetime` argument is used as a basis for:
        - The initial time-to-live of the session
        - The lifetime used when bumping the session
        """

        self.__token = os.urandom(64)
        self.__token_str = bytes(self.__token.hex(), "utf8")
        self.__expiry = time.perf_counter() + lifetime
        self.__on_expire = []
        self.__expire_event = asyncio.Event()
        self.__lifetime = lifetime
        self.__expiry_task = asyncio.create_task(self.expiry_loop())

    def on_expire(self, callback:typing.Callable[[typing.Self],typing.Awaitable[None]]):
        """Add a listener that is called when the session expires.
        
        The callback should take one argument, which is the issuing `Session`.
        It should return an `Awaitable`.
        
        Expiry callbacks are called when the expiry timer runs out.
        After all calls are completed, `self.teardown()` is scheduled.
        """

        self.__on_expire.append(callback)
        return callback
    
    async def expiry_loop(self):
        """Run the expiry loop, calling all expiry callbacks when the
        timer runs out.

        This should not be called; it is started as a task during
        session construction. If you're a highly trained professional,
        however, feel free to use this, but prepare for unforeseen
        consequences.
        """

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
        """Bump the session's expiry timer by the lifetime.
        """

        self.__expiry = time.time() + self.__lifetime
        self.__expire_event.set()
        return self.__expiry
    
    async def validate(self, cpt:str|bytes, bump:bool=True) -> bool:
        """Validate a client-issued session token against this session.

        If `bump` is true, `self.bump()` is called directly afterwards,
        extending the lifetime of the session.

        If `cpt` is a `str`, it is automatically converted to `bytes`.
        This is because `sodium_memcmp` is used, which provides
        a secure alternative to `==`.
        """

        if isinstance(cpt, str):
            cpt = bytes(cpt, "utf8")

        res = await asyncio.to_thread(bindings.sodium_memcmp, cpt, self.__token_str)
        if time.perf_counter() >= self.__expiry:
            return False
        
        if res is True and bump is True:
            await self.bump()

        return res

    async def teardown(self):
        """Shut down the session.

        This clears the token, all expiry hooks and cancels the
        expiry loop task created at construction.
        """

        self.__on_expire.clear()
        self.__expiry_task.cancel()
        self.__token = b""
        self.__token_str = b""
        self.__expiry = 0
        self.__lifetime = -1

    async def get_user_token(self) -> str:
        """Get the token as a string that can be used as a raw
        HTTP header.
        """

        return str(self.__token_str, "utf8")

class SessionManager:
    """Utility to manage `Session` objects, using tokens as
    a reference.
    """

    def __init__(self, key:str, hasher:PasswordHasher|None=None):
        """Session manager constructor.

        The `key` must be an Argon2id-encoded password hash,
        encoded using the provided hasher.

        If no hasher is provided, the default Argon2 arguments
        are used.
        """

        if hasher is None:
            hasher = PasswordHasher()

        self.__sessions = {}
        self.__key = key
        self.__hasher = hasher

    def get_session(self, token:str) -> Session|None:
        """Get a session, using a user-issued token as a key.

        If the session exists, it is returned, otherwise `None`
        is returned.

        Note, this does **not** perform validation. You still
        need to validate the session after it is returned.
        """

        if token in self.__sessions:
            return self.__sessions[token]
        return None
    
    async def start_session(self, lifetime:float=30) -> Session:
        """Start a session with the given lifetime.

        This constructs a session (using `Session(lifetime)`),
        adds it to the manager's internal dictionary, and
        returns it.
        """

        ses = Session(lifetime)
        self.__sessions[await ses.get_user_token()] = ses
        return ses

    async def authenticate(self, key:str, lifetime:float=30) -> Session:
        """Validate a user-issued API key against the stored
        hash.

        `lifetime` is used as the `lifetime` argument in
        `self.start_session`, which is called if the key is
        valid.

        This raises an error if the key is not valid. See the
        documentation for `argon2.PasswordHasher` for details.
        Should a quantum bit-flip occur, this may also raise a
        `RuntimeError` on fail.
        """

        if await asyncio.to_thread(self.__hasher.verify, self.__key, key) is True:
            return await self.start_session(lifetime)
        
        # literally impossible
        raise RuntimeError("Verify failed")
