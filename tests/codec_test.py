"""Codec tests under Lua 5.1: round trips, damage detection, hostile input."""
import sys, random
from lupa.lua51 import LuaRuntime

lua = LuaRuntime(unpack_returned_tuples=True)
lua.execute("NS = {}")
lua.execute(open("UISnapshot/Codec.lua").read().replace("local ADDON, ns = ...", "local ADDON, ns = 'UISnapshot', NS"))
lua.execute(r'''
C = NS.codec
local function deepEq(a, b)
  if type(a) ~= type(b) then return false end
  if type(a) ~= "table" then return a == b end
  for k, v in pairs(a) do if not deepEq(v, b[k]) then return false end end
  for k in pairs(b) do if a[k] == nil then return false end end
  return true
end
DEEPEQ = deepEq
RESULTS = {}
function check(label, ok) table.insert(RESULTS, (ok and "PASS " or "FAIL ") .. label) end

-- round trips
local samples = {
  empty = {},
  nested = { a = { b = { c = { 1, 2, 3 } } } },
  sparse = { [1] = "x", [3] = "z", [10] = true },
  strings = { "", " ", "line1\nline2", "tab\there", 'quote"s\'', "|cffff0000red|r", "pipe | and \\ backslash",
              "unicode: caf\195\169 \226\130\172", "# $ % & ' ( ) * + , - . /", "s5:fake", "}{", "n1;", string.rep("x", 70000) },
  numbers = { 0, -0.5, 1738.9, 0.66666668653488, 1e300, -1e-300, 123456789012, 3.14159265358979 },
  bools = { yes = true, no = false },
  mixedkeys = { ["a key with spaces"] = 1, [5] = "five", [-2] = "neg", [0.5] = "frac" },
}
for name, v in pairs(samples) do
  local text = C.encode(v)
  local back, err = C.decode(text)
  check("roundtrip " .. name, back ~= nil and DEEPEQ(v, back))
end

-- numbers survive bit-exact
local back = C.decode(C.encode({ x = 0.66666668653488 }))
check("float is bit-exact", back.x == 0.66666668653488)

-- whitespace around a paste is tolerated
local good = C.encode({ k = "v" })
check("leading/trailing whitespace/newlines ok", C.decode("  \n" .. good .. "\r\n\n") ~= nil)

-- encoding is deterministic
check("encode is deterministic", C.encode({ b = 1, a = 2, [1] = 3 }) == C.encode({ [1] = 3, a = 2, b = 1 }))

-- unsupported values are skipped, not fatal
local skipped = C.decode(C.encode({ keep = 1, fn = print }))
check("functions are skipped", skipped and skipped.keep == 1 and skipped.fn == nil)
check("NaN refused", not pcall(C.encode, { x = 0/0 }))
check("infinity refused", not pcall(C.encode, { x = math.huge }))
local deep = {}; local cur = deep
for i = 1, 20 do cur.n = {}; cur = cur.n end
check("too-deep data refused on encode", not pcall(C.encode, deep))

-- damage
local text = C.encode({ name = "Nekramess UI", list = { "a", "b", "c" } })
local function fails(t) local v, e = C.decode(t); return v == nil and type(e) == "string" and #e > 0 end
check("truncated paste detected", fails(text:sub(1, #text - 5)))
check("extended paste detected", fails(text .. "extra"))
check("empty rejected", fails("") and fails("   \n "))
check("not an export rejected", fails("hello world") and fails("UISNAP2:1:1:{}"))
check("nil rejected", fails(nil))
-- flip each single character after the header: must never decode successfully to different data
local survived = 0
local hdrEnd = select(2, text:find("^UISNAP1:%d+:%d+:"))
for i = hdrEnd + 1, #text do
  local c = text:sub(i, i)
  local flipped = text:sub(1, i - 1) .. (c == "x" and "y" or "x") .. text:sub(i + 1)
  local v = C.decode(flipped)
  if v ~= nil then survived = survived + 1 end
end
check("every single-character corruption is detected", survived == 0)
-- a swapped pair of characters is also caught
local swapped = text:sub(1, hdrEnd + 2) .. text:sub(hdrEnd + 4, hdrEnd + 4) .. text:sub(hdrEnd + 3, hdrEnd + 3) .. text:sub(hdrEnd + 5)
check("swapped characters detected", swapped == text or fails(swapped))

-- hostile payloads with a CORRECT checksum/length (so the parser itself is exercised)
local function wrap(payload)
  local sum = (function(s) local a, b = 1, 0 for i = 1, #s do a = (a + s:byte(i)) % 65521; b = (b + a) % 65521 end return b * 65536 + a end)(payload)
  return string.format("UISNAP1:%d:%.0f:%s", #payload, sum, payload)
end
check("string longer than text", fails(wrap("{s999999:ab}")))
check("giant length claim", fails(wrap("{s99999999999:ab}")))
check("bad number", fails(wrap("{s1:an1e;}")) and fails(wrap("{s1:anabc;}")))
check("nan number text", fails(wrap("{s1:annan;}")))
check("table key not string/number", fails(wrap("{TT}")) and fails(wrap("{{}s1:a}")))
check("unclosed table", fails(wrap("{s1:as1:b")))
check("unknown token", fails(wrap("{s1:aq}")))
check("trailing garbage", fails(wrap("{}junk")))
check("root is not a table", fails(wrap("s1:a")))
check("depth bomb", fails(wrap(string.rep("{s1:a", 200) .. string.rep("}", 200))))
check("too many entries rejected", fails(wrap("{" .. string.rep("s1:aT", 6000) .. "}")))
local ok1 = pcall(C.decode, wrap("{" .. string.rep("n1;T", 6000) .. "}"))
check("entry flood does not crash", ok1)

-- fuzz: random strings and mutated valid exports never raise, never return garbage silently
math.randomseed(12345)
local crashed, wrongOK = 0, 0
for i = 1, 3000 do
  local len = math.random(0, 60)
  local t = {}
  for j = 1, len do t[j] = string.char(math.random(32, 126)) end
  local ok = pcall(C.decode, table.concat(t))
  if not ok then crashed = crashed + 1 end
end
for i = 1, 3000 do
  local pos = math.random(1, #text)
  local mutated = text:sub(1, pos - 1) .. string.char(math.random(0, 255)) .. text:sub(pos + 1)
  local ok, v = pcall(C.decode, mutated)
  if not ok then crashed = crashed + 1 elseif v ~= nil and mutated ~= text and not DEEPEQ(v, C.decode(text)) then wrongOK = wrongOK + 1 end
end
check("fuzz: decode never raises (0 crashes)", crashed == 0)
check("fuzz: mutated exports never decode to different data", wrongOK == 0)
''')
res = lua.eval("table.concat(RESULTS, '\\n')")
print(res)
sys.exit(1 if "FAIL" in res else 0)
