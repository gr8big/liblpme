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

# test of proper authentication

def test_auth(auth):
    if not auth:
        raise RuntimeError("Did not authenticate")

# test of an invalid key

def test_auth_bad(lpme):
    res = requests.post(
        lpme,
        headers={
            "X-LPME-Token": "invalid"
        }
    )

    if res.ok:
        raise ValueError("Bad auth request was accepted")
    
    if res.headers.get("X-LPME-Session", ""):
        raise ValueError("Session was returned on failed request")

# test of a missing key

def test_auth_missing(lpme):
    res = requests.post(
        lpme
    )

    if res.ok:
        raise ValueError("Bad auth request was accepted")
    
    if res.headers.get("X-LPME-Session", ""):
        raise ValueError("Session was returned on failed request")

# tests for malformed header content

def test_auth_malformed_a(lpme):
    with requests.session() as ses:
        req = requests.Request(
            "POST",
            lpme
        )
        prep = req.prepare()
        prep.headers["X-LPME-Token"] = "\x00"
        res = ses.send(prep)

        if res.status_code in range(500, 599):
            raise ValueError("Server error returned")

        if res.ok:
            raise ValueError("Malformed auth request was accepted")
        
        if res.headers.get("X-LPME-Session", ""):
            raise ValueError("Session was returned on failed request")

def test_auth_malformed_b(lpme):
    with requests.session() as ses:
        req = requests.Request(
            "POST",
            lpme
        )
        prep = req.prepare()
        prep.headers["X-LPME-Token\x00"] = "test"
        res = ses.send(prep)

        if res.status_code in range(500, 599):
            raise ValueError("Server error returned")

        if res.ok:
            raise ValueError("Malformed auth request was accepted")
        
        if res.headers.get("X-LPME-Session", ""):
            raise ValueError("Session was returned on failed request")
