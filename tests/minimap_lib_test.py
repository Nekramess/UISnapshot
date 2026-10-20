"""Minimap button: registered through the embedded LibDBIcon-1.0, and the .toc loads the
libraries in order. Reason: a minimap button manager flagged the old hand-built button with
"This is a custom button. Please ask the addon author to use the standard LibDBIcon library
instead." Simulated client only (tests/mock_env.py); not the live client."""
import re
from mock_env import make_runtime, FILES

results = []
def check(label, cond):
    results.append(("PASS " if cond else "FAIL ") + label)

# The .toc lists the four libraries first, in dependency order, before the addon files.
toc = [l.strip().replace("\\", "/") for l in open("UISnapshot/UISnapshot.toc") if l.strip() and not l.startswith("#")]
want = ["Libs/LibStub/LibStub.lua", "Libs/CallbackHandler-1.0/CallbackHandler-1.0.lua",
        "Libs/LibDataBroker-1.1/LibDataBroker-1.1.lua", "Libs/LibDBIcon-1.0/LibDBIcon-1.0.lua"]
check("toc lists the libraries in dependency order, before Minimap.lua",
      all(w in toc for w in want) and [toc.index(w) for w in want] == sorted(toc.index(w) for w in want)
      and toc.index(want[-1]) < toc.index("Minimap.lua"))
check("mock_env loads the same files as the toc (same order)", [f.replace("UISnapshot/", "") for f in FILES] == toc)

def fire(lua, ev="PLAYER_LOGIN"): lua.execute('FIRE("%s")' % ev)

# Fresh install: registered, shown, default angle in LibDBIcon's field
lua, printed = make_runtime()
fire(lua)
check("registered with LibDBIcon", lua.eval('LibStub("LibDBIcon-1.0"):IsRegistered("UISnapshot")'))
check("shown by default", lua.eval('LibStub("LibDBIcon-1.0"):GetMinimapButton("UISnapshot"):IsShown()'))
check("default minimapPos 215", lua.eval("NS.db().settings.minimap.minimapPos") == 215)

# Settings from before the library: angle carries over, shape override dropped, hidden kept
lua, printed = make_runtime()
lua.execute('UISnapshotDB = { settings = { minimap = { hide = true, angle = 123, shape = "square" } } }')
fire(lua)
check("old angle becomes minimapPos", lua.eval("NS.db().settings.minimap.minimapPos") == 123)
check("old angle and shape keys removed", lua.eval("NS.db().settings.minimap.angle == nil and NS.db().settings.minimap.shape == nil"))
check("old hidden flag keeps the button hidden", lua.eval('not LibStub("LibDBIcon-1.0"):GetMinimapButton("UISnapshot"):IsShown()'))
lua, printed = make_runtime()
lua.execute('UISnapshotDB = { settings = { minimap = { angle = "junk" } } }')
fire(lua)
check("unusable old angle: default 215", lua.eval("NS.db().settings.minimap.minimapPos") == 215)

# Square minimap: LibDBIcon follows GetMinimapShape on the next placement
lua, printed = make_runtime()
lua.execute('UISnapshotDB = { settings = { minimap = { hide = false, minimapPos = 45 } } }')
lua.execute('GetMinimapShape = function() return "SQUARE" end')
fire(lua)
x, y = lua.eval('(function() local p = LibStub("LibDBIcon-1.0"):GetMinimapButton("UISnapshot").lastPoint; return p[4], p[5] end)()')
check("square minimap: button pushed toward the box corner", x > 65 and y > 65 and (x * x + y * y) ** 0.5 > 80)

# Libraries missing (broken install): no errors, commands still answer
files = [f for f in FILES if "/Libs/" not in f]
lua, printed = make_runtime(files)
fire(lua)
ok = lua.eval("pcall(SlashCmdList['UISNAPSHOT'], 'minimap off')")
check("without the libraries /uisnap minimap does not error", ok)
check("without the libraries the window still opens", lua.eval("pcall(SlashCmdList['UISNAPSHOT'], '') and UISnapshotFrame ~= nil"))

for r in results: print(r)
failed = [r for r in results if r.startswith("FAIL")]
print("%d/%d passed" % (len(results) - len(failed), len(results)))
raise SystemExit(1 if failed else 0)
