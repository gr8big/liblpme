--!native

-- This file is part of LibLPME.

-- LibLPME is free software; you can redistribute it and/or modify it under
-- the terms of the GNU General Public License as published by the Free
-- Software Foundation; either version 3, or (at your option) any later
-- version.

-- LibLPME is distributed in the hope that it will be useful, but WITHOUT ANY
-- WARRANTY; without even the implied warranty of MERCHANTABILITY or
-- FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
-- for more details.

-- You should have received a copy of the GNU General Public License
-- along with LibLPME; see the file LICENSE.md.  If not see
-- <http://www.gnu.org/licenses/>.

-- imports

local http = game:GetService("HttpService")
local util = require(script.Parent.util)

-- type defs

export type LPMEServerEventResponse = {
    body: string,
    headers: util.Headers,
    status: number,
    ok: boolean,

    json: (self:LPMEServerEventResponse) -> {}|string|number|boolean
}

export type LPME = {
    __session_token: string?,
    __session_id: string?,
    __server_id: string?,
    __base_url: string,
    __poll_thread: thread?,

    __longpoll: (self:LPME) -> nil,
    __commands: {[string]:(data:string) -> nil},

    connect: (self:LPME, api_key:string) -> boolean,
    disconnect: (self:LPME) -> nil,

    run_event: (self:LPME, event:string, data:string) -> LPMEServerEventResponse,
    command: (self:LPME, command_id:string, callback:(data:string) -> nil) -> nil
}

-- templates

local tmp_lpmeservereventresponse: LPMEServerEventResponse = {
    __init__ = function(self:LPMEServerEventResponse, response:{[string]:any})
        self.body = response.Body
        self.status = response.StatusCode
        self.headers = util.Headers(response.Headers)
        self.ok = response.Success
    end,

    json = function(self:LPMEServerEventResponse): {}|string|number|boolean
        return http:JSONDecode(self.body)
    end
}
local tmp_lpme: LPME = {
    __init__ = function(self:LPME, base_url:string)
        while string.sub(base_url, #base_url) == "/" do
            base_url = string.sub(base_url, 1, #base_url - 1)
        end

        self.__base_url = base_url
    end,

    __longpoll = function(self:LPME)
        local fails = 0

        while true do
            local res = self:run_event("/liblpme/longpoll")

            if res.ok then
                fails = 0

                local pattern = string.rep("<s4", tonumber(res.headers:get("X-LPME-Chunk-Count")))
                local chunks = table.pack(string.unpack(pattern, res.body))

                for _, v in pairs(chunks) do
                    local sep = string.find(v, "\x00", 0, true)
                    local cmd, body = string.sub(v, 1, sep - 1), string.sub(sep + 1)

                    if self.__commands[cmd] then
                        self.__commands[cmd](body)
                    else
                        warn(`Received invalid command '{cmd}' from server with data length {#body} (total chunk size {#v})`)
                    end
                end
            else
                fails += 1
                if fails >= 8 then
                    error("Number of failed requests reached maximum", 0)
                end
            end
        end
    end,

    connect = function(self:LPME, api_key:string)
        local res = util.safe_request({
            Url = self.__base_url,
            Method = "POST",
            Body = "",
            Headers = {
                ["X-LPME-Token"] = api_key
            }
        })
        if res.Success then
            local headers = util.Headers(res.Headers)
            self.__session_token = headers:get("X-LPME-Session")
            self.__session_id = headers:get("X-LPME-Session-Id")
            self.__server_id = headers:get("X-LPME-Server-Id")
            
            self.__poll_thread = task.spawn(self.__longpoll)
            return true
        else
            if res.StatusCode == 401 then
                error("Provided API key is invalid.", 0)
            elseif res.StatusCode >= 500 then
                error(`Server encountered error. HTTP Status: {res.StatusCode}`, 0)
            elseif res.StatusCode <= 0 then
                error(res.StatusMessage)
            else
                error(`Unknown error. HTTP Status: {res.StatusCode}`, 0)
            end
        end

        return false
    end,
    disconnect = function(self:LPME)
        self:run_event("/liblpme/shutdown", "")
        if self.__poll_thread then
            task.cancel(self.__poll_thread)
        end
    end,

    run_event = function(self:LPME, event:string, data:string): LPMEServerEventResponse
        local res = util.safe_request({
            Url = `{self.__base_url}/{event}`,
            Method = "POST",
            Body = data,
            Headers = {
                ["X-LPME-Session-Id"] = self.__session_id,
                ["X-LPME-Session"] = self.__session
            }
        })
        return util.construct(tmp_lpmeservereventresponse, res)
    end,
    command = function(self:LPME, command_id:string, callback:(data:string) -> nil)
        self.__commands[command_id] = callback
    end
}

-- module

return {
    LPME = function(base_url:string)
        return util.construct(tmp_lpme, base_url)
    end
}
