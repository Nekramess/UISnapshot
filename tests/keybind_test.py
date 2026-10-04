"""Key binding capture / restore against a simulated binding API (not the live client)."""
import sys
from mock_env import make_runtime

results = []
def check(label, cond):
    results.append(("PASS " if cond else "FAIL ") + label)

BIND_API = r'''
BINDS = {
  { cmd = "MOVEFORWARD",  keys = { "W", "UP" } },
  { cmd = "MOVEBACKWARD", keys = { "S" } },
  { cmd = "JUMP",         keys = { "SPACE" } },
  { cmd = "TOGGLEBACKPACK", keys = { "B" } },
  { cmd = "ACTIONBUTTON1", keys = { "1" } },
  { cmd = "ACTIONBUTTON2", keys = {} },
  { cmd = "HEADER_ONLY",  keys = {} },
}
SETCALLS, SAVED, FAIL_KEYS = {}, {}, {}
BINDSET = 1
InCombat = false
InCombatLockdown = function() return InCombat end
GetNumBindings = function() return #BINDS end
GetBinding = function(i)
  local b = BINDS[i]
  return b.cmd, "BINDING_HEADER_X", unpack(b.keys)
end
local function find(cmd) for _, b in ipairs(BINDS) do if b.cmd == cmd then return b end end end
SetBinding = function(key, cmd)
  SETCALLS[#SETCALLS + 1] = { key, cmd }
  if FAIL_KEYS[key] then error("restricted") end
  for _, b in ipairs(BINDS) do
    for i = #b.keys, 1, -1 do if b.keys[i] == key then table.remove(b.keys, i) end end
  end
  if cmd then
    local b = find(cmd)
    if not b then return nil end
    b.keys[#b.keys + 1] = key
  end
  return 1
end
GetCurrentBindingSet = function() return BINDSET end
SaveBindings = function(which) SAVED[#SAVED + 1] = which end
function KEYS(cmd) local b = find(cmd); return table.concat(b.keys, ",") end
'''

def setup():
    lua, printed = make_runtime()
    lua.execute(BIND_API)
    return lua, printed

def slash(lua, msg):
    lua.eval("function(m) SlashCmdList['UISNAPSHOT'](m) end")(msg)

def has(printed, text):
    return any(text in p for p in printed)

# 1: save captures every listed command, with and without keys
lua, printed = setup()
slash(lua, "save kb")
p = lua.eval("UISnapshotDB.profiles.kb.bindings")
entries = [p[i] for i in range(1, len(p) + 1)]
check("save: captured one entry per listed command (7)", len(entries) == 7)
check("save: two keys on one command kept", "MOVEFORWARD W UP" in entries)
check("save: command without keys kept as bare name", "ACTIONBUTTON2" in entries and "HEADER_ONLY" in entries)
check("save: message reports commands with keys", has(printed, "Key bindings: 5 commands with keys saved (of 7 listed)"))

# 2: restore after changes: rebound, cleared and swapped keys all come back
lua.execute('SetBinding("W", nil); SetBinding("S", "JUMP"); SetBinding("1", nil); SetBinding("F9", "ACTIONBUTTON2")')
check("setup: bindings are really changed", lua.eval('KEYS("MOVEFORWARD")') == "UP" and lua.eval('KEYS("JUMP")') == "SPACE,S")
lua.execute("SETCALLS = {}")
printed.clear()
slash(lua, "load kb")
check("load: MOVEFORWARD restored to W,UP (order may differ)", sorted(lua.eval('KEYS("MOVEFORWARD")').split(",")) == ["UP", "W"])
check("load: MOVEBACKWARD gets S back", lua.eval('KEYS("MOVEBACKWARD")') == "S")
check("load: JUMP loses the extra S", lua.eval('KEYS("JUMP")') == "SPACE")
check("load: ACTIONBUTTON1 gets 1 back", lua.eval('KEYS("ACTIONBUTTON1")') == "1")
check("load: key added to a command that should be empty is cleared (F9)", lua.eval('KEYS("ACTIONBUTTON2")') == "")
check("load: saved with the active binding set", lua.eval("#SAVED") == 1 and lua.eval("SAVED[1]") == 1)
check("load: report line printed", has(printed, "Key bindings:") and has(printed, ", saved"))
lua.execute("SETCALLS = {}")
printed.clear()
slash(lua, "diff kb")
check("diff after load: bindings all match", has(printed, "Key bindings: all match"))

# 3: character binding set is passed through to SaveBindings
lua.execute("BINDSET = 2; SAVED = {}")
slash(lua, "load kb")
check("load: character-specific set (2) is saved as 2", lua.eval("SAVED[1]") == 2)

# 4: a key moving between commands is freed before it is rebound
lua, printed = setup()
slash(lua, "save kb")
lua.execute('SetBinding("B", "JUMP")')      # B moved from TOGGLEBACKPACK to JUMP
lua.execute("SETCALLS = {}")
slash(lua, "load kb")
check("move: B is back on TOGGLEBACKPACK", lua.eval('KEYS("TOGGLEBACKPACK")') == "B" and lua.eval('KEYS("JUMP")') == "SPACE")

