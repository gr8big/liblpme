# LibLPME Client

Luau library using Roblox APIs to enable communication with the Python
back-end.

## Summary

**Usage:**
```lua
liblpme = require(path.to.liblpme)
```

**Classes:**
- [`LPME`](#lpme) -- Handler for the LPME API connection.
- [`LPMEServerEventResponse`](#lpmeservereventresponse) -- Small wrapper
containing additional details about an event response.

**Submodules:**
- [`util`](./util.md) -- Utility package containing additional resources
used by the main module.

## Classes

### `LPME`

An API handler exposing methods for interfacing with the LPME API.

#### Constructor

**Arguments:**
- `base_url: string` -- The base URL, e.g. `https://example.com/lpme`.
The path must match the base URL on the server.

#### Methods

##### `LPME:connect()`

**Arguments:**
- `api_key: string` -- The API key that matches that expected by the
server.

Initialize the session and connect to the API.

This will set the internal session token and ID values, as well as the
unique server ID. After this, events can be issued and messages can be
received.

This method also starts the long-poll task on success.

##### `LPME:disconnect()`

Shut down the connection, cancelling the long-poll task.

##### `LPME:run_event()`

**Arguments:**
- `event: string` -- The ID of the event to run.
- `data: string` -- Data to attach to the request body.

**Returns:** `LPMEServerEventResponse` -- The response sent by the
server.

Issue an event to the server.

Internally, this calls the API bound for the event ID. Therefore, this
returns an HTTP status in the response.

##### `LPME:command()`

**Arguments:**
- `command_id: string` -- The command ID to bind.
- `callback: (data: string) -> nil` -- The command handler.

Bind a command handler to an ID.

After this has been called, the server is able to issue events for the
`command_id`. The body sent will be passed to the handler as the `data`
argument.

### `LPMEServerEventResponse`

Container for an LPME event response.

#### Constructor

Not constructable.

#### Properties

- `body: string` -- The raw content returend by the server.
- `headers: Headers` -- Headers of the response.
- `status: number` -- The HTTP status code.
- `status_msg: string` -- The status message.
- `ok: boolean` -- Boolean denoting success, where `true` means the
request was completed without issue.

#### Methods

##### `LPMEServerEventResponse:json()`

**Returns:** `any` -- The response body as parsed JSON.

Parse the request body as JSON. Throws an error if it is invalid.
