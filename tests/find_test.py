"""/uisnap find, watch and changed: locating the CVar behind a setting (simulated client)."""
import sys
from mock_env import make_runtime

results = []
def check(label, cond):
    results.append(("PASS " if cond else "FAIL ") + label)

EXTRA = r'''
CV.damageMeterEnabled = { "0", "0" }
CV.damageMeterAutoReset = { "0", "0" }
CV.swingTimerEnabled = { "1", "0" }
local oldGet = C_Console.GetAllCommands
C_Console.GetAllCommands = function()
  local t = oldGet()
  for _, c in ipairs(t) do
    if c.command == "damageMeterEnabled" then c.help = "Enables the built-in meter" end
    if c.command == "swingTimerEnabled" then c.help = "Show swing timer" end
    if c.command == "damageMeterAutoReset" then c.help = "Reset on new instance" end
  end
  return t
end
'''

def setup():
    lua, printed = make_runtime()
    lua.execute(EXTRA)
    return lua, printed

def slash(lua, msg):
    lua.eval("function(m) SlashCmdList['UISNAPSHOT'](m) end")(msg)

def has(printed, text):
    return any(text in p for p in printed)

# find by name
lua, printed = setup()
slash(lua, "find damage")
check("find: matches by name (3 hits)", has(printed, "3 CVars match 'damage'"))
check("find: unchecked setting equals default, so it would NOT be saved",
      has(printed, "damageMeterEnabled = 0 (default 0): equals its default: not saved"))
lua.execute('CV.damageMeterEnabled[1] = "1"')
printed.clear()
slash(lua, "find damage")
check("find: ticked setting is reported as captured by Save", has(printed, "damageMeterEnabled = 1 (default 0): differs from default: Save captures it"))

# find by help text
printed.clear()
slash(lua, "find swing")
check("find: matches help text too / swing timer", has(printed, "swingTimerEnabled = 1"))
printed.clear()
slash(lua, "find BUILT-IN")
check("find: help match is case-insensitive", has(printed, "damageMeterEnabled"))
printed.clear()
slash(lua, "find nothingmatchesthis")
check("find: no match says the setting may not be a CVar", has(printed, "may not be a CVar"))
printed.clear()
slash(lua, "find")
check("find: no argument prints usage", has(printed, "/uisnap find <text>"))

# find with a profile shows whether the profile has it
lua, printed = setup()
lua.execute('CV.damageMeterEnabled[1] = "1"')
slash(lua, "save p1")
lua.execute('UISnapshotDB.profiles.p1.cvars.damageMeterEnabled = nil')
printed.clear()
slash(lua, "find damage p1")
check("find with profile: reports NOT in the profile", has(printed, "NOT in 'p1'"))
lua.execute('UISnapshotDB.profiles.p1.cvars.damageMeterEnabled = "1"')
printed.clear()
slash(lua, "find damage p1")
check("find with profile: reports the saved value", has(printed, "in 'p1': 1"))
printed.clear()
slash(lua, "find damage nosuch")
check("find with unknown profile: says so and still lists live values", has(printed, "No profile named 'nosuch'") and has(printed, "damageMeterEnabled"))

# watch -> change -> changed
lua, printed = setup()
slash(lua, "changed")
check("changed before watch asks for watch first", has(printed, "/uisnap watch first"))
slash(lua, "watch")
check("watch: reports how many CVars", has(printed, "Watching") and has(printed, "CVars"))
printed.clear()
slash(lua, "changed")
check("changed with nothing flipped says it is probably not a CVar", has(printed, "No CVar changed"))
lua.execute('CV.damageMeterEnabled[1] = "1"; CV.gxWindow[1] = "0"; CV.lockedThing[1] = "8"')
printed.clear()
slash(lua, "changed")
check("changed: lists the flipped CVar with old -> new and verdict",
      has(printed, "damageMeterEnabled: 0 -> 1 (default 0): differs from default: Save captures it"))
check("changed: deny-listed CVar is flagged never saved", has(printed, "gxWindow") and has(printed, "never saved"))
check("changed: locked CVar is flagged skipped", has(printed, "lockedThing") and has(printed, "locked from users: skipped"))

# many changes are capped
lua, printed = setup()
lua.execute('for i = 1, 40 do CV["bulk" .. i] = { "0", "0" } end')
slash(lua, "watch")
lua.execute('for i = 1, 40 do CV["bulk" .. i][1] = "1" end')
printed.clear()
slash(lua, "changed")
check("changed: output capped at 25 lines plus a count", sum(1 for x in printed if x.startswith("bulk") or "bulk" in x) == 25 and has(printed, "and 15 more"))

# API missing
lua, printed = make_runtime()
lua.execute("C_Console = nil")
slash(lua, "watch")
slash(lua, "find damage")
check("no C_Console: watch and find explain instead of erroring", has(printed, "cannot be watched") and has(printed, "not available"))

for r in results: print(r)
fails = [r for r in results if r.startswith("FAIL")]
print(f"\n{len(results) - len(fails)}/{len(results)} passed")
sys.exit(1 if fails else 0)