# 5: combat blocks the whole load, nothing is changed
lua, printed = setup()
slash(lua, "save kb")
lua.execute('SetBinding("W", nil); SETCALLS = {}; InCombat = true')
slash(lua, "load kb")
check("combat: no SetBinding call made", lua.eval("#SETCALLS") == 0)

# 6: a failing SetBinding is counted and does not stop the rest
lua, printed = setup()
slash(lua, "save kb")
lua.execute('SetBinding("W", nil); SetBinding("S", nil); FAIL_KEYS["W"] = true; SETCALLS = {}')
printed.clear()
slash(lua, "load kb")
check("failure: other keys still restored", lua.eval('KEYS("MOVEBACKWARD")') == "S")
check("failure: reported as failed", has(printed, "1 failed"))

# 7: export/import keeps bindings; only listed commands are ever bound
lua, printed = setup()
slash(lua, "save kb")
slash(lua, "export kb")
text = lua.eval("UISnapshotCopyFrame.edit:GetText()")
lua.execute("UISnapshotDB.profiles = {}")
lua.eval("function(t) return NS.importString(t, 'imp', false) end")(text)
q = lua.eval("UISnapshotDB.profiles.imp.bindings")
check("import: bindings round trip through the export text", q is not None and len(q) == 7 and q[1] == "MOVEFORWARD W UP")

# 8: hostile imported entries are dropped or ignored
lua, printed = setup()
slash(lua, "save kb")
lua.execute('''
local b = UISnapshotDB.profiles.kb.bindings
b[#b+1] = "RUNSCRIPT_EVIL F1"
b[#b+1] = "MACRO evil F2"
b[#b+1] = "JUMP\\0 F3"
b[#b+1] = string.rep("A", 500) .. " F4"
b[#b+1] = "TOGGLEBACKPACK |cffff0000"
''')
slash(lua, "export kb")
text = lua.eval("UISnapshotCopyFrame.edit:GetText()")
lua.execute("UISnapshotDB.profiles = {}")
lua.eval("function(t) return NS.importString(t, 'h', false) end")(text)
ents = lua.eval("(function() local o = {} for _, e in ipairs(UISnapshotDB.profiles.h.bindings) do o[#o+1] = e end return table.concat(o, '\\n') end)()")
check("hostile: control char, oversized and pipe entries dropped", "\x00" not in ents and "F3" not in ents and "F4" not in ents and "cff" not in ents)
check("hostile: clean-looking entries survive (and are checked at load)", "RUNSCRIPT_EVIL F1" in ents)
lua.execute("SETCALLS = {}")
slash(lua, "load h")
unknown_bound = lua.eval('(function() for _, c in ipairs(SETCALLS) do if c[2] == "RUNSCRIPT_EVIL" or c[2] == "MACRO" or c[2] == "evil" then return true end end return false end)()')
check("hostile: commands the client does not list are never bound", not unknown_bound)
check("hostile: skipped unknown commands are reported", has(printed, "skipped"))

# 9: API missing: save still works, load of such a profile and old profiles are safe
lua, printed = make_runtime()
slash(lua, "save nokb")
check("no API: save works, bindings not captured", lua.eval("UISnapshotDB.profiles.nokb.bindings == nil") and has(printed, "Key bindings: not captured"))
lua.execute('UISnapshotDB.profiles.old = { chat = {}, cvars = {}, addons = {}, editMode = { layouts = {} } }')
printed.clear()
slash(lua, "load old")
check("old profile without bindings loads without error", has(printed, "Applied 'old'"))
slash(lua, "show old")
check("show: old profile says no bindings saved", has(printed, "none saved in this profile"))

# 10: keys / cvars / show views
lua, printed = setup()
slash(lua, "save kb")
slash(lua, "keys kb")
box = lua.eval("UISnapshotCopyFrame.edit:GetText()")
check("keys: lists commands with keys, sorted, no empty ones", box.split("\n")[0] == "ACTIONBUTTON1: 1" and "MOVEFORWARD: W, UP" in box and "HEADER_ONLY" not in box)
slash(lua, "cvars kb")
box = lua.eval("UISnapshotCopyFrame.edit:GetText()")
check("cvars view also shows the key binding section", "-- Key bindings --" in box and "JUMP: SPACE" in box)
slash(lua, "show kb")
check("show: reports saved bindings", has(printed, "Key bindings saved: 5 commands with keys"))
lua.execute('SetBinding("S", "JUMP")')
printed.clear()
slash(lua, "diff kb")
check("diff: differing commands listed", has(printed, "Key bindings: 2 commands differ") and has(printed, "JUMP: now SPACE/S, saved SPACE"))

for r in results: print(r)
fails = [r for r in results if r.startswith("FAIL")]
print(f"\n{len(results) - len(fails)}/{len(results)} passed")
sys.exit(1 if fails else 0)
