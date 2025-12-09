# LibLPME Server

Python library for user applications.

## Summary

**Usage:**
```py
import liblpme
```

**Classes:**
- [`LPMEEndpointApi`](#lpmeendpointapi) -- Wrapper around a Quart app
that handles the LPME API.
- [`SessionManager`](#sessionmanager) -- Manager for session auth with
an Argon2id-based API key authentication system.
- [`Session`](#session) -- Represents a session initiated by a client.

## Classes

### `LPMEEndpointApi`

Utility wrapper for the LPME API.

#### Constructor

**Arguments:**
- `app: Quart` -- The Quart app to wrap with the endpoint API.
- `base_endpoint: str` *default `/lpme`* -- The base endpoint to use
when binding the API. Auth calls use this endpoint, while events are
appended to it, e.g. an event `/example` would bind to `/lpme/example`.

**Keyword Arguments:**
- `manager: SessionManager|None` *default `None`* -- A session manager
to use for authentication and session management.
- `api_key: str|None` *default `None`* -- The hashed API key to use.
- `hasher: PasswordHasher|None` *default `None`* -- The password hasher
to use for verification.
- `lifetime: float` *default `30`* -- The lifetime of a session once it
is bumped (i.e. every time it is used.)

To construct a `LPMEEndpointApi`, one of the following argument sets
must be used:
- The `manager` is defined using an already constructed `SessionManager`
- Both `api_key` and `hasher` are defined

#### Methods

##### `LPMEEndpointApi.event()`

**Arguments:**
- `endpoint: str` -- The endpoint (relative to the base URL) to bind the
event to.

Add an event listener.

The handler for an event is identical to a standard Quart request
handler. However, the first argument passed will always be the `Session`
object of the client executing the command.

This is intended to be used as a decorator, for example:
```py
lpme = LPMEEndpointApi(...)

@lpme.event("/event/endpoint")
async def event_handler(session, ...):
    return "Response"
```

Since this is effectively a Quart handler, request and response data can
be handled as such. As such, a simple echo-message handler is as
follows:
```py
from quart import request

lpme = LPMEEndpointApi(...)

@lpme.event("/echo")
async def event_echo(session, ...):
    return await request.get_data()
```
All Quart response types are supported. Furthermore, request variables
can be used as normal, e.g. with an endpoint of `/<string>`.

##### `LPMEEndpointApi.on_session_start()`

**Arguments:**
- `callback: Callable[[Session],Awaitable[None]]` -- The callback to
bind to the event.

Add a handler for session start.

The `callback` is an async function that is called with one argument,
the session that is being opened.

Handlers for session start are run before the authentication endpoint
returns the session token, allowing server state initialization before
the client is able to send requests.

This is intended to be used as a decorator, for example:
```py
lpme = LPMEEndpointApi(...)

@lpme.on_session_start
async def start_handler(session):
    ...
```

##### `LPMEEndpointApi.on_session_end()`

**Arguments:**
- `callback: Callable[[Session],Awaitable[None]]` -- The callback to
bind to the event.

Add a handler for session end.

The `callback` is an async function that is called with one argument,
the session that is shutting down.

Handlers for session end are run in a task that is started when the
client issues a shutdown event. This means the session will be
deactivated while handlers are running, and long-running shutdown
handlers will not block the deactivation.

This is intended to be used as a decorator, for example:
```py
lpme = LPMEEndpointApi(...)

@lpme.on_session_end
async def end_handler(session):
    ...
```

### `SessionManager`

Utility to manage `Session` objects, using session IDs as a reference.

#### Constructor

**Arguments:**
- `key: str` -- The hashed key to use for verification.
- `hasher: PasswordHasher|None` *default `PasswordHasher`* -- The hasher
to use for Argon2id verification.

#### Methods

##### `SessionManager.get_session()`

**Arguments:**
- `id: int` -- The ID of the session.

**Returns:** `Session|None` -- The session with the associated ID, if
present, otherwise `None`.

Get a session, using a user-issued ID as a key.

If the session exists, it is returned, otherwise `None` is returned.

Note, this does **not** perform validation. You still need to validate
the session after it is returned -- see
[`Session.validate()`](#async-sessionvalidate) for details. This can be
done as follows:
```py
session = await SessionManager.get_session(id)
if await session.validate(token) is True:
    ...
```

##### *async* `SessionManager.start_session()`

**Arguments:**
- `lifetime: float` *default `30`* -- The lifetime for the session,
which resets to this value when the session is bumped.

**Returns:** `Session` -- The new session.

Start a session with the given lifetime.

This constructs a session (using `Session(lifetime)`), adds it to the
manager's internal dictionary, and returns it.

After this, the client-facing session details can be returned, i.e:
- The session ID, via `Session.id` -- this is the unique identifier for
the session in this currently running process
- The session token, via `await Session.get_user_token()` -- this is the
token the client uses to verify that it owns the session
- The unique server ID, via `Session.unique_id` -- this is a globally
unique identifier that references a single session

##### *async* `SessionManager.authenticate()`

**Arguments:**
- `key: str` -- The user-issued API key.
- `lifetime: float` *default `30`* -- The lifetime to use for the
session, if it is constructed.

**Returns:** `Session` -- The new session.

Validate a user-issued API key against the stored hash.

`lifetime` is used as the `lifetime` argument in `self.start_session`,
which is called if the key is valid.

**This raises an error if the key is not valid.** See the
documentation for `argon2.PasswordHasher` for details. Should a quantum
bit-flip occur, this may also raise a `RuntimeError` on fail.

This performs a complete Argon2id hash verification, so it may take a
long time to execute if your `PasswordHasher` has high security params.
As such, please be mindful when constructing the hasher and session
manager.

### `Session`

#### Constructor

**Arguments:**
- `id: int` -- The session ID to assign.
- `lifetime: float` *default 30* -- The lifetime to use when bumping the
session.

**Note:** You should almost never construct a `Session` object yourself.
This is handled by a `SessionManager`. This class is only relevant if
you are implementing an alternative manager.

#### Properties

- `id: int` -- The current local session ID. This is a reference only
unique to the currently running process, and is used to identify the
session when a client sends a request associated with it.
- `unique_id: str` -- This is a globally unique ID generated based on
cryptographically secure random values (`os.urandom`) and the current
time. As such, this can safely be used to identify any number of
sessions.

#### Methods

##### `Session.on_expire()`

**Arguments:**
- `callback: Callable[[Session],Awaitable[None]]` -- The callback to
bind to the expiration event.

Add a listener that is called when the session expires. This method is
intended to be used as a decorator.

The callback should take one argument, which is the issuing `Session`.
It should return an `Awaitable`.

Expiry callbacks are called when the expiry timer runs out. After all
calls are completed, `self.teardown()` is scheduled.

Note, if `Session.teardown()` is called instead, **expiry listeners will
not run.** To bind an event that will run even if the session is
manually torn down, see [`Session.on_teardown()`](#sessionon_teardown).

##### `Session.on_teardown()`

**Arguments:**
- `callback: Callable[[Session],Awaitable[None]]` -- The callback to
bind to the teardown event.

Add a listener that is called when the session expires.

The callback should take one argument, which is the issuing `Session`.
It should return an `Awaitable`.
 
Expiry callbacks are called **after** the session is torn down. This is
either after it expires, or when it is manually closed.

##### *async* `Session.bump()`

**Returns:** `float` -- The new expiry timestamp.

Bump the session's expiry timer by the lifetime. The session's expiry
timestamp will be set to `time.perf_counter() + lifetime`, where
`lifetime` is the value specified in the session's constructor.

##### *async* `Session.validate()`

**Arguments:**
- `cpt: str|bytes` -- The session token to validate.
- `bump: bool` *default `True`* -- If `True`, the session will be bumped
if the token is valid.

**Returns:** `bool` -- `True` if the session is valid, otherwise `False`

Validate a client-issued session token against this session.

If `bump` is true, `self.bump()` is called directly afterwards,
extending the lifetime of the session.

If `cpt` is a `str`, it is automatically converted to `bytes`. This is
because `sodium_memcmp` is used, which provides a secure alternative to
`==`.

##### *async* `Session.teardown()`

Shut down the session.

This clears the token, all expiry hooks and cancels the expiry loop task
created at construction.

Before the teardown event listeners are run, the following changes are
made to the session's internal state:
- The token is set to an empty byte string
- The expiry timestamp is set to `0`
- The lifetime is set to `-1` (hence, `Session.bump` no longer works)
- The queue of outgoing messages is shut down

However, the `id` and `unique_id` values are untouched. These are safe
to use in a teardown event.

##### *async* `Session.get_user_token()`

**Returns:** `str` -- The user token.

Get the token as a string that can be used as a raw HTTP header.

##### *async* `Session.long_poll()`

**Arguments:**
- `max_ttl: float` *default `55`* -- The maximum time to wait for a new
message to be added to the outgoing queue.

**Returns:** `list[bytes]` -- A list of outgoing messages.

Long-poll the outgoing message queue.

The `max_ttl` is used as a hard limit on how long a single poll
is allowed to take. If this limit is reached, an empty list is
returned.

The result is a single list containing every unsent outgoing message.

##### *async* `Session.run()`

**Arguments:**
- `command: str` -- The command ID to execute.
- `body: bytes` -- The data to send alongside the command.

Push a message to the client to run a command.

This uses `Session.push` internally to send a formatted message.

Note, this is a "fire-and-forget" system - there is no way for the
client to respond to a command without issuing an event. Therefore, if
a command fails or the client does not have a handler for the ID, it
will silently fail on the server.

##### *async* `Session.push()`

**Arguments:**
- `msg: bytes` -- The raw message to push into the outgoing queue.

Push a message to be sent at the next long-poll cycle.

For general use, use `Session.run`.

Messages are inserted into the outgoing queue. As such, if the session
has been shut down already, this will fail, as the queue will have also
been shut down.

Note, the client may not handle badly formatted messages properly. It is
recommended that `Session.run()` is used instead, as this ensures the
message is properly formatted.
