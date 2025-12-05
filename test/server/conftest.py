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
import sys
import time
import pytest
import signal
import requests
import subprocess

# main fixture

@pytest.fixture(scope="session", autouse=True)
def lpme():
    proc = subprocess.Popen([
        sys.executable,
        os.path.dirname(os.path.abspath(__file__)) + "/server.py"
    ])
    time.sleep(1)

    for i in range(9):
        try:
            requests.get("http://localhost:8080")
            break
        except requests.ConnectionError:
            time.sleep(1)

    yield "http://localhost:8080/lpme"

    proc.send_signal(signal.SIGINT)
    
    try:
        proc.wait(3)
    except subprocess.TimeoutExpired:
        proc.kill()
