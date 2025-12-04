# LibLPME

A utility to connect Roblox game servers with Python applications.

This project is licensed under the GNU GPL-3.0 -- see
[LICENSE.md](./LICENSE.md).

## Introduction

LibLPME is based on two components: the server (the Python app) and the
client (the Roblox game server). The client is able to run commands on
the server, which is handled as a standard HTTP request, and the server
is able to run commands on the client via a long-poll-based messaging
engine.

Each Roblox game server is also given a unique ID. This can be used in
logging to trace requests back to a specific server, as well as to
identify one server specifically.

## Installation

To install the server package from source, run in the repository root:  
```bash
pip install -e .
```

This installs LibLPME as an editable package.

To install the client package, add the contents of
[client](./src/client/) to a Roblox game (ideally in `ServerStorage`)
and import LibLPME with:
```lua
local liblpme = require(game.ServerStorage.path.to.liblpme)
```
Ensure the `util` and `liblpme` modules are in the same folder.

## Usage

To wrap a Quart app with a LPME wrapper:  
```py
import liblpme
from quart import Quart

app = Quart(__name__)
lpme = liblpme.LPMEEndpointApi(
    app,
    api_key="my hashed api key",
    lifetime = 60
)
```
The `api_key` keyword argument should be the previously stored Argon2id
hash of your actual key.

Then, to connect from the client:
```lua
local lpme = liblpme.LPME("http://hostname/lpme")

lpme.connect("my api key")
```
The `lpme.connect()` method returns a boolean, where `true` denotes a
successful connection. Games relying on an LPME connection should use
this to detect when a connection fails.
