--!native

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

-- types

export type EventController = {
    __event_listeners: {[string]:{(...any) -> nil}},
    add_event_listener: (self:EventController, event:string, callback:(...any) -> nil) -> nil,
    trigger_event: (self:EventController, event:string, ...any) -> nil
}

export type Headers = {
    __values: {[string]:string},

    get: (self:Headers, key:string) -> string?,
    set: (self:Headers, key:string, value:string) -> nil
}

export type RequestAsyncResponse = {
    Success: boolean,
    StatusCode: number,
    StatusMessage: string,
    Headers: {[string]:any},
    Body: any
}

-- templates

local tmp_fire_event: EventController = {
    __init__ = function(self)
        self.__event_listeners = {}
    end,

    add_event_listener = function(self:EventController, event:string, callback:(...any) -> nil)
        self.__event_listeners[event] = self.__event_listeners[event] or {}
        self.__event_listeners[event][#self.__event_listeners[event]+1] = callback
    end,

    trigger_event = function(self:EventController, event:string, ...)
        if self.__event_listeners[event] then
            for _, i in pairs(self.__event_listeners[event]) do
                task.spawn(i, ...)
            end
        end
    end
}

local tmp_headers: Headers = {
    __init__ = function(self:Headers, from:{[string]:string})
        self.__values = {}
        for i, j in pairs(from) do
            self.__values[string.lower(i)] = j
        end
    end,
    get = function(self:Headers, key:string): string
        return self.__values[string.lower(key)]
    end,
    set = function(self:Headers, key:string, value:string)
        self.__values[string.lower(key)] = value
    end
}

-- utility

somewhat_deep_copy = function(v:{}): {}
    local res = {}
    for i, j in pairs(v) do
        if type(j) == "table" then
            res[i] = somewhat_deep_copy(j)
        else
            res[i] = j
        end
    end

    return res
end

--[[ Construct an object from a template.

The template must contain an `__init__` method, which is called with all
other arguments to emulate the `class` behavior in Python.

Additionally, a `__inherits__` table may be included, which can contain
references to other templates. The `__init__` method from these
templates will be called on the object, but **values are not
inherited.**
]]
local construct = function(template, ...): any
    local res = somewhat_deep_copy(template)
    res:__init__(...)

    if res.__inherits__ then
        for _, v in pairs(res.__inherits__) do
            v.__init__(res, ...)
        end
    end

    return res
end

local request = function(request): {[string]:any}
    return http:RequestAsync(request)
end

-- module

return {
    -- Construct `Headers`.  
    -- A `Headers` object is a case-insensitive dictionary.  
    -- Optionally, a dictionary can be passed to the
    -- constructor, which will be used to initialize the
    -- headers.
    Headers = function(from:{[string]:string}?): Headers
        return construct(tmp_headers, from or {})
    end,

    construct = construct,

    -- Safely perform an HTTP request.  
    -- The `req` argument is identical to that of
    -- `HttpService:RequestAsync()`.  
    -- If an error is thrown, the status code `-1` is
    -- returned, and the error will be used as the
    -- status message.
    safe_request = function(req): RequestAsyncResponse
        local s, e = pcall(request, req)
        if s then
            return e
        end
        return {
            Success = false,
            StatusCode = -1,
            StatusMessage = e,
            Headers = {},
            Body = ""
        }
    end,

    templates = {
        event_ctl = tmp_fire_event
    }
}
