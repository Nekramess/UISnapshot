"""Smoke test: runs UISnapshot.lua under Lua 5.1 against a simulated WoW client.
This is NOT the live client; it only catches Lua errors and logic slips."""
import sys
from lupa.lua51 import LuaRuntime

lua = LuaRuntime(unpack_returned_tuples=True)
printed = []
lua.globals().print = lambda *a: printed.append(" ".join(str(x) for x in a))

lua.execute(r'''
NUM_CHAT_WINDOWS = 3
local cv = { uiScale = "0.64", useUiScale = "1", chatStyle = "classic" }
function GetCVar(n) return cv[n] end
C_CVar = { SetCVar = function(n, v) cv[n] = v; return true end }
local chat = {
  { "General", 18, 0,0,0, 1, true, true, 1, false },
  { "Combat Log", 14, 0,0,0, 1, true, true, 2, false },
  { "Guild", 12, 0,0,0, 0.5, true, false, nil, false },
}
function GetChatWindowInfo(i) if chat[i] then return unpack(chat[i]) end end
function GetChatWindowMessages(i) return "SAY", "GUILD" end
function GetChatWindowChannels(i) return "Trade", 2 end
for i = 1, 3 do
  local f = { isDocked = (i <= 2) }
  function f:GetSize() return 400, 200 end
  function f:GetPoint() return "BOTTOMLEFT", nil, "BOTTOMLEFT", 10, 20 end
  function f:ClearAllPoints() end
  function f:SetPoint() end
  function f:SetSize() end
  _G["ChatFrame"..i] = f
end
SetChatWindowName = function() end SetChatWindowSize = function() end
SetChatWindowColor = function() end SetChatWindowAlpha = function() end
SetChatWindowLocked = function() end
ChatFrame_RemoveAllMessageGroups = function() end ChatFrame_AddMessageGroup = function() end
ChatFrame_RemoveAllChannels = function() end ChatFrame_AddChannel = function() end
C_EditMode = {
  GetLayouts = function() return { layouts = { { layoutName = "UI", layoutType = 1 } }, activeLayout = 1 } end,
  ConvertLayoutInfoToString = function(l) return "2 49 0 0 " .. l.layoutName end,
}
C_AddOns = {
  GetNumAddOns = function() return 2 end,
  GetAddOnInfo = function(i) return ({ "Details", "SpellCDTracker" })[i] end,
  GetAddOnEnableState = function(n, p) return n == "Details" and 2 or 0 end,
  EnableAddOn = function() end,
}
UnitName = function() return "Nekramess" end
GetRealmName = function() return "Test" end
InCombatLockdown = function() return false end
GetPhysicalScreenSize = function() return 3840, 1080 end
EditModeManagerFrame = { GetActiveLayoutInfo = function() return { layoutName = "UI" } end }
UIParent = { GetScale = function() return 0.64 end }
GetScreenWidth = function() return 5120 end GetScreenHeight = function() return 1440 end
date = os.date
SlashCmdList = {}
''')


lua.execute(r"""
-- Catch-all frame: any method exists and returns a harmless value; scripts are recorded.
local shown = {}
local function newFrame(name)
  local f = { scripts = {}, text = "", name = name, shown = false }
  local mt = {}
  mt.__index = function(t, k)
    if k == "SetScript" then return function(self, ev, fn) self.scripts[ev] = fn end end
    if k == "GetScript" then return function(self, ev) return self.scripts[ev] end end
    if k == "SetText" then return function(self, v) self.text = v or "" end end
    if k == "GetText" then return function(self) return self.text end end
    if k == "Show" then return function(self) self.shown = true end end
    if k == "Hide" then return function(self) self.shown = false end end
    if k == "SetShown" then return function(self, v) self.shown = v and true or false end end
    if k == "IsShown" then return function(self) return self.shown end end
    if k == "AddMessage" then return function(self, v) self.lines = self.lines or {}; table.insert(self.lines, v) end end
    if k == "CreateFontString" or k == "CreateTexture" then return function() return newFrame() end end
    if type(k) == "string" and k:match("^[A-Z]") then return function() return newFrame() end end
    return rawget(t, k)
  end
  return setmetatable(f, mt)
end
local created = {}
function CreateFrame(kind, name, parent, tmpl)
  local f = newFrame(name); f.kind = kind; f.template = tmpl
  if name then _G[name] = f end
  table.insert(created, f)
  return f
end
UISpecialFrames = {}
function tinsert(t, v) table.insert(t, v) end
ACCEPT, CANCEL = "Accept", "Cancel"
ChatFontNormal = {}
StaticPopupDialogs = {}
POPUPS = {}
function StaticPopup_Show(which, text, _, data) table.insert(POPUPS, { which = which, text = text, data = data }) end
function ACCEPT_LAST_POPUP() local p = table.remove(POPUPS); StaticPopupDialogs[p.which].OnAccept(nil, p.data); return p.text end
CREATED = created
""")

