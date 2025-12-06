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

import pytest
import requests

# valid use of a session

def test_session(lpme, auth):
    res = requests.post(
        f"{lpme}/test",
        "",
        headers={
            "X-LPME-Session-Id": auth.session_id,
            "X-LPME-Session": auth.session
        }
    )

    if not res.ok:
        raise RuntimeError("Valid session was rejected")

# no session

def test_session_missing(lpme, auth):
    res = requests.post(
        f"{lpme}/test",
        ""
    )

    if res.status_code in range(500, 599):
        raise ValueError("Server error for bad session")

    if res.ok:
        raise RuntimeError("Invalid session was accepted")

# non-existent session

def test_session_invalid(lpme, auth):
    res = requests.post(
        f"{lpme}/test",
        "",
        headers={
            "X-LPME-Session-Id": "485",
            "X-LPME-Session": "token"
        }
    )

    if res.status_code in range(500, 599):
        raise ValueError("Server error for bad session")

    if res.ok:
        raise RuntimeError("Invalid session was accepted")

# existing session, bad token

def test_session_badtoken(lpme, auth):
    res = requests.post(
        f"{lpme}/test",
        "",
        headers={
            "X-LPME-Session-Id": auth.session_id,
            "X-LPME-Session": "token"
        }
    )

    if res.status_code in range(500, 599):
        raise ValueError("Server error for bad session")

    if res.ok:
        raise RuntimeError("Invalid session was accepted")

# bad id, valid token

def test_session_badid_a(lpme, auth):
    res = requests.post(
        f"{lpme}/test",
        "",
        headers={
            "X-LPME-Session-Id": "485",
            "X-LPME-Session": auth.session
        }
    )

    if res.status_code in range(500, 599):
        raise ValueError("Server error for bad session")

    if res.ok:
        raise RuntimeError("Invalid session was accepted")

def test_session_badid_b(lpme, auth):
    res = requests.post(
        f"{lpme}/test",
        "",
        headers={
            "X-LPME-Session-Id": "abc",
            "X-LPME-Session": auth.session
        }
    )

    if res.status_code in range(500, 599):
        raise ValueError("Server error for bad session")

    if res.ok:
        raise RuntimeError("Invalid session was accepted")

# huge data

def test_session_hugeid(lpme, auth):
    res = requests.post(
        f"{lpme}/test",
        "",
        headers={
            "X-LPME-Session-Id": auth.session_id * 536870912,
            "X-LPME-Session": auth.session
        }
    )

    if res.status_code in range(500, 599):
        raise ValueError("Server error for bad session")

    if res.ok:
        raise RuntimeError("Invalid session was accepted")

def test_session_hugeses(lpme, auth):
    res = requests.post(
        f"{lpme}/test",
        "",
        headers={
            "X-LPME-Session-Id": auth.session_id,
            "X-LPME-Session": auth.session * 4194304
        }
    )

    if res.status_code in range(500, 599):
        raise ValueError("Server error for bad session")

    if res.ok:
        raise RuntimeError("Invalid session was accepted")

# malformed headers

def test_session_malformedid(lpme, auth):
    with requests.session() as ses:
        req = requests.Request(
            "POST",
            lpme
        )
        prep = req.prepare()
        prep.headers["X-LPME-Session-Id"] = "\x00"
        prep.headers["X-LPME-Session"] = auth.session
        res = ses.send(prep)

        if res.status_code in range(500, 599):
            raise ValueError("Server error returned")

        if res.ok:
            raise ValueError("Malformed session was accepted")

def test_session_malformedses(lpme, auth):
    with requests.session() as ses:
        req = requests.Request(
            "POST",
            lpme
        )
        prep = req.prepare()
        prep.headers["X-LPME-Session-Id"] = auth.session_id
        prep.headers["X-LPME-Session"] = auth.session + "\x00"
        res = ses.send(prep)

        if res.status_code in range(500, 599):
            raise ValueError("Server error returned")

        if res.ok:
            raise ValueError("Malformed session was accepted")
