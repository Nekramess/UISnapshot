"""Export copy box: plain-ASCII safe export, import round trip, odd-value note, truncation warning."""
import sys
from mock_env import make_runtime

results = []
def check(label, cond):
    results.append(("PASS " if cond else "FAIL ") + label)

def slash(lua, msg):
    lua.eval("function(m) SlashCmdList['UISNAPSHOT'](m) end")(msg)

def has(printed, text):
    return any(text in p for p in printed)

ODD = r'''
CV.oddPipeValue = { "|cffff0000red|r |Tpath:16|t", "0" }
CV.oddBytesValue = { "caf\195\169 \255\254 line1\nline2 ~41", "0" }
'''

lua, printed = make_runtime()
lua.execute(ODD)
slash(lua, "save p")
printed.clear()
slash(lua, "export p")
box = lua.eval("UISnapshotCopyFrame.edit:GetText()")
check("export: box holds the export (UISNAP1E header)", box.startswith("UISNAP1E:"))
check("export: nothing but plain printable ASCII, no pipe, in the box", all(32 <= ord(c) <= 126 and c != "|" for c in box))
check("export: the odd settings are named in a note", has(printed, "Note:") and has(printed, "oddPipeValue") and has(printed, "oddBytesValue"))
check("export: no truncation warning when the box holds everything", not has(printed, "WARNING"))
check("export: reported length equals the box length", has(printed, f"is {len(box)} characters"))

# round trip into an empty database restores the odd values exactly
lua.execute("UISnapshotDB.profiles = {}")
name = lua.eval("function(t) return NS.importString(t, 'back', false) end")(box)
check("import of the safe export works", name == "back")
check("pipe value comes back exactly", lua.eval('UISnapshotDB.profiles.back.cvars.oddPipeValue') == "|cffff0000red|r |Tpath:16|t")

# the exact-bytes comparison, done in Lua so no encoding guesses are involved
ok = lua.eval(r'''(function()
  local want = "caf\195\169 \255\254 line1\nline2 ~41"
  return UISnapshotDB.profiles.back.cvars.oddBytesValue == want
end)()''')
check("odd bytes round trip exactly (compared in Lua)", ok)

# legacy (unescaped) exports still import
lua.execute("UISnapshotDB.profiles = {}")
legacy = lua.eval('''(function()
  local p = { saved = "x", character = "y", chat = {}, cvars = { a = "1" }, addons = {}, editMode = { layouts = {} } }
  return NS.codec.encode({ v = 1, name = "old", profile = p })
end)()''')
check("legacy export starts with UISNAP1:", legacy.startswith("UISNAP1:"))
check("legacy export still imports", lua.eval("function(t) return NS.importString(t, nil, false) end")(legacy) == "old")

# a box that cannot hold the whole text is reported
lua, printed = make_runtime()
slash(lua, "save p")
slash(lua, "export p")
lua.execute("UISnapshotCopyFrame.edit.SetText = function(self, v) self.text = v:sub(1, 1000) end")
printed.clear()
slash(lua, "export p")
check("short box: WARNING says how much it holds", has(printed, "WARNING: the box holds 1000 of the"))

# large profile: many odd CVars, still plain ASCII and round trips
lua, printed = make_runtime()
lua.execute('for i = 1, 300 do CV["bulkOdd" .. i] = { "v|" .. i .. "\\n\\255", "0" } end')
slash(lua, "save p")
printed.clear()
slash(lua, "export p")
box = lua.eval("UISnapshotCopyFrame.edit:GetText()")
check("large: plain ASCII", all(32 <= ord(c) <= 126 and c != "|" for c in box))
check("large: note lists at most 8 names then dots", has(printed, "300 settings have unusual characters") and has(printed, ", ..."))
lua.execute("UISnapshotDB.profiles = {}")
check("large: imports and keeps all 300", lua.eval("function(t) return NS.importString(t, 'big', false) end")(box) == "big"
      and lua.eval("(function() local n = 0 for k in pairs(UISnapshotDB.profiles.big.cvars) do if k:find('^bulkOdd') then n = n + 1 end end return n end)()") == 300)

for r in results: print(r)
fails = [r for r in results if r.startswith("FAIL")]
print(f"\n{len(results) - len(fails)}/{len(results)} passed")
sys.exit(1 if fails else 0)
