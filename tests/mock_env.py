"""Shared simulated WoW client for the tests (Lua 5.1 via lupa). Not the live client.
Frames made by CreateFrame start SHOWN, like the real client."""
from lupa.lua51 import LuaRuntime

FILES = ("UISnapshot/Codec.lua", "UISnapshot/UISnapshot.lua", "UISnapshot/Minimap.lua", "UISnapshot/UI.lua")

MOCK_CLIENT = r'''
NUM_CHAT_WINDOWS = 3
-- name = { value, default, locked?, readonly? }
CV = {
  uiScale = { "0.64", "1" }, useUiScale = { "1", "0" }, chatStyle = { "classic", "im" },
  chatClassColorOverride = { "0", "0" }, whisperMode = { "inline", "inline" }, chatMouseScroll = { "1", "1" }, showTutorials = { "0", "1" },
  autoLootDefault = { "1", "0" }, nameplateShowEnemies = { "1", "0" }, floatingCombatTextCombatDamage = { "1", "1" },
  alwaysShowActionBars = { "1", "0" }, cameraDistanceMaxZoomFactor = { "2.6", "1.9" }, Sound_MasterVolume = { "0.4", "1" },
  -- machine- or session-specific: must never be captured or applied
  gxWindow = { "1", "1" }, gxResolution = { "3840x1080", "1024x768" }, gxMaximize = { "0", "1" },
  lastCharacterIndex = { "3", "0" }, Sound_OutputDriverName = { "Speakers", "" }, locale = { "enUS", "enUS" },
  textLocale = { "deDE", "enUS" }, accountName = { "ANTHONY", "" }, portal = { "US", "US" }, realmName = { "Test", "" },
  -- cannot be changed by the user
  lockedThing = { "9", "1", true, false }, readonlyThing = { "9", "1", false, true },
  -- cannot be set (SetCVar refuses)
  refusesToSet = { "5", "1" },
}
SETS = {}
function GetCVar(n) return CV[n] and CV[n][1] or nil end
C_CVar = {
  SetCVar = function(n, v)
    if n == "refusesToSet" then return false end
    if not CV[n] then error("unknown cvar " .. tostring(n)) end
    CV[n][1] = v; table.insert(SETS, n); return true
  end,
  GetCVarInfo = function(n)
    local e = CV[n]; if not e then return nil end
    return e[1], e[2], false, false, e[3] or false, false, e[4] or false
  end,
}
-- Forever has the global ConsoleGetAllCommands and NO C_Console namespace (checked in the
-- 1.60.1 UI source), so the mock is Forever-like. Retail-like is tested separately.
function ConsoleGetAllCommands()
  local t = {}
  for n in pairs(CV) do table.insert(t, { command = n, commandType = 0 }) end
  table.insert(t, { command = "reloadui", commandType = 1 })      -- a command, not a CVar
  return t
end
Enum = { ConsoleCommandType = { Cvar = 0, Command = 1 } }
BARS = { false, true, true, false, false, false, false }
ALWAYS_SHOW_MULTIBARS = "1"
BAR_SET_CALLS = {}
function GetActionBarToggles() return unpack(BARS) end
function SetActionBarToggles(...) table.insert(BAR_SET_CALLS, { ... }) end
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
'''

MOCK_FRAMES = r"""
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
    if k == "RegisterEvent" then return function(self, e) self.registered = self.registered or {}; self.registered[e] = true end end
    if k == "Show" then return function(self) self.shown = true end end
    if k == "Hide" then return function(self) self.shown = false end end
    if k == "SetShown" then return function(self, v) self.shown = v and true or false end end
    if k == "IsShown" then return function(self) return self.shown end end
    if k == "SetPoint" then return function(self, ...) self.lastPoint = { ... } end end
    if k == "ClearAllPoints" then return function(self) self.lastPoint = nil end end
    if k == "SetChecked" then return function(self, v) self.checked = v and true or false end end
    if k == "GetChecked" then return function(self) return self.checked end end
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
  f.shown = true   -- the real client shows frames on creation
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
RELOADS = 0
RELOAD_FAILS = false
function ReloadUI() if RELOAD_FAILS then error("blocked") end RELOADS = RELOADS + 1 end
TIMERS = {}
C_Timer = { After = function(sec, fn) table.insert(TIMERS, { sec = sec, fn = fn }) end }
function RUN_TIMERS() local t = TIMERS; TIMERS = {}; for _, x in ipairs(t) do x.fn() end end
GameTooltip = newFrame("GameTooltip")
CURSOR = { 0, 0 }
function GetCursorPosition() return CURSOR[1], CURSOR[2] end
Minimap = CreateFrame("Frame", "Minimap")
Minimap.GetWidth = function() return 140 end
Minimap.GetHeight = function() return 140 end
Minimap.GetCenter = function() return 1000, 500 end
Minimap.GetEffectiveScale = function() return 1 end
function FIRE(event) for _, f in ipairs(CREATED) do if f.scripts.OnEvent and f.registered and f.registered[event] then f.scripts.OnEvent(f, event) end end end
"""


def make_runtime():
    lua = LuaRuntime(unpack_returned_tuples=True)
    printed = []
    lua.globals().print = lambda *a: printed.append(" ".join(str(x) for x in a))
    lua.execute(MOCK_CLIENT)
    lua.execute(MOCK_FRAMES)
    lua.execute("NS = {}")
    for fn in FILES:
        src = open(fn).read().replace("local ADDON, ns = ...", "local ADDON, ns = 'UISnapshot', NS")
        lua.execute(src)
    return lua, printed
