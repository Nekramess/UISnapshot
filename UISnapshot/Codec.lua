-- UI Snapshot: text codec for export/import.
-- Turns a plain Lua table (strings, numbers, booleans, nested tables) into one block
-- of text and back. It never runs pasted text as code: a small parser reads it as data.
--
-- Format:  UISNAP1:<payload length>:<checksum>:<payload>
-- Payload: s<len>:<bytes>   string (length-prefixed, so nothing needs escaping)
--          n<number>;       number
--          T / F            booleans
--          { key value ... }   table (keys are strings or numbers)

local ADDON, ns = ...
local Codec = {}
ns.codec = Codec

local HEADER = "UISNAP1"
local MAX_DEPTH = 12
local MAX_STRING = 200000     -- one string
local MAX_ITEMS = 5000        -- entries in one table
local MAX_TOTAL = 2000000     -- whole payload, bytes

local function checksum(s)
    local a, b = 1, 0
    for i = 1, #s do
        a = (a + s:byte(i)) % 65521
        b = (b + a) % 65521
    end
    return b * 65536 + a
end

local function keyLess(x, y)
    local tx, ty = type(x), type(y)
    if tx ~= ty then return tx == "number" end
    return x < y
end

local function ser(v, out, depth)
    local t = type(v)
    if t == "string" then
        out[#out + 1] = "s" .. #v .. ":" .. v
    elseif t == "number" then
        if v ~= v or v == math.huge or v == -math.huge then error("cannot export NaN or infinity", 0) end
        out[#out + 1] = "n" .. string.format("%.17g", v) .. ";"
    elseif t == "boolean" then
        out[#out + 1] = v and "T" or "F"
    elseif t == "table" then
        if depth >= MAX_DEPTH then error("data is nested too deeply", 0) end
        local keys = {}
        for k, val in pairs(v) do
            local tk, tv = type(k), type(val)
            if (tk == "string" or tk == "number")
                and (tv == "string" or tv == "number" or tv == "boolean" or tv == "table") then
                keys[#keys + 1] = k
            end
        end
        table.sort(keys, keyLess)
        out[#out + 1] = "{"
        for _, k in ipairs(keys) do
            ser(k, out, depth + 1)
            ser(v[k], out, depth + 1)
        end
        out[#out + 1] = "}"
    else
        error("cannot export a " .. t, 0)
    end
end

function Codec.encode(value)
    local out = {}
    ser(value, out, 0)
    local payload = table.concat(out)
    return string.format("%s:%d:%.0f:%s", HEADER, #payload, checksum(payload), payload)
end

local function parse(s, pos, depth)
    if depth > MAX_DEPTH then error("data is nested too deeply", 0) end
    local c = s:sub(pos, pos)
    if c == "s" then
        local lenStr, start = s:match("^(%d+):()", pos + 1)
        if not lenStr or #lenStr > 7 then error("bad string header", 0) end
        local len = tonumber(lenStr)
        if len > MAX_STRING then error("string too long", 0) end
        local stop = start + len - 1
        if stop > #s then error("text is cut off", 0) end
        return s:sub(start, stop), stop + 1
    elseif c == "n" then
        local numStr, nxt = s:match("^([^;]*);()", pos + 1)
        if not numStr or #numStr > 40 then error("bad number", 0) end
        local n = tonumber(numStr)
        if not n or n ~= n or n == math.huge or n == -math.huge then error("bad number", 0) end
        return n, nxt
    elseif c == "T" then
        return true, pos + 1
    elseif c == "F" then
        return false, pos + 1
    elseif c == "{" then
        local t, count = {}, 0
        pos = pos + 1
        while true do
            if s:sub(pos, pos) == "}" then return t, pos + 1 end
            local k, v
            k, pos = parse(s, pos, depth + 1)
            if type(k) ~= "string" and type(k) ~= "number" then error("bad key", 0) end
            v, pos = parse(s, pos, depth + 1)
            t[k] = v
            count = count + 1
            if count > MAX_ITEMS then error("too many entries", 0) end
        end
    end
    error(pos > #s and "text is cut off" or "unexpected character", 0)
end

-- Returns the table, or nil plus a message fit to show the user.
function Codec.decode(text)
    if type(text) ~= "string" then return nil, "Nothing to import." end
    text = text:gsub("^%s+", "")
    text = text:gsub("%s+$", "")
    if text == "" then return nil, "Paste an export into the box first." end
    local len, sum, start = text:match("^" .. HEADER .. ":(%d+):(%d+):()")
    if not len then return nil, "That doesn't look like a UI Snapshot export (it should start with " .. HEADER .. ":)." end
    len, sum = tonumber(len), tonumber(sum)
    if len > MAX_TOTAL then return nil, "That export is too large." end
    local payload = text:sub(start)
    if #payload ~= len then
        return nil, ("The export is %d characters long but should be %d. It was probably cut off or changed when copied; copy it again.")
            :format(#payload, len)
    end
    if checksum(payload) ~= sum then
        return nil, "The export is damaged (checksum mismatch). Copy it again."
    end
    local ok, value, stop = pcall(parse, payload, 1, 0)
    if not ok then return nil, "The export could not be read: " .. tostring(value) end
    if stop ~= #payload + 1 then return nil, "The export has extra data after the end." end
    if type(value) ~= "table" then return nil, "The export has no data in it." end
    return value
end
