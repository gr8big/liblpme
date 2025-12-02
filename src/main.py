import os
import time
import typing
import asyncio
from nacl import bindings
from hashlib import sha3_256
from argon2 import exceptions
from argon2 import PasswordHasher
from quart import Quart, Response, request, make_response

# utility

async def respond_stream(f:asyncio.StreamReader):
    while True:
        chunk = await f.read()
        if chunk:
            yield chunk
        break

async def chunk_writer(chunks:list[bytes], to:asyncio.StreamReader):
    for i in chunks:
        to.feed_data(to)
    to.feed_eof()

# general classes

class Session:
    """Class representing a single active session.

    When a session is constructed, a lifetime is passed. This denotes
    how long the session is allowed to live, and is used when
    `Session.bump()` is called.
    """

    id: int
    unique_id: str

    __token: bytes
    __token_str: bytes
    __expiry: float
    __expire_event: asyncio.Event
    __lifetime: float
    __expiry_task: asyncio.Task
    __on_expire: list[typing.Callable[[typing.Self],typing.Awaitable[None]]]
    __on_teardown: list[typing.Callable[[typing.Self],typing.Awaitable[None]]]
    
    __outgoing: asyncio.Queue[bytes]

    def __init__(self, id:int, lifetime:float=30):
        """Session constructor.

        The `lifetime` argument is used as a basis for:
        - The initial time-to-live of the session
        - The lifetime used when bumping the session
        """

        self.id = id
        self.unique_id = sha3_256(
            os.urandom(16)
            + time.perf_counter_ns().to_bytes(16, "little", signed=True)
        ).hexdigest()

        self.__token = os.urandom(64)
        self.__token_str = bytes(self.__token.hex(), "utf8")
        self.__expiry = time.perf_counter() + lifetime
        self.__expire_event = asyncio.Event()
        self.__lifetime = lifetime
        self.__expiry_task = asyncio.create_task(self.expiry_loop())
        self.__on_expire = []
        self.__on_teardown = []
        self.__outgoing = asyncio.Queue()

    def on_expire(self, callback:typing.Callable[[typing.Self],typing.Awaitable[None]]):
        """Add a listener that is called when the session expires.
        
        The callback should take one argument, which is the issuing `Session`.
        It should return an `Awaitable`.
        
        Expiry callbacks are called when the expiry timer runs out.
        After all calls are completed, `self.teardown()` is scheduled.
        """

        self.__on_expire.append(callback)
        return callback
    
    def on_teardown(self, callback:typing.Callable[[typing.Self],typing.Awaitable[None]]):
        """Add a listener that is called when the session expires.
        
        The callback should take one argument, which is the issuing `Session`.
        It should return an `Awaitable`.
        
        Expiry callbacks are called **after** the session is torn down.
        This is either after it expires, or when it is manually
        closed.
        """

        self.__on_teardown.append(callback)
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
        self.__outgoing.shutdown(True)

        for i in self.__on_teardown:
            await i(self)

    async def get_user_token(self) -> str:
        """Get the token as a string that can be used as a raw
        HTTP header.
        """

        return str(self.__token_str, "utf8")


    async def long_poll(self, max_ttl:float=55.0) -> list[bytes]:
        """Long-poll the outgoing message queue.
        
        The `max_ttl` is used as a hard limit on how long a
        single poll is allowed to take. If this limit is
        reached, an empty list is returned.
        """

        res = []
        try:
            async with asyncio.timeout(max_ttl):
                res.append(await self.__outgoing.get())
            
            while not self.__outgoing.empty():
                res.append(self.__outgoing.get_nowait())
        except asyncio.TimeoutError:
            pass

        return res

    async def push(self, message:bytes):
        """Push a message to be sent at the next long-poll
        cycle.

        Messages are inserted into the outgoing queue. As
        such, if the session has been shut down already, this
        will fail, as the queue will have also been shut
        down.
        """

        self.__outgoing.put_nowait(message)

