# Client Utils

Utility package containing additional resources used by the
[main module](./README.md).

## Summary

**Usage:**
```lua
util = require(path.to.util)
```

**Classes:**
- [`EventController`](#eventcontroller) -- Class used for event handling
and firing.
- [`Headers`](#headers) -- Small wrapper around a table that makes keys
case-insensitive.

**Methods:**
- [`construct()`](#utilconstruct) -- Utility that processes a template
with an `__init__` method.
- [`safe_request()`](#utilsaferequest) -- Wrapper around `RequestAsync`
that prevents an error from being thrown.

## Methods

### `util.construct()`

**Arguments:**
- `template: any` -- The template to initialize.
- `...: any` -- Arguments to pass to the `__init__` method.

**Returns:** `any` -- A copy of the template after `__init__` was
called.

This method implements Python-like class handling, where an `__init__`
metamethod handles the initialization of a new instance. When a
template is constructed, a deep-copy of every table is made, and
`template:__init__(...)` is called.

Additionally, if a template contains a `__inherits__` table, any
`__init__` methods within the table will also be called. While it should
contain complete templates (i.e. tables with the `__init__` method),
**no other properties of the inherited templates are used.**

All extra arguments after `template` are passed to the `__init__` method
during construction.

### `util.safe_request()`

**Arguments:**
- `req: {[string]:any}` -- The body to pass to `RequestAsync`.

**Returns:** `RequestAsyncResponse` -- The response.

A simple wrapper around `HttpService:RequestAsync()`.

If the request throws an error (for example, the network connection
fails), a response will still be returned. However, it will contain an
empty body, a status code of `-1` and a status message of the error
issued.

If the request succeeds, all parameters are identical to the values
returned by `RequestAsync`.

## Classes

### `EventController`

A controller to manage event listeners and issuers.

#### Constructor

No native constructor.

An `EventController` should be used as an inherited template. It is
available in `util.templates.event_ctl`.

#### Methods

##### `EventController:add_event_listener()`

**Arguments:**
- `event: string` -- The event to listen for.
- `callback: (...) -> nil` -- The callback to bind to the event.

Bind an event listener for a specific event. All listeners are called
asynchronously when the event is fired.

##### `EventController:trigger_event()`

**Arguments:**
- `event: string` -- The event to fire.
- `...: any` -- Arguments to pass to the event handlers.

Run all event listeners for an event. All additional arguments after
`event` are passed to the listeners.

### `Headers`

A case-insensitive dictionary used to store HTTP headers.

#### Constructor

**Arguments:**
- `from: {[string]: string}|nil` -- An optional table to use as a source
when initializing a new `Headers` object.

#### Methods

##### `Headers:get()`

**Arguments:**
- `key: string` -- The key to get.

**Returns:** `string|nil` -- The item associated with the key, or `nil`
if none are present.

Keys for a `Headers` object are case-insensitive. As such, if an item
has been added to the object with the key `Key`, it will still be
returned if `Headers:get()` is called for any other forms, such as `key`
or `kEy`.

##### `Headers:set()`

**Arguments:**
- `key: string` -- The key to set.
- `value: string` -- The value to assign.

Sets the value associated with a specific case-insensitive key.
