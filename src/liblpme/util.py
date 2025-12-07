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

from . import main
from quart import request
from typing import Callable, Awaitable

# player handling

class Player:
    def __init__(self, id:int, name:str):
        self.user_id = id
        self.name = name

    def __eq__(self, value):
        if isinstance(value, Player):
            return value.user_id == self.user_id
        return False
    
    def __hash__(self):
        return hash(self.user_id)
    
    def __repr__(self):
        return f"<Player {self.user_id}>"

    def __str__(self):
        return self.name

class Playerlist:
    __servers: dict[main.Session,set[Player]]
    __players: dict[int,str]

    def __init__(self, wraps:main.LPMEEndpointApi):
        self.__servers = {}
        self.__players = {}

        self.__on_player_join = None
        self.__on_player_leaving = None

        wraps.on_session_start(self.__evt_session_start)
        wraps.on_session_end(self.__evt_session_end)
        wraps.event("/plrlist/join")(self.__hdl_plr_join)
        wraps.event("/plrlist/left")(self.__hdl_plr_left)


    async def on_join(
        self,
        callback:Callable[[main.Session,Player],Awaitable[None]]
    ):
        """Set the join handler.

        **Only one join handler can exist for a player list. Calling
        this again will override any existing handler.**

        The join handler is called after a player has been added to a
        server's playerlist. The returned value is used directly as the
        Quart endpoint response, so it must adhere to request handler
        rules.

        Although this needs to return a valid Quart response, **handlers
        are not always called in a request context.** Do not rely on
        request context features in a handler.
        """

        self.__on_player_join = callback

    async def on_leaving(
        self,
        callback:Callable[[main.Session,Player],Awaitable[None]]
    ):
        """Set the leaving handler.

        **Only one leaving handler can exist for a player list. Calling
        this again will override any existing handler.**

        The leaving handler is called after a player has been added to a
        server's playerlist. The returned value is used directly as the
        Quart endpoint response, so it must adhere to request handler
        rules.

        Although this needs to return a valid Quart response, **handlers
        are not always called in a request context.** Do not rely on
        request context features in a handler.
        """

        self.__on_player_leaving = callback


    def get_player_server_uid(self, id:int) -> str|None:
        """Get the unique ID of the server a player is in, or `None` if
        they aren't in any.

        The `id` argument is the user ID of the player.

        This method uses the internal player index to quickly return the
        correct server.
        """

        return self.__players.get(id)
    
    def get_player_server(self, plr:Player|int) -> main.Session:
        """Get the server a player is currently in. Throws `KeyError` if
        the player is not in a server.

        `plr` can be either a `Player` instance or a user ID.

        The returned object is the server session the player is in.
        """

        if isinstance(plr, Player):
            plr = plr.user_id

        uid = self.get_player_server_uid(plr)

        if uid is None:
            raise KeyError(str(plr))
        return self.__servers[uid]

    def is_player_active(self, plr:Player|int) -> bool:
        """Check if a player is in a server. Return `True` if they are.

        `plr` can be either a `Player` instance or a user ID.
        """

        if isinstance(plr, Player):
            plr = plr.user_id

        return self.get_player_server_uid(plr) is not None


    async def __evt_session_start(self, ses:main.Session):
        self.__servers[ses.unique_id] = set()

    async def __evt_session_end(self, ses:main.Session):
        plrs = self.__servers[ses.unique_id]

        for i in plrs:
            await self.__evt_plr_left(ses, i)

        del self.__servers[ses.unique_id]

    async def __evt_plr_join(self, ses:main.Session, plr:Player):
        self.__servers[ses.unique_id].add(plr)
        self.__players[plr.user_id] = ses.unique_id

        if self.__on_player_join:
            return await self.__on_player_join()
        return ""
    
    async def __evt_plr_left(self, ses:main.Session, plr:Player):
        self.__servers[ses.unique_id].remove(plr)
        del self.__players[plr.user_id]

        if self.__on_player_leaving:
            return await self.__on_player_leaving(plr)
        return ""
    

    async def __hdl_plr_join(self, ses:main.Session):
        payload = await request.get_json(True, cache=False)
        plr = Player(payload["id"], payload["name"])

        return await self.__evt_plr_join(ses, plr)
    
    async def __hdl_plr_left(self, ses:main.Session):
        payload = await request.get_json(True, cache=False)
        plr = Player(payload["id"], payload["name"])

        return await self.__evt_plr_left(ses, plr)
