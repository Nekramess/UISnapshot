"""The list of all settings: Forever has the global ConsoleGetAllCommands and no C_Console
(Forever 1.60.1 UI source). 0.5.0-0.6.1 looked only for C_Console.GetAllCommands, so on
Forever Save captured just the 7 tracked CVars and lost Damage Meter etc."""
import sys
from mock_env import make_runtime

results = []
def check(label, cond):
    results.append(("PASS " if cond else "FAIL ") + label)

SETTINGS = r'''
CV.damageMeterEnabled = { "1", "0" }
CV.damageMeterResetOnNewInstance = { "1", "0" }
CV.showSwingTimer = { "1", "1" }          -- equals its default on purpose
CV.cooldownViewerEnabled = { "0", "0" }
'''

def setup(extra=""):
    lua, printed = make_runtime()
    lua.execute(SETTINGS + extra)
    return lua, printed

def slash(lua, msg):
    lua.eval("function(m) SlashCmdList['UISNAPSHOT'](m) end")(msg)

def has(printed, text):
    return any(text in p for p in printed)

def cv(lua, n):
    return lua.eval(f'UISnapshotDB.profiles.p.cvars["{n}"]')

# 1: Forever-like (global only, no C_Console)
lua, printed = setup()
check("setup: Forever-like client has no C_Console", lua.eval("C_Console == nil and ConsoleGetAllCommands ~= nil"))
slash(lua, "save p")
check("forever: Damage Meter settings are saved", cv(lua, "damageMeterEnabled") == "1" and cv(lua, "damageMeterResetOnNewInstance") == "1")
check("forever: Save used the full list (mode all changed from default)", lua.eval("UISnapshotDB.profiles.p.cvarInfo.mode") == "all changed from default")
check("forever: an ordinary changed CVar is saved too", cv(lua, "autoLootDefault") is not None)
check("forever: Swing Timer saved even though equal to default", cv(lua, "showSwingTimer") == "1")
check("forever: no warning printed", not has(printed, "WARNING"))

# 2: load on a 'fresh' character restores them
lua.execute('CV.damageMeterEnabled[1] = "0"; CV.damageMeterResetOnNewInstance[1] = "0"; CV.showSwingTimer[1] = "0"; SETS = {}')
slash(lua, "load p")
check("forever: Load sets Damage Meter back on", lua.eval('CV.damageMeterEnabled[1]') == "1" and lua.eval('CV.damageMeterResetOnNewInstance[1]') == "1")
check("forever: Load sets Swing Timer back", lua.eval('CV.showSwingTimer[1]') == "1")

# 3: retail-like (C_Console only)
lua, printed = setup('''
local f = ConsoleGetAllCommands
C_Console = { GetAllCommands = f }
ConsoleGetAllCommands = nil
''')
slash(lua, "save p")
check("retail-like: C_Console.GetAllCommands still works", lua.eval("UISnapshotDB.profiles.p.cvarInfo.mode") == "all changed from default" and cv(lua, "damageMeterEnabled") == "1")

# 4: neither exists: loud warning, safety net still saves the Advanced Options settings
lua, printed = setup("ConsoleGetAllCommands = nil")
slash(lua, "save p")
check("neither: warns that only some settings were saved", has(printed, "WARNING: only"))
check("neither: Damage Meter / Swing Timer still saved by the safety net",
      cv(lua, "damageMeterEnabled") == "1" and cv(lua, "showSwingTimer") == "1" and cv(lua, "damageMeterResetOnNewInstance") == "1")
check("neither: a CVar not on any list is not saved", cv(lua, "cameraDistanceMaxZoomFactor") is None)
printed.clear()
slash(lua, "watch")
check("neither: watch says why", has(printed, "neither ConsoleGetAllCommands nor C_Console.GetAllCommands exists"))

# 5: the call throws: handled, reason shown
lua, printed = setup('ConsoleGetAllCommands = function() error("restricted") end')
slash(lua, "save p")
check("throws: save still works with a warning and the safety net", has(printed, "WARNING: only") and cv(lua, "damageMeterEnabled") == "1")
printed.clear()
slash(lua, "find damage")
check("throws: find shows the failure reason", has(printed, "the call failed") and has(printed, "restricted"))

# 6: a CVar the client does not have is simply skipped
lua, printed = make_runtime()
slash(lua, "save p")
check("missing CVars: safety-net names that do not exist are not saved", cv(lua, "damageMeterEnabled") is None)

for r in results: print(r)
fails = [r for r in results if r.startswith("FAIL")]
print(f"\n{len(results) - len(fails)}/{len(results)} passed")
sys.exit(1 if fails else 0)
