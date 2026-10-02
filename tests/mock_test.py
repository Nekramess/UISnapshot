"""Smoke test: runs UISnapshot.lua under Lua 5.1 against a simulated WoW client.
This is NOT the live client; it only catches Lua errors and logic slips."""
import sys
from lupa.lua51 import LuaRuntime

lua = LuaRuntime(unpack_returned_tuples=True)
printed = []
lua.globals().print = lambda *a: printed.append(" ".join(str(x) for x in a))

lua.execute(r'''
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
C_Console = { GetAllCommands = function()
  local t = {}
  for n in pairs(CV) do table.insert(t, { command = n, commandType = 0 }) end
  table.insert(t, { command = "reloadui", commandType = 1 })      -- a command, not a CVar
  return t
end }
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
Minimap.GetCenter = function() return 1000, 500 end
Minimap.GetEffectiveScale = function() return 1 end
function FIRE(event) for _, f in ipairs(CREATED) do if f.scripts.OnEvent and f.registered and f.registered[event] then f.scripts.OnEvent(f, event) end end end
""")

lua.execute("NS = {}")
for fn in ("UISnapshot/Codec.lua", "UISnapshot/UISnapshot.lua", "UISnapshot/Minimap.lua", "UISnapshot/UI.lua"):
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

-- ===== export / import through the window =====
local f2 = UISnapshotFrame
SlashCmdList['UISNAPSHOT']("")                        -- open again (was toggled closed above)
f2.nameBox:SetText("Round Trip"); A.save()
local original = UISnapshotDB.profiles["Round Trip"]
NS.ui.selected = "Round Trip"
A.export()
local exported = UISnapshotCopyFrame and UISnapshotCopyFrame.edit and UISnapshotCopyFrame.edit:GetText()
check("export opened the copy box with text", type(exported) == "string" and exported:sub(1, 8) == "UISNAP1:")
check("export contains the profile name", exported and exported:find("Round Trip", 1, true) ~= nil)

-- wipe everything, then import into a "fresh install"
UISnapshotDB = {}
NS.ui.selected = nil
A.import()
local imp = UISnapshotImportFrame
check("import box opened", imp and imp:IsShown())
imp.edit:SetText(exported); imp.nameBox:SetText("")
POPUPS = {}
-- press the import box's own Import button (the last "Import" button created)
local importBtn
for _, fr in ipairs(CREATED) do
  if fr.kind == "Button" and fr.text == "Import" then importBtn = fr end
end
check("import box has its own Import button", importBtn ~= nil and importBtn.scripts.OnClick ~= nil)
importBtn.scripts.OnClick(importBtn)
local back = UISnapshotDB.profiles and UISnapshotDB.profiles["Round Trip"]
check("button imported the profile", back ~= nil)
check("box closed after import", not imp:IsShown())
check("imported profile is selected in the window", NS.ui.selected == "Round Trip")
back.importedOn = nil
check("imported profile equals the original", DEEPEQ_PROFILE(original, back))
check("box cleared after import", imp.edit:GetText() == "")
-- pressing Import with an empty box reports an error, no crash
local n0 = #NS.ui.log.lines
importBtn.scripts.OnClick(importBtn)
check("empty box reports in the log", #NS.ui.log.lines > n0)
-- pressing Import on an existing name asks before replacing
imp:Show(); imp.edit:SetText(exported)
POPUPS = {}
importBtn.scripts.OnClick(importBtn)
check("existing name triggers a replace confirmation", #POPUPS == 1)
ACCEPT_LAST_POPUP()
check("replace confirmed imports again", UISnapshotDB.profiles["Round Trip"] ~= nil and not imp:IsShown())

-- importing the same name again asks first
local r1, r2, r3 = NS.importString(exported, "", false)
check("existing name is not overwritten silently", r1 == false and r2 == "exists" and r3 == "Round Trip")
check("force replaces it", NS.importString(exported, "", true) == "Round Trip")
check("save-as renames", NS.importString(exported, "Other Name", false) == "Other Name" and UISnapshotDB.profiles["Other Name"] ~= nil)

-- bad input
local n1, e1 = NS.importString("garbage", "", false)
check("garbage import fails with a message", n1 == nil and type(e1) == "string")
local n2, e2 = NS.importString(exported:sub(1, #exported - 10), "", false)
check("truncated import fails with a message", n2 == nil and e2:find("cut off") ~= nil)
local n3, e3 = NS.importString("", "", false)
check("empty import fails with a message", n3 == nil and type(e3) == "string")

-- hostile profile: valid wrapper, bad contents
local evil = NS.codec.encode({ v = 1, name = "evil\nname\1", profile = {
  saved = string.rep("x", 5000),
  chat = { [1] = { name = "ok", fontSize = "huge", groups = { "SAY", 5, {}, string.rep("g", 500) } }, [2] = "notatable", [99] = { name = "far" } },
  cvars = { ["good_name"] = "1", ["bad name;rm"] = "1", ["x"] = { 1 }, ["long"] = string.rep("v", 500), ["num"] = 5 },
  addons = { "A", 5, string.rep("a", 500) },
  editMode = { layouts = { { name = "L", str = "abc" }, { name = 5, str = "x" }, "junk" } },
  unknownField = "should vanish", __index = "x",
}})
local en = NS.importString(evil, "", false)
local ep = en and UISnapshotDB.profiles[en]
check("hostile import is accepted but cleaned", ep ~= nil)
check("control characters stripped from name", en == "evilname")
check("long saved text rejected", ep and ep.saved == "?")
check("bad font size replaced with default", ep and ep.chat[1] and ep.chat[1].fontSize == 14)
check("only valid chat groups kept", ep and #ep.chat[1].groups == 1 and ep.chat[1].groups[1] == "SAY")
check("non-table and out-of-range chat entries dropped", ep and ep.chat[2] == nil and ep.chat[99] == nil)
check("only safe CVars kept", ep and ep.cvars.good_name == "1" and ep.cvars.num == "5"
      and ep.cvars["bad name;rm"] == nil and ep.cvars.x == nil and ep.cvars.long == nil)
check("only valid addons kept", ep and #ep.addons == 1)
check("only valid layouts kept", ep and #ep.editMode.layouts == 1)
check("unknown fields dropped", ep and ep.unknownField == nil)
-- newer export version refused
local newer = NS.codec.encode({ v = 99, name = "x", profile = {} })
local nn, ne = NS.importString(newer, "", false)
check("newer export version refused", nn == nil and ne:find("newer") ~= nil)
-- importing does not touch the tracked list
local trackedNow = {}
for _, c in ipairs(NS.db().cvars) do trackedNow[c] = true end
check("import does not add CVar names to the tracked list", not trackedNow.good_name and not trackedNow.gxResolution)

-- ===== 0.4.0: settings, reload, report, minimap, Edit Mode apply =====
local S = NS.db().settings
check("defaults: auto-reload on", S.autoReload == true)
check("no Edit Mode auto-apply setting exists", S.applyEditMode == nil and NS.applyEditMode == nil)
check("defaults: minimap button shown", S.minimap.hide == false)

-- a profile to load
UISnapshotDB.profiles = {}
f2.nameBox:SetText("Reload Test"); A.save()
NS.ui.selected = "Reload Test"
TIMERS = {}; RELOADS = 0; POPUPS = {}

-- Load with auto-reload on
A.load(); ACCEPT_LAST_POPUP()
check("load schedules a reload (not instant)", RELOADS == 0 and #TIMERS == 1 and TIMERS[1].sec == 1.5)
RUN_TIMERS()
check("reload happens after the delay", RELOADS == 1)
local pending = UISnapshotDB.pendingReport
check("report is stored for after the reload", pending and #pending.lines > 0)
-- "new session": fire login, run timers, report printed once
local printedBefore = #PRINTED
FIRE("PLAYER_LOGIN"); RUN_TIMERS()
check("report is shown after login", #PRINTED > printedBefore)
check("report is cleared once shown", UISnapshotDB.pendingReport == nil)
local p2 = #PRINTED; FIRE("PLAYER_LOGIN"); RUN_TIMERS()
check("report is not shown twice", #PRINTED == p2)

-- Auto-reload off
S.autoReload = false; RELOADS = 0; TIMERS = {}
A.load(); ACCEPT_LAST_POPUP(); RUN_TIMERS()
check("auto-reload off: no reload", RELOADS == 0)
check("auto-reload off: nothing stored", UISnapshotDB.pendingReport == nil)
local joined = table.concat(NS.ui.log.lines, "\n")
check("auto-reload off: tells the user to /reload", joined:find("/reload", 1, true) ~= nil)
S.autoReload = true

-- Reload blocked
RELOAD_FAILS = true; TIMERS = {}
A.load(); ACCEPT_LAST_POPUP(); RUN_TIMERS()
check("blocked reload falls back to a message", table.concat(NS.ui.log.lines, "\n"):find("type /reload", 1, true) ~= nil)
RELOAD_FAILS = false

-- Import via the box triggers a reload too
TIMERS = {}; RELOADS = 0
A.export()
local exp2 = UISnapshotCopyFrame.edit:GetText()
UISnapshotDB.profiles["Reload Test"] = nil
A.import()
UISnapshotImportFrame.edit:SetText(exp2)
local ib
for _, fr in ipairs(CREATED) do if fr.kind == "Button" and fr.text == "Import" then ib = fr end end
ib.scripts.OnClick(ib); RUN_TIMERS()
check("import schedules and runs a reload", RELOADS == 1)
-- failed import does not reload
TIMERS = {}; RELOADS = 0
UISnapshotImportFrame:Show(); UISnapshotImportFrame.edit:SetText("junk")
ib.scripts.OnClick(ib); RUN_TIMERS()
check("failed import does not reload", RELOADS == 0)

-- Enable addons also reloads
C_AddOns.GetAddOnEnableState = function(n, p) return 0 end
NS.ui.selected = "Reload Test"
UISnapshotDB.profiles["Reload Test"].addons = { "Details", "SpellCDTracker" }
local enabled = 0
C_AddOns.EnableAddOn = function() enabled = enabled + 1 end
TIMERS = {}; RELOADS = 0
A.addons(); RUN_TIMERS()
check("enable addons enabled the missing ones", enabled == 2)
check("enable addons reloads", RELOADS == 1)

-- Minimap
local px, py = NS.minimap.position(0, 80)
check("minimap position at 0 degrees", math.abs(px - 80) < 1e-9 and math.abs(py) < 1e-9)
px, py = NS.minimap.position(math.pi / 2, 80)
check("minimap position at 90 degrees", math.abs(px) < 1e-9 and math.abs(py - 80) < 1e-9)
check("angle to cursor (up)", math.abs(NS.minimap.angleTo(0, 0, 0, 5) - math.pi / 2) < 1e-9)
check("angle to cursor (left)", math.abs(NS.minimap.angleTo(0, 0, -5, 0) - math.pi) < 1e-9)
FIRE("PLAYER_LOGIN")
local mb = UISnapshotMinimapButton
check("minimap button created and shown", mb and mb:IsShown())
local pt = mb.lastPoint
check("button placed on the minimap edge", pt and pt[1] == "CENTER" and pt[2] == Minimap)
-- click toggles the window
local wasShown = UISnapshotFrame:IsShown()
mb.scripts.OnClick(mb, "LeftButton")
check("clicking the button toggles the window", UISnapshotFrame:IsShown() ~= wasShown)
mb.scripts.OnClick(mb, "LeftButton")
-- drag moves it and saves the angle
CURSOR = { 1000, 600 }                         -- straight up from the minimap centre (1000,500)
mb.scripts.OnDragStart(mb)
mb.scripts.OnUpdate(mb)
check("drag saves the new angle (90 degrees)", math.abs(NS.db().settings.minimap.angle - 90) < 1e-6)
check("click right after a drag is ignored", (function() local before = UISnapshotFrame:IsShown(); mb.scripts.OnClick(mb, "LeftButton"); return UISnapshotFrame:IsShown() == before end)())
mb.scripts.OnDragStop(mb); RUN_TIMERS()
-- hide / show via command and checkbox
SlashCmdList['UISNAPSHOT']("minimap off")
check("/uisnap minimap off hides and saves", not mb:IsShown() and NS.db().settings.minimap.hide == true)
SlashCmdList['UISNAPSHOT']("minimap on")
check("/uisnap minimap on shows again", mb:IsShown() and NS.db().settings.minimap.hide == false)
SlashCmdList['UISNAPSHOT']("minimap")
check("/uisnap minimap toggles", not mb:IsShown())
SlashCmdList['UISNAPSHOT']("minimap")
-- checkboxes in the window
local win = UISnapshotFrame
if not win:IsShown() then SlashCmdList['UISNAPSHOT']("") end
check("window has two setting checkboxes", #win.checks == 2)
local cbReload, cbMini = win.checks[1], win.checks[2]
check("checkboxes show saved state", cbReload.checked == true and cbMini.checked == true)
cbReload:SetChecked(false); cbReload.scripts.OnClick(cbReload)
check("reload checkbox saves", NS.db().settings.autoReload == false)
cbReload:SetChecked(true); cbReload.scripts.OnClick(cbReload)
cbMini:SetChecked(false); cbMini.scripts.OnClick(cbMini)
check("minimap checkbox hides the button", not mb:IsShown())
SlashCmdList['UISNAPSHOT']("minimap on")
check("checkbox state follows the command", cbMini.checked == true)


-- ===== 0.5.0: game settings (all changed CVars) and action bars =====
if not UISnapshotFrame:IsShown() then SlashCmdList['UISNAPSHOT']("") end
local function text() return table.concat(NS.ui.log.lines, "\n") end
local function resetLog() NS.ui.log.lines = {} end
local function reset(n) for k in pairs(n) do n[k] = nil end end

-- tracked list is what the user chose on top of "everything changed"
local tr = NS.db().cvars
check("tracked list still has the defaults", #tr >= 7)

resetLog()
NS.commands.save("Settings")
local P = UISnapshotDB.profiles["Settings"]
check("captures non-default CVars", P.cvars.autoLootDefault == "1" and P.cvars.nameplateShowEnemies == "1"
      and P.cvars.alwaysShowActionBars == "1" and P.cvars.cameraDistanceMaxZoomFactor == "2.6" and P.cvars.Sound_MasterVolume == "0.4")
check("captures uiScale and useUiScale", P.cvars.uiScale == "0.64" and P.cvars.useUiScale == "1")
check("tracked CVars are included even when at default", P.cvars.chatMouseScroll == "1" and P.cvars.whisperMode == "inline")
check("untracked default-valued CVars are left out", P.cvars.floatingCombatTextCombatDamage == nil)
for _, n in ipairs({ "gxWindow", "gxResolution", "gxMaximize", "lastCharacterIndex", "Sound_OutputDriverName", "locale", "textLocale", "accountName", "portal", "realmName" }) do
  check("never captures machine/session setting " .. n, P.cvars[n] == nil)
end
check("skips locked and read-only CVars", P.cvars.lockedThing == nil and P.cvars.readonlyThing == nil)
check("console commands are not mistaken for CVars", P.cvars.reloadui == nil)
check("records how settings were gathered", P.cvarInfo and P.cvarInfo.mode == "all changed from default" and P.cvarInfo.scanned > 10)
check("captures action bar toggles", P.actionBars and P.actionBars.bars[1] == false and P.actionBars.bars[2] == true
      and P.actionBars.bars[3] == true and P.actionBars.bars[4] == false and #P.actionBars.bars == 7)
check("captures always-show value", P.actionBars.alwaysShow == "1")
check("save message reports the CVar count and action bars", text():find("changed from default", 1, true) ~= nil and text():find("Action Bar 3, 4", 1, true) ~= nil)

-- show / cvars / bars commands
resetLog(); NS.commands.show("Settings")
check("show reports the settings mode and action bars", text():find("all changed from default", 1, true) ~= nil and text():find("Action Bar 3, 4", 1, true) ~= nil)
UISnapshotCopyFrame:Hide()
NS.commands.cvars("Settings")
local listing = UISnapshotCopyFrame.edit:GetText()
check("cvars command lists saved settings", UISnapshotCopyFrame:IsShown() and listing:find("autoLootDefault = 1", 1, true) ~= nil)
check("cvars listing has no machine-specific settings", listing:find("gxResolution", 1, true) == nil and listing:find("accountName", 1, true) == nil)
resetLog(); NS.commands.bars()
check("bars command prints the toggles", text():find("GetActionBarToggles: false, true, true, false", 1, true) ~= nil)

-- diff before changing anything: all match
resetLog(); NS.commands.diff("Settings")
check("diff: unchanged settings match", text():find("saved settings match", 1, true) ~= nil and text():find("Action bars: match", 1, true) ~= nil)

-- change things like a fresh install would look
CV.autoLootDefault[1] = "0"; CV.nameplateShowEnemies[1] = "0"; CV.Sound_MasterVolume[1] = "1"
CV.uiScale[1] = "1"; CV.useUiScale[1] = "0"; CV.refusesToSet[1] = "6"
CV.gxResolution[1] = "1920x1080"; CV.locale[1] = "frFR"; CV.accountName[1] = "OTHER"
BARS = { false, false, false, false, false, false, false }
resetLog(); NS.commands.diff("Settings")
check("diff lists changed settings with now/saved", text():find("autoLootDefault: now 0, saved 1", 1, true) ~= nil)
check("diff reports the changed count", text():find("saved settings differ from now", 1, true) ~= nil)
check("diff shows the action bar change", text():find("Action bars: now none of bars 2-8, saved Action Bar 3, 4", 1, true) ~= nil)
check("diff ignores machine-specific settings", text():find("gxResolution", 1, true) == nil)

-- load restores them
reset(SETS); BAR_SET_CALLS = {}
resetLog(); TIMERS = {}
NS.commands.load("Settings")
check("load restored the CVars", CV.autoLootDefault[1] == "1" and CV.nameplateShowEnemies[1] == "1" and CV.Sound_MasterVolume[1] == "0.4")
check("load restored uiScale", CV.uiScale[1] == "0.64" and CV.useUiScale[1] == "1")
local posUse, posScale
for i, n in ipairs(SETS) do if n == "useUiScale" then posUse = i elseif n == "uiScale" then posScale = i end end
check("useUiScale is set before uiScale", posUse and posScale and posUse < posScale)
local setList = table.concat(SETS, ",")
check("settings that already matched are not set again", not setList:find("chatStyle", 1, true) and not setList:find("whisperMode", 1, true))
check("machine-specific settings were not touched", CV.gxResolution[1] == "1920x1080" and CV.locale[1] == "frFR" and CV.accountName[1] == "OTHER")
check("action bars were set once, with the saved states", #BAR_SET_CALLS == 1 and BAR_SET_CALLS[1][1] == false and BAR_SET_CALLS[1][2] == true
      and BAR_SET_CALLS[1][3] == true and BAR_SET_CALLS[1][4] == false)
check("always-show value is passed along", BAR_SET_CALLS[1][8] == "1")
check("load says the action bars show after the reload", text():find("Action bars set to: Action Bar 3, 4 (shows after the reload)", 1, true) ~= nil)
check("load names the CVar that could not be set", text():find("Could not set: refusesToSet", 1, true) ~= nil)
check("load reports changed/matched/failed counts", text():find("CVars changed", 1, true) ~= nil and text():find("already matched", 1, true) ~= nil and text():find("1 could not be set", 1, true) ~= nil)
check("load still schedules the reload", #TIMERS >= 1)

-- imported profile cannot set denied CVars
local hostile = NS.codec.encode({ v = 1, name = "sneaky", profile = { cvars = { gxResolution = "640x480", locale = "xxXX", accountName = "EVIL", autoLootDefault = "0" } } })
local hn = NS.importString(hostile, "", true)
CV.autoLootDefault[1] = "1"; CV.gxResolution[1] = "1920x1080"; CV.locale[1] = "frFR"; CV.accountName[1] = "OTHER"
resetLog(); NS.commands.load(hn)
check("imported profile can set normal CVars", CV.autoLootDefault[1] == "0")
check("imported profile cannot set denied CVars", CV.gxResolution[1] == "1920x1080" and CV.locale[1] == "frFR" and CV.accountName[1] == "OTHER")

-- diff caps its output
local many = {}
for i = 1, 30 do many["fake" .. i] = tostring(i) end
local big = NS.importString(NS.codec.encode({ v = 1, name = "many", profile = { cvars = many } }), "", true)
resetLog(); NS.commands.diff(big)
check("diff caps long lists", text():find("30 of 30 saved settings differ", 1, true) ~= nil and text():find("...and 5 more.", 1, true) ~= nil)

-- sanitizing the new fields
local odd = NS.importString(NS.codec.encode({ v = 1, name = "odd", profile = {
  actionBars = { bars = { 1, "x", true, nil, false }, alwaysShow = { 1 } }, cvarInfo = { mode = string.rep("m", 500), scanned = "many" } } }), "", true)
local op = UISnapshotDB.profiles[odd]
check("action bars sanitized to 7 booleans", op.actionBars and #op.actionBars.bars == 7 and op.actionBars.bars[1] == true and op.actionBars.bars[4] == false)
check("bad always-show value dropped", op.actionBars.alwaysShow == nil)
check("cvarInfo sanitized", op.cvarInfo.mode == "?" and op.cvarInfo.scanned == 0)

-- export/import keeps the new fields
NS.ui.selected = "Settings"
UISnapshotCopyFrame:Hide(); UISnapshotDB.profiles["Settings"].importedOn = nil
local before = UISnapshotDB.profiles["Settings"]
NS.commands.export("Settings")
local ex = UISnapshotCopyFrame.edit:GetText()
local rt = NS.importString(ex, "Settings copy", true)
local rp = UISnapshotDB.profiles[rt]; rp.importedOn = nil
check("export/import keeps CVars, action bars and cvarInfo", DEEPEQ_PROFILE(before.cvars, rp.cvars) and DEEPEQ_PROFILE(before.actionBars, rp.actionBars) and DEEPEQ_PROFILE(before.cvarInfo, rp.cvarInfo))

-- fallbacks when the list-all call is missing
local savedConsole = C_Console
C_Console = nil
resetLog(); NS.commands.save("Tracked only")
local T = UISnapshotDB.profiles["Tracked only"]
check("without C_Console only tracked CVars are saved", T.cvarInfo.mode == "tracked list only" and T.cvars.autoLootDefault == nil and T.cvars.chatStyle ~= nil)
check("fallback says so", text():find("only the", 1, true) ~= nil and text():find("not available here", 1, true) ~= nil)
C_Console = savedConsole
local savedInfo = C_CVar.GetCVarInfo
C_CVar.GetCVarInfo = nil
NS.commands.save("No info")
check("without GetCVarInfo only tracked CVars are saved", UISnapshotDB.profiles["No info"].cvarInfo.mode == "tracked list only")
C_CVar.GetCVarInfo = savedInfo

-- fallbacks when the action bar API is missing
local g, s2 = GetActionBarToggles, SetActionBarToggles
GetActionBarToggles = nil
NS.commands.save("No bars")
check("no GetActionBarToggles: profile has no action bars, no crash", UISnapshotDB.profiles["No bars"].actionBars == nil)
GetActionBarToggles = g
SetActionBarToggles = nil
resetLog(); NS.commands.load("Settings")
check("no SetActionBarToggles: says so, still applies CVars", text():find("Could not set the action bars", 1, true) ~= nil)
SetActionBarToggles = s2
resetLog(); NS.commands.load("No bars")
check("profile without action bars loads fine", text():find("Applied 'No bars'", 1, true) ~= nil and text():find("Action bars set", 1, true) == nil)

return table.concat(out, "\n")
"""
lua.execute("""
function DEEPEQ_PROFILE(a, b)
  if type(a) ~= type(b) then return false end
  if type(a) ~= "table" then return a == b end
  for k, v in pairs(a) do if not DEEPEQ_PROFILE(v, b[k]) then return false end end
  for k in pairs(b) do if a[k] == nil then return false end end
  return true
end
""")
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
