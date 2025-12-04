local liblmpe = require(game.ServerStorage.LPME.liblpme)

local lpme = liblmpe.LPME("http://localhost:8080/lpme")

local state = lpme:connect("a token")
if not state then
    error("Failed to connect. Ensure the test server is running.")
end

-- bind command

lpme:command("test", function(data)
    print("Got message from server:", data)
end)

-- bind to game close

game:BindToClose(function()
    lpme:disconnect()
end)

-- one-shot command

lpme:run_event("test", "Hello, world!")

-- run-later command

lpme:run_event("longtest", "")
