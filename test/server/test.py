#!/usr/bin/python3

# This file is part of LibLPME.

# LibLPME is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free
# Software Foundation; either version 3, or (at your option) any later
# version.

# LibLPME is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
# for more details.

# You should have received a copy of the GNU General Public License
# along with LibLPME; see the file LICENSE.md.  If not see
# <http://www.gnu.org/licenses/>.

import asyncio
import liblpme
from quart import Quart, request
from argon2 import PasswordHasher

# app init

app = Quart(__name__)
hasher = PasswordHasher()
lpme = liblpme.LPMEEndpointApi(
    app,
    api_key=hasher.hash("a token"),
    hasher=hasher,
    lifetime=90
)

# utility

async def run_event_later(ses:liblpme.Session, event:str, data:bytes):
    await asyncio.sleep(5)
    await ses.run(event, data)

# commands

@lpme.event("/test")
async def evt_test(ses:liblpme.Session):
    print(f"Got event: '{await request.get_data(False, True)}'")
    return "Success!"


@lpme.event("/longtest")
async def evt_longtest(ses:liblpme.Session):
    print(f"Running test event later for server '{ses.unique_id}'")
    asyncio.create_task(run_event_later(ses, "test", b"Success!"))
    return "OK"

# launcher

if __name__ == "__main__":
    app.run("127.0.0.1", 8080, use_reloader=False)
