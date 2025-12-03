--!native

-- imports

local http = game:GetService("HttpService")

-- types

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

-- Construct an object from a template.  
-- The template must contain an `__init__` method,
-- which is called with all other arguments to emulate
-- the `class` behavior in Python.
local construct = function(template, ...): any
    local res = somewhat_deep_copy(template)
    res:__init__(...)
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
    end
}