lua.execute("NS = {}")
for fn in ("UISnapshot/UISnapshot.lua", "UISnapshot/UI.lua"):
    src = open(fn).read().replace("local ADDON, ns = ...", "local ADDON, ns = 'UISnapshot', NS")
    lua.execute(src)
run = lua.eval("function(m) SlashCmdList['UISNAPSHOT'](m) end")
for cmd in ["save main", "list", "show main", "diff main", "load main", "addons main", "editmode nonexist", "cvar", "cvar add foo", "bogus"]:
    printed.append(f">>> /uisnap {cmd}")
    try:
        run(cmd)
    except Exception as e:
        printed.append(f"LUA ERROR: {e}")
print("\n".join(printed))

ui_script = r"""
local out = {}
local function check(label, cond) table.insert(out, (cond and "PASS " or "FAIL ") .. label) end
SlashCmdList['UISNAPSHOT']("")                       -- opens the window
local f = UISnapshotFrame
check("window created and shown", f and f:IsShown())
check("escape-close registered", UISpecialFrames[1] == "UISnapshotFrame")
local A = NS.actions
-- Save with a typed name
f.nameBox:SetText("ui test"); A.save()
check("save via button stored profile", UISnapshotDB.profiles["ui test"] ~= nil)
check("save selected the new profile", NS.ui.selected == "ui test")
check("output went to the window log", NS.ui.log.lines and #NS.ui.log.lines > 0)
-- Save again over the same name: must ask first
local before = #POPUPS
A.save()
check("overwrite asks for confirmation", #POPUPS == before + 1)
POPUPS = {}
-- Buttons that need a selection
NS.ui.selected = nil
local n0 = #NS.ui.log.lines
A.load()
check("load with nothing selected only warns", #POPUPS == 0 and #NS.ui.log.lines == n0 + 1)
NS.ui.selected = "ui test"
A.diff(); A.show(); A.addons()
A.load()
check("load asks for confirmation", #POPUPS == 1)
ACCEPT_LAST_POPUP()
A.editmode()
check("edit mode copy box opened", UISnapshotCopyFrame and UISnapshotCopyFrame:IsShown())
-- CVar buttons
f.cvarBox:SetText("")
A.cvarAdd()
f.cvarBox:SetText("foo"); A.cvarAdd(); A.cvarList(); A.cvarRemove()
-- Delete with confirmation
A.delete()
check("delete asks for confirmation", #POPUPS == 1)
ACCEPT_LAST_POPUP()
check("delete removed profile", UISnapshotDB.profiles["ui test"] == nil)
check("selection cleared after delete", NS.ui.selected == nil)
-- toggle closes
SlashCmdList['UISNAPSHOT']("ui")
check("/uisnap ui toggles window closed", not f:IsShown())
-- text commands still print to chat when window closed
local p0 = #PRINTED
SlashCmdList['UISNAPSHOT']("list")
check("typed command prints to chat when window closed", #PRINTED > p0)
return table.concat(out, "\n")
"""
lua.execute("PRINTED = {}")
lua.globals().print = lambda *a: (printed.append(" ".join(str(x) for x in a)), lua.execute("table.insert(PRINTED, 1)"))
try:
    res = lua.execute(ui_script)
except Exception as e:
    res = "LUA ERROR in UI script: " + str(e)
print("\n--- UI window checks ---\n" + res)
if "FAIL" in res or "LUA ERROR" in res:
    sys.exit(1)
errs = [p for p in printed if "LUA ERROR" in p]
sys.exit(1 if errs else 0)
