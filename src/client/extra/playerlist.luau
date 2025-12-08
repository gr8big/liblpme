--!nocheck

-- This file is part of LibLPME.

-- LibLPME is free software; you can redistribute it and/or modify it
-- under the terms of the GNU General Public License as published by the
-- Free Software Foundation; either version 3, or (at your option) any
-- later version.

-- LibLPME is distributed in the hope that it will be useful, but
-- WITHOUT ANY WARRANTY; without even the implied warranty of
-- MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
-- General Public License for more details.

-- You should have received a copy of the GNU General Public License
-- along with LibLPME; see the file LICENSE.md.  If not see
-- <http://www.gnu.org/licenses/>.

-- imports

local http = game:GetService("HttpService")
local liblpme = require(script.Parent.Parent.liblpme)

-- utility

local pack_player = function(plr:Player): string
    return http:JSONEncode({
        ["id"] = plr.UserId,
        ["name"] = plr.Name
    })
end

-- methods

local listen = function(lpme:liblpme.LPME)
    game.Players.PlayerAdded:Connect(function(plr)
        local res = lpme:run_event("/plrlist/join", pack_player(plr))

        if res.ok then
            lpme:trigger_event("player_load", res)
        else
            error(`Player join event failed. HTTP Status: {res.status}`)
        end
    end)

    game.Players.PlayerRemoving:Connect(function(plr)
        local res = lpme:run_event("/plrlist/left", pack_player(plr))

        if not res.ok then
            error(`Player leave event failed. HTTP Status: {res.status}`)
        end
    end)
end

-- module

return function(lpme:liblpme.LPME)
    listen(lpme)
end