class SessionManager:
    """Utility to manage `Session` objects, using session IDs as
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
        self.__id_prog = 0
        self.__hasher = hasher

    def get_session(self, id:int) -> Session|None:
        """Get a session, using a user-issued ID as a key.

        If the session exists, it is returned, otherwise `None`
        is returned.

        Note, this does **not** perform validation. You still
        need to validate the session after it is returned.
        """

        if id in self.__sessions:
            return self.__sessions[id]
        return None
    
    async def start_session(self, lifetime:float=30) -> Session:
        """Start a session with the given lifetime.

        This constructs a session (using `Session(lifetime)`),
        adds it to the manager's internal dictionary, and
        returns it.
        """

        id = self.__id_prog
        self.__id_prog += 1

        ses = Session(id, lifetime)
        self.__sessions[id] = ses
        ses.on_teardown(self.__teardown)
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

    async def __teardown(self, ses:Session):
        del self.__sessions[ses.id]

# main class

class LPMEEndpointApi:
    """Utility wrapper for the LPME API.
    """

    def __init__(
            self,
            app:Quart,
            base_endpoint:str="/lpme",
            *,
            manager:SessionManager|None=None,
            api_key:str|None=None,
            hasher:PasswordHasher|None=None,
            lifetime:float=30
    ):
        """Construct an `LPMEEndpointApi` around an existing
        app.
        """

        if manager is None:
            if api_key is None:
                raise ValueError("API key must be set when manager is not")
            
            manager = SessionManager(api_key, hasher)

        self.__app = app
        self.__base_endpoint = base_endpoint.rstrip("/")
        self.__manager = manager
        self.__lifetime = lifetime

        app.route(self.__base_endpoint, methods=["POST"])(self.__hndl_auth)
        self.event("/liblpme/shutdown")(self.__hndl_shutdown)
        self.event("/liblpme/longpoll")(self.__hndl_longpoll)

    def event(self, endpoint:str):
        """Add an event listener.

        The handler for an event is identical to a standard
        Quart request handler. However, the first argument
        passed will always be the `Session` object of the
        client executing the command.
        """

        if not endpoint.startswith("/"):
            raise ValueError("Endpoint must start with a trailing '/'")
        
        def wrapper(callback:typing.Callable[...,typing.Awaitable]):
            async def handler(*args, **kwargs):
                ses_tk = request.headers.get("X-LPME-Session", "")
                ses_id = request.headers.get("X-LPME-Session-Id", -1, int)
                session = self.__manager.get_session(ses_id)

                if session is None:
                    return "Unauthorized", 401
                
                if await session.validate(ses_tk) is True:
                    res = await callback(session, *args, **kwargs)

                    if not isinstance(res, Response):
                        if isinstance(res, tuple):
                            res = make_response(*res)
                        else:
                            res = make_response(res)

                    res.headers.set("X-LPME-Server-Id", session.unique_id)
                    return res
                else:
                    return "Forbidden", 403

            handler.__name__ = f"handler_{callback.__name__}"
            self.__app.route(
                f"{self.__base_endpoint}{endpoint}",
                methods=["POST"]
            )(handler)

            return handler
        return wrapper


    # base handlers

    async def __hndl_auth(self):
        api_key = request.headers.get("X-LPME-Token", "")

        try:
            ses = await self.__manager.authenticate(api_key, self.__lifetime)

            response = Response("", 200, mimetype="text/plain")
            response.headers.set("X-LPME-Session-Id", str(ses.id))
            response.headers.set("X-LPME-Session", ses)
            response.headers.set("X-LPME-Server-Id", ses.unique_id)
            return response

        except exceptions.Argon2Error:
            return "Unauthorized", 401

    async def __hndl_shutdown(self, ses:Session):
        await ses.teardown()

    async def __hndl_longpoll(self, ses:Session):
        f = asyncio.StreamReader()
        chunks = await ses.long_poll()

        res = Response(respond_stream(f), 200, mimetype="application/x-lpme-chunks")
        res.headers.set("X-LPME-Chunk-Count", str(len(chunks)))
        return res
