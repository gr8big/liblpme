#!/usr/bin/python3

# This file is part of LibLPME.

# LibLPME is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation; either version 3, or (at your option) any
# later version.

# LibLPME is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
# for more details.

# You should have received a copy of the GNU General Public License
# along with LibLPME; see the file LICENSE.md.  If not see
# <http://www.gnu.org/licenses/>.

import sys
import liblpme
from quart import Quart, request
from argon2 import PasswordHasher

# app init

app = Quart(__name__)
hasher = PasswordHasher()
lpme = liblpme.LPMEEndpointApi(
    app,
    api_key=hasher.hash("test"),
    hasher=hasher,
    lifetime=90
)

# commands

@lpme.event("/test")
async def evt_test(ses:liblpme.Session):
    return await request.get_data(False)


@lpme.event("/run")
async def evt_run(ses:liblpme.Session):
    await ses.run("test", await request.get_data(False))
    return "ok"

# root

@app.route("/")
async def home():
    return "ok"

# launcher

if __name__ == "__main__":
    app.run("127.0.0.1", 8080, use_reloader=False)
