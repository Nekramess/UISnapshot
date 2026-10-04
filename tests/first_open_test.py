"""Regression: the window must open on the FIRST press (slash command, minimap button,
Import box). The real client shows frames the moment CreateFrame returns them, so a
build-then-toggle sequence used to hide the window on first use (0.5.0 bug)."""
import sys
from mock_env import make_runtime

results = []
def check(label, cond):
    results.append(("PASS " if cond else "FAIL ") + label)

def slash(lua, msg):
    lua.eval("function(m) SlashCmdList['UISNAPSHOT'](m) end")(msg)

# A: first /uisnap opens, second closes, third opens again
lua, printed = make_runtime()
check("A: before any use there is no window", lua.eval("UISnapshotFrame == nil"))
slash(lua, "")
check("A: first /uisnap opens the window", lua.eval("UISnapshotFrame ~= nil and UISnapshotFrame:IsShown()"))
slash(lua, "")
check("A: second /uisnap closes it", lua.eval("not UISnapshotFrame:IsShown()"))
slash(lua, "")
check("A: third /uisnap opens it again", lua.eval("UISnapshotFrame:IsShown()"))
slash(lua, "ui")
check("A: /uisnap ui toggles it closed", lua.eval("not UISnapshotFrame:IsShown()"))
slash(lua, "ui")
check("A: /uisnap ui toggles it open", lua.eval("UISnapshotFrame:IsShown()"))

# B: first minimap click opens (nothing else has opened the window before)
lua, printed = make_runtime()
lua.execute('FIRE("PLAYER_LOGIN")')
check("B: minimap button exists after login", lua.eval("UISnapshotMinimapButton ~= nil and UISnapshotMinimapButton:IsShown()"))
lua.execute('local b = UISnapshotMinimapButton; b.scripts.OnClick(b, "LeftButton")')
check("B: first minimap click opens the window", lua.eval("UISnapshotFrame ~= nil and UISnapshotFrame:IsShown()"))
lua.execute('local b = UISnapshotMinimapButton; b.scripts.OnClick(b, "LeftButton")')
check("B: second minimap click closes it", lua.eval("not UISnapshotFrame:IsShown()"))
lua.execute('local b = UISnapshotMinimapButton; b.scripts.OnClick(b, "LeftButton")')
check("B: third minimap click opens it again", lua.eval("UISnapshotFrame:IsShown()"))

# C: the Import box also opens on first use, from the command and from the window button
lua, printed = make_runtime()
slash(lua, "import")
check("C: first /uisnap import opens the box", lua.eval("UISnapshotImportFrame ~= nil and UISnapshotImportFrame:IsShown()"))
lua, printed = make_runtime()
slash(lua, "")
lua.execute('''
local btn
for _, fr in ipairs(CREATED) do if fr.kind == "Button" and fr.text == "Import" then btn = fr end end
btn.scripts.OnClick(btn)
''')
check("C: window Import button opens the box on first use", lua.eval("UISnapshotImportFrame:IsShown()"))
lua.execute('UISnapshotImportFrame:Hide()')
lua.execute('''
local btn
for _, fr in ipairs(CREATED) do if fr.kind == "Button" and fr.text == "Import" and fr.scripts.OnClick ~= nil then btn = btn or fr end end
btn.scripts.OnClick(btn)
''')
check("C: and again after closing it", lua.eval("UISnapshotImportFrame:IsShown()"))

# D: output goes to chat while the window is closed (a never-opened or closed window must not swallow it)
lua, printed = make_runtime()
before = len(printed)
slash(lua, "list")
check("D: before the window exists, output goes to chat", len(printed) > before)
slash(lua, ""); slash(lua, "")        # open then close
before = len(printed)
slash(lua, "list")
check("D: after closing the window, output goes to chat", len(printed) > before)

# E: the copy box (Export / Edit Mode strings) opens on first use
lua, printed = make_runtime()
lua.execute('NS.commands.save("x")')
slash(lua, "export x")
check("E: Export opens the copy box", lua.eval("UISnapshotCopyFrame ~= nil and UISnapshotCopyFrame:IsShown()"))

print("\n".join(results))
sys.exit(1 if any(r.startswith("FAIL") for r in results) else 0)
