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

import os
import io
import time
import pytest
import requests

# valid event

def test_event(lpme, auth):
    sample = os.urandom(64).hex()

    res = requests.post(
        f"{lpme}/test",
        sample,
        headers={
            "X-LPME-Session-Id": auth.session_id,
            "X-LPME-Session": auth.session
        }
    )

    if not res.ok:
        raise RuntimeError("Valid session was rejected")
    
    assert res.text == sample

# client-issued event

def test_event_huge(lpme, auth):
    sample = os.urandom(64).hex()

    res = requests.post(
        f"{lpme}/run",
        sample,
        headers={
            "X-LPME-Session-Id": auth.session_id,
            "X-LPME-Session": auth.session
        }
    )

    time.sleep(1)

    res = requests.post(
        f"{lpme}/liblpme/longpoll",
        sample,
        headers={
            "X-LPME-Session-Id": auth.session_id,
            "X-LPME-Session": auth.session
        }
    )

    if not res.ok:
        raise RuntimeError("Valid session was rejected")
    
    buf = io.BytesIO(res.content)

    chunks = int(res.headers.get("X-LPME-Chunk-Count"))
    for i in range(chunks):
        data = buf.read(int.from_bytes(buf.read(4), "little", signed=False))
        sep = data.find(b"\0")
        command = str(data[:sep], "utf8")
        content = str(data[sep+1:], "utf8")

        if command == "test":
            assert content == sample
            return
        
    raise RuntimeError("Server did not respond with an event")
