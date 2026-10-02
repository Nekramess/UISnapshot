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
for fn in ("UISnapshot/Codec.lua", "UISnapshot/UISnapshot.lua", "UISnapshot/EditModeApply.lua", "UISnapshot/Minimap.lua", "UISnapshot/UI.lua"):
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
-- imported CVar names join the tracked list
local tracked = {}
for _, c in ipairs(NS.db().cvars) do tracked[c] = true end
check("imported CVar names are tracked for future saves", tracked.good_name)

-- ===== 0.4.0: settings, reload, report, minimap, Edit Mode apply =====
local S = NS.db().settings
check("defaults: auto-reload on", S.autoReload == true)
check("defaults: Edit Mode apply off", S.applyEditMode == false)
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
check("window has three setting checkboxes", #win.checks == 3)
local cbReload, cbEM, cbMini = win.checks[1], win.checks[2], win.checks[3]
check("checkboxes show saved state", cbReload.checked == true and cbEM.checked == false and cbMini.checked == true)
cbReload:SetChecked(false); cbReload.scripts.OnClick(cbReload)
check("reload checkbox saves", NS.db().settings.autoReload == false)
cbReload:SetChecked(true); cbReload.scripts.OnClick(cbReload)
cbEM:SetChecked(true); cbEM.scripts.OnClick(cbEM)
check("Edit Mode checkbox saves", NS.db().settings.applyEditMode == true)
cbEM:SetChecked(false); cbEM.scripts.OnClick(cbEM)
cbMini:SetChecked(false); cbMini.scripts.OnClick(cbMini)
check("minimap checkbox hides the button", not mb:IsShown())
SlashCmdList['UISNAPSHOT']("minimap on")
check("checkbox state follows the command", cbMini.checked == true)

-- ===== Edit Mode apply =====
-- Fake API with 2 preset layouts in front of the custom ones for SetActiveLayout numbering
local PRESETS = 2
local function lay(name, ty) return { layoutName = name, layoutType = ty, systems = {} } end
local store, activeName, saves, setActiveCalls, saveShouldFail
local function resetEM(customLayouts, active)
  store = customLayouts
  activeName = active
  saves, setActiveCalls, saveShouldFail = 0, {}, false
  C_EditMode = {
    GetLayouts = function()
      local idx
      for i, l in ipairs(store) do if l.layoutName == activeName then idx = i + PRESETS end end
      local copy = {}
      for i, l in ipairs(store) do copy[i] = l end
      return { layouts = copy, activeLayout = idx or 1 }
    end,
    SaveLayouts = function(info)
      if saveShouldFail then error("AllowedWhenUntainted: blocked") end
      saves = saves + 1; store = info.layouts
    end,
    SetActiveLayout = function(i) table.insert(setActiveCalls, i)
      local custom = i - PRESETS
      if store[custom] then activeName = store[custom].layoutName end
    end,
    ConvertLayoutInfoToString = function(l) return "EXPORT:" .. l.layoutName end,
    ConvertStringToLayoutInfo = function(s) if s:sub(1, 2) == "OK" then return { systems = {}, from = s } end return nil end,
  }
  EditModeManagerFrame = { IsShown = function() return false end,
    GetActiveLayoutInfo = function() return { layoutName = activeName } end }
  Constants = nil
end
local function profileWith(layouts, active)
  return { editMode = { layouts = layouts, active = active } }
end
local function lines() return table.concat(NS.ui.log.lines, "\n") end

-- normal case: A,B exist; C,D are new; C was active
resetEM({ lay("A", 1), lay("B", 2) }, "A")
UISnapshotDB.editModeBackups = nil
NS.ui.log.lines = {}
local rep = NS.applyEditMode(profileWith({
  { name = "A", str = "OK a", layoutType = 1 }, { name = "B", str = "OK b", layoutType = 2 },
  { name = "C", str = "OK c", layoutType = 1 }, { name = "D", str = "OK d", layoutType = 2 } }, "C"))
check("EM: added the two new layouts", #rep.added == 2 and rep.added[1] == "C" and rep.added[2] == "D")
check("EM: existing layouts skipped, not overwritten", #rep.skipped == 2)
check("EM: saved exactly once", saves == 1)
check("EM: store has 4 layouts, originals first and untouched", #store == 4 and store[1].layoutName == "A" and store[2].layoutName == "B")
check("EM: new layouts got names and types", store[3].layoutName == "C" and store[3].layoutType == 1 and store[4].layoutName == "D" and store[4].layoutType == 2)
check("EM: backup of the 2 old layouts was made", UISnapshotDB.editModeBackups and #UISnapshotDB.editModeBackups[1].layouts == 2 and UISnapshotDB.editModeBackups[1].layouts[1].str == "EXPORT:A")
check("EM: activation index includes the preset offset (3 + 2 = 5)", #setActiveCalls == 1 and setActiveCalls[1] == 5)
check("EM: reports the activated layout", rep.activated == "C")

-- already active
resetEM({ lay("A", 1) }, "A")
rep = NS.applyEditMode(profileWith({ { name = "A", str = "OK a" } }, "A"))
check("EM: nothing to add, no save", saves == 0 and #rep.added == 0)
check("EM: already-active layout is not re-activated", #setActiveCalls == 0 and rep.activateNote and rep.activateNote:find("already") ~= nil)

-- string not accepted
resetEM({ lay("A", 1) }, "A")
rep = NS.applyEditMode(profileWith({ { name = "X", str = "BAD", layoutType = 1 } }, nil))
check("EM: unaccepted string reported, nothing saved", #rep.failed == 1 and saves == 0)

-- save refused (tainted/blocked)
resetEM({ lay("A", 1) }, "A")
saveShouldFail = true
rep = NS.applyEditMode(profileWith({ { name = "C", str = "OK c", layoutType = 1 } }, "C"))
check("EM: refused save is reported", rep.error ~= nil and rep.error:find("nothing was changed", 1, true) ~= nil)
check("EM: refused save adds nothing and does not activate", #rep.added == 0 and #setActiveCalls == 0 and #store == 1)
check("EM: refusal points to the manual route", rep.error:find("/uisnap editmode", 1, true) ~= nil)

-- combat and Edit Mode open
resetEM({ lay("A", 1) }, "A")
InCombatLockdown = function() return true end
UISnapshotDB.editModeBackups = nil
rep = NS.applyEditMode(profileWith({ { name = "C", str = "OK c" } }, "C"))
check("EM: refuses in combat, no backup, no save", rep.error ~= nil and saves == 0 and UISnapshotDB.editModeBackups == nil)
InCombatLockdown = function() return false end
EditModeManagerFrame.IsShown = function() return true end
rep = NS.applyEditMode(profileWith({ { name = "C", str = "OK c" } }, "C"))
check("EM: refuses while Edit Mode is open", rep.error ~= nil and rep.error:find("close Edit Mode", 1, true) ~= nil and saves == 0)
EditModeManagerFrame.IsShown = function() return false end

-- API missing
resetEM({ lay("A", 1) }, "A")
C_EditMode.ConvertStringToLayoutInfo = nil
rep = NS.applyEditMode(profileWith({ { name = "C", str = "OK c" } }, "C"))
check("EM: missing API is handled", rep.error ~= nil and saves == 0)

-- no layouts in the profile
rep = NS.applyEditMode(profileWith({}, nil))
check("EM: profile without layouts is handled", rep.error ~= nil)

-- cap per type
resetEM({ lay("A", 1), lay("B", 2) }, "A")
Constants = { EditModeConsts = { EditModeMaxLayoutsPerType = 1 } }
rep = NS.applyEditMode(profileWith({ { name = "C", str = "OK c", layoutType = 1 }, { name = "D", str = "OK d", layoutType = 2 } }, nil))
check("EM: per-type cap respected", #rep.added == 0 and #rep.skipped == 2 and saves == 0)
Constants = nil

-- active layout is a preset: numbering unknown, so do not guess
resetEM({ lay("A", 1) }, "Modern")
rep = NS.applyEditMode(profileWith({ { name = "C", str = "OK c", layoutType = 1 } }, "C"))
check("EM: preset-active numbering is not guessed", #setActiveCalls == 0 and rep.activateNote ~= nil and #rep.added == 1)

-- target missing
resetEM({ lay("A", 1) }, "A")
rep = NS.applyEditMode(profileWith({ { name = "C", str = "OK c", layoutType = 1 } }, "Zed"))
check("EM: unknown target layout is reported", #setActiveCalls == 0 and rep.activateNote ~= nil and rep.activateNote:find("Zed", 1, true) ~= nil)

-- backups keep only the newest 3
resetEM({ lay("A", 1) }, "A")
UISnapshotDB.editModeBackups = nil
for i = 1, 5 do NS.applyEditMode(profileWith({ { name = "N" .. i, str = "OK" } }, nil)) end
check("EM: only 3 backups kept, newest first", #UISnapshotDB.editModeBackups == 3)
NS.commands.backups()
check("backups command lists them", lines():find("Backup 1", 1, true) ~= nil)
UISnapshotCopyFrame:Hide()
NS.commands.backup("1")
check("backup command opens the strings", UISnapshotCopyFrame:IsShown() and UISnapshotCopyFrame.edit:GetText():find("EXPORT:", 1, true) ~= nil)

-- Load honours the setting
resetEM({ lay("A", 1) }, "A")
UISnapshotDB.profiles["EM Test"] = { saved = "x", character = "x", chat = {}, cvars = {}, addons = {},
  editMode = { layouts = { { name = "Z", str = "OK z", layoutType = 1 } }, active = "Z" } }
NS.ui.selected = "EM Test"
NS.db().settings.applyEditMode = false
NS.commands.load("EM Test")
check("Load does not touch Edit Mode when the setting is off", saves == 0)
NS.db().settings.applyEditMode = true
NS.commands.load("EM Test")
check("Load applies Edit Mode when the setting is on", saves == 1 and #store == 2)
NS.db().settings.applyEditMode = false

-- the window button asks first
POPUPS = {}; saves = 0; resetEM({ lay("A", 1) }, "A")
A.applyEditMode()
check("Apply Edit Mode button asks for confirmation", #POPUPS == 1)
ACCEPT_LAST_POPUP()
check("Apply Edit Mode button applies after confirm", saves == 1)

-- layoutType survives export/import and is validated
local lt = NS.codec.encode({ v = 1, name = "LT", profile = { editMode = { layouts = {
  { name = "one", str = "s", layoutType = 2 }, { name = "two", str = "s", layoutType = 7 }, { name = "three", str = "s" } } } } })
local ltn = NS.importString(lt, "", true)
local ll = UISnapshotDB.profiles[ltn].editMode.layouts
check("layoutType 2 kept, invalid or missing become 1", ll[1].layoutType == 2 and ll[2].layoutType == 1 and ll[3].layoutType == 1)

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
