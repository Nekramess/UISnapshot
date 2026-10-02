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
UIParent = { GetScale = function() return 0.64 end }
GetScreenWidth = function() return 5120 end GetScreenHeight = function() return 1440 end
date = os.date
SlashCmdList = {}
''')

lua.execute(open("UISnapshot/UISnapshot.lua").read().replace("local ADDON, ns = ...", "local ADDON, ns = 'UISnapshot', {}"))
run = lua.eval("function(m) SlashCmdList['UISNAPSHOT'](m) end")
for cmd in ["save main", "list", "show main", "diff main", "load main", "addons main", "editmode nonexist", "cvar", "cvar add foo", "bogus"]:
    printed.append(f">>> /uisnap {cmd}")
    try:
        run(cmd)
    except Exception as e:
        printed.append(f"LUA ERROR: {e}")
print("\n".join(printed))
errs = [p for p in printed if "LUA ERROR" in p]
sys.exit(1 if errs else 0)
