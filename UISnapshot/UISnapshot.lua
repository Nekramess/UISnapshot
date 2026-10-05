-- UI Snapshot 0.6.3
-- Saves chat windows, selected CVars, Edit Mode layouts and the enabled-addon
-- list under a name, and re-applies them later (e.g. on a fresh install).
--
-- STATUS: written against the Mainline API as documented on the Warcraft Wiki.
-- Only these were confirmed in the Forever beta (user screenshot, 1 Oct 2026):
--   C_EditMode exists, C_EditMode.GetLayouts() exists, GetChatWindowInfo(1)
--   returns 10 values. Everything else is UNTESTED in the live client; every
--   client call is wrapped in pcall so one failure cannot abort a save or load.

local ADDON, ns = ...
UISnapshotDB = UISnapshotDB or {}
local ui = {}   -- window state, filled in by UI.lua
ns.ui = ui

local DB_VERSION = 1
local DEFAULT_CVARS = {
    "useUiScale", "uiScale", "chatStyle", "chatClassColorOverride",
    "whisperMode", "chatMouseScroll", "showTutorials",
}

-- Messages go to the window's log while it is open, otherwise to chat.
local captured   -- while a Load/Import runs, its messages are also kept here
local function say(msg)
    local text = "|cff33ccffUI Snapshot:|r " .. tostring(msg)
    if captured then captured[#captured + 1] = text end
    if ui.frame and ui.frame:IsShown() and ui.log then
        ui.log:AddMessage(text)
    else
        print(text)
    end
end
ns.say = say
function ns.beginCapture() captured = {} end
function ns.endCapture() local c = captured or {}; captured = nil; return c end

local function db()
    local d = UISnapshotDB
    d.version = d.version or DB_VERSION
    d.profiles = d.profiles or {}
    d.cvars = d.cvars or {}
    d.settings = d.settings or {}
    if d.settings.autoReload == nil then d.settings.autoReload = true end
    d.settings.minimap = d.settings.minimap or { hide = false, angle = 215 }
    if #d.cvars == 0 then
        for _, name in ipairs(DEFAULT_CVARS) do d.cvars[#d.cvars + 1] = name end
    end
    return d
end

ns.db = db

local function count(t)
    local n = 0
    for _ in pairs(t or {}) do n = n + 1 end
    return n
end

-- Run fn; return its first result, or nil plus the error text.
local function try(fn, ...)
    local ok, a = pcall(fn, ...)
    if ok then return a end
    return nil, a
end

---------------------------------------------------------------------------
-- Capture
---------------------------------------------------------------------------

local function captureChat()
    local out = {}
    local n = NUM_CHAT_WINDOWS or 10
    for i = 1, n do
        local name, fontSize, r, g, b, alpha, shown, locked, docked, uninteractable =
            GetChatWindowInfo(i)
        if name then
            local w = {
                name = name, fontSize = fontSize, r = r, g = g, b = b, alpha = alpha,
                shown = shown and true or false, locked = locked and true or false,
                docked = docked, uninteractable = uninteractable and true or false,
            }
            local frame = _G["ChatFrame" .. i]
            if frame then
                w.width, w.height = frame:GetSize()
                local point, _, relPoint, x, y = frame:GetPoint(1)
                if point then
                    w.point, w.relPoint, w.x, w.y = point, relPoint, x, y
                end
            end
            local groups = { GetChatWindowMessages(i) }
            w.groups = groups
            local chans = { GetChatWindowChannels(i) }
            w.channels = {}
            for k = 1, #chans, 2 do
                if chans[k] then w.channels[#w.channels + 1] = chans[k] end
            end
            out[i] = w
        end
    end
    return out
end

---------------------------------------------------------------------------
-- Game settings (CVars) and action bar toggles
---------------------------------------------------------------------------

-- Settings that belong to this computer or this session rather than to a UI.
-- They are never captured and never applied, even from an imported profile.
local DENY_PREFIXES = { "gx", "last", "sound_output", "videooptions", "hwdetect", "installtype",
    "locale", "textlocale", "audiolocale", "accountname", "portal", "realm", "wowversion" }

local function isDenied(name)
    local l = tostring(name):lower()
    for _, pre in ipairs(DENY_PREFIXES) do
        if l:sub(1, #pre) == pre then return true end
    end
    return false
end
ns.isDeniedCVar = isDenied

local function cvarInfoFn()
    return (C_CVar and C_CVar.GetCVarInfo) or _G.GetCVarInfo
end

-- value, default, lockedFromUser, readOnly
local function cvarInfo(name)
    local f = cvarInfoFn()
    if not f then return nil end
    local ok, v, d, _, _, locked, _, ro = pcall(f, name)
    if not ok then return nil end
    return v, d, locked, ro
end

-- Forever (1.60.1 UI source) has the global ConsoleGetAllCommands() and no C_Console
-- namespace; retail has C_Console.GetAllCommands. Try both.
local function allCommands()
    local get = (C_Console and C_Console.GetAllCommands) or _G.ConsoleGetAllCommands
    if not get then return nil, "neither ConsoleGetAllCommands nor C_Console.GetAllCommands exists" end
    local ok, cmds = pcall(get)
    if not ok then return nil, "the call failed: " .. tostring(cmds) end
    if type(cmds) ~= "table" then return nil, "the call returned " .. type(cmds) end
    return cmds
end

local function cvarType()
    return (Enum and Enum.ConsoleCommandType and Enum.ConsoleCommandType.Cvar) or 0
end

local function allCVarNames()
    local cmds = allCommands()
    if not cmds then return nil end
    local ct = cvarType()
    local names = {}
    for _, c in ipairs(cmds) do
        if c.commandType == ct and type(c.command) == "string" then names[#names + 1] = c.command end
    end
    return names
end

-- Settings whose CVar names come from Forever's own Options source (Advanced Options:
-- Cooldown Manager, Swing Timer, Damage Meter). Always saved, even when the full CVar
-- list cannot be read and even when the value equals its default.
local ALWAYS_CAPTURE = { "damageMeterEnabled", "damageMeterResetOnNewInstance", "showSwingTimer", "cooldownViewerEnabled" }

-- Every CVar that differs from its default (minus the deny list), plus the tracked list.
-- Returns the table and a small summary of how it was gathered.
local function captureCVars()
    local out, info = {}, { mode = "tracked list only", scanned = 0 }
    local names = allCVarNames()
    if names and cvarInfoFn() then
        info.mode = "all changed from default"
        for _, name in ipairs(names) do
            if not isDenied(name) then
                info.scanned = info.scanned + 1
                local v, d, locked, ro = cvarInfo(name)
                if v ~= nil and d ~= nil and v ~= d and not locked and not ro then out[name] = v end
            end
        end
    end
    for _, name in ipairs(ALWAYS_CAPTURE) do
        local v = GetCVar(name)
        if v ~= nil then out[name] = v end
    end
    for _, name in ipairs(db().cvars) do
        local v = GetCVar(name)
        if v ~= nil and not isDenied(name) then out[name] = v end
    end
    return out, info
end

-- Action bars 2-8 on/off. bars[1] is "Action Bar 2" ... bars[7] is "Action Bar 8"
-- (naming follows the wiki's description of GetActionBarToggles).
local function captureActionBars()
    if not GetActionBarToggles then return nil end
    local t = { pcall(GetActionBarToggles) }
    if not t[1] then return nil end
    local bars = {}
    for i = 2, math.min(#t, 8) do bars[i - 1] = t[i] and true or false end
    return { bars = bars, alwaysShow = _G.ALWAYS_SHOW_MULTIBARS }
end

local function barsText(ab)
    if not (ab and ab.bars) then return "not captured" end
    local on = {}
    for i, v in ipairs(ab.bars) do if v then on[#on + 1] = tostring(i + 1) end end
    return #on > 0 and ("Action Bar " .. table.concat(on, ", ")) or "none of bars 2-8"
end

-- Key bindings. Each entry is "COMMAND key1 key2..." (space separated; a tab could be
-- altered when text goes through the game's edit boxes) for every command the client
-- lists (GetNumBindings/GetBinding), including commands with no key, so a load can
-- also clear keys a fresh install binds by default. Names with spaces or "|" are skipped.
local function splitBinding(e)
    local parts = {}
    for part in e:gmatch("%S+") do parts[#parts + 1] = part end
    return table.remove(parts, 1) or "", parts
end

local function cleanName(x)
    return type(x) == "string" and x ~= "" and not x:find("[%s%c|]")
end

local function listBindings()
    if not (GetNumBindings and GetBinding) then return nil end
    local ok, n = pcall(GetNumBindings)
    if not ok or type(n) ~= "number" then return nil end
    local out = {}
    for i = 1, n do
        local t = { pcall(GetBinding, i) }
        if t[1] and cleanName(t[2]) then
            local keys = {}
            for k = 4, #t do
                if cleanName(t[k]) then keys[#keys + 1] = t[k] end
            end
            out[#out + 1] = { command = t[2], keys = keys }
        end
    end
    return out
end

local function captureBindings()
    local list = listBindings()
    if not list then return nil end
    local out = {}
    for _, b in ipairs(list) do
        local e = b.command
        for _, k in ipairs(b.keys) do e = e .. " " .. k end
        out[#out + 1] = e
    end
    return out
end

local function bindingsWithKeys(saved)
    local n = 0
    for _, e in ipairs(saved or {}) do
        local _, keys = splitBinding(e)
        if #keys > 0 then n = n + 1 end
    end
    return n
end

-- Compares saved bindings with the client now. Only commands the client lists are
-- considered, so an imported profile cannot bind a key to anything else.
local function bindingDiff(saved)
    local cur = listBindings()
    if not cur then return nil end
    local have = {}
    for _, b in ipairs(cur) do have[b.command] = b.keys end
    local diffs, unknown = {}, 0
    for _, e in ipairs(saved) do
        local cmd, keys = splitBinding(e)
        local now = have[cmd]
        if not now then
            if #keys > 0 then unknown = unknown + 1 end
        else
            local a, b = {}, {}
            for _, k in ipairs(keys) do a[k] = true end
            for _, k in ipairs(now) do b[k] = true end
            local same = true
            for k in pairs(a) do if not b[k] then same = false end end
            for k in pairs(b) do if not a[k] then same = false end end
            if not same then diffs[#diffs + 1] = { command = cmd, want = keys, now = now } end
        end
    end
    return diffs, unknown
end

-- Sets every key of every listed command to the saved state, then saves the binding set.
-- Not allowed in combat (SetBinding is restricted); the caller checks.
local function applyBindings(saved)
    if not (saved and SetBinding) then return nil end
    local diffs, unknown = bindingDiff(saved)
    if not diffs then return nil end
    local r = { unbound = 0, bound = 0, failed = 0, unknown = unknown, commands = #diffs }
    -- Unbind first so a key moving from one command to another is free when it is bound.
    for _, d in ipairs(diffs) do
        local want = {}
        for _, k in ipairs(d.want) do want[k] = true end
        for _, k in ipairs(d.now) do
            if not want[k] then
                if pcall(SetBinding, k, nil) then r.unbound = r.unbound + 1 else r.failed = r.failed + 1 end
            end
        end
    end
    for _, d in ipairs(diffs) do
        for _, k in ipairs(d.want) do
            local ok, res = pcall(SetBinding, k, d.command)
            if ok and res then r.bound = r.bound + 1 else r.failed = r.failed + 1 end
        end
    end
    local save = SaveBindings or AttemptToSaveBindings
    if save then
        local set = (GetCurrentBindingSet and GetCurrentBindingSet()) or 1
        r.saved = (pcall(save, set))
    end
    return r
end

local function bindingLines(saved)
    local lines = {}
    for _, e in ipairs(saved or {}) do
        local cmd, keys = splitBinding(e)
        if #keys > 0 then lines[#lines + 1] = cmd .. ": " .. table.concat(keys, ", ") end
    end
    table.sort(lines)
    return lines
end

local function captureAddons()
    local out = {}
    local getNum = (C_AddOns and C_AddOns.GetNumAddOns) or GetNumAddOns
    local getInfo = (C_AddOns and C_AddOns.GetAddOnInfo) or GetAddOnInfo
    local isOn = (C_AddOns and C_AddOns.GetAddOnEnableState) or GetAddOnEnableState
    if not (getNum and getInfo and isOn) then return out end
    local player = UnitName("player")
    for i = 1, getNum() do
        local name = getInfo(i)
        if name then
            -- Enable state 2 means enabled for this character.
            local state = isOn(name, player)
            if state == 2 or state == true then out[#out + 1] = name end
        end
    end
    return out
end

local function captureEditMode()
    local out = { layouts = {} }
    if not (C_EditMode and C_EditMode.GetLayouts and C_EditMode.ConvertLayoutInfoToString) then
        out.error = "C_EditMode layout API not available"
        return out
    end
    local info, err = try(C_EditMode.GetLayouts)
    if not info then
        out.error = "GetLayouts failed: " .. tostring(err)
        return out
    end
    for _, layout in ipairs(info.layouts or {}) do
        local str = try(C_EditMode.ConvertLayoutInfoToString, layout)
        if str then
            out.layouts[#out.layouts + 1] = { name = layout.layoutName, str = str, }
        end
    end
    -- GetLayouts() lists custom layouts only, so activeLayout may be offset by the
    -- preset layouts. Ask the Edit Mode manager for the active layout by name instead.
    out.activeIndex = info.activeLayout
    local mgr = _G.EditModeManagerFrame
    if mgr and mgr.GetActiveLayoutInfo then
        local li = try(mgr.GetActiveLayoutInfo, mgr)
        if type(li) == "table" then out.active = li.layoutName end
    end
    return out
end

local function capture(name)
    local profile = {
        saved = date("%Y-%m-%d %H:%M"),
        character = (UnitName("player") or "?") .. "-" .. (GetRealmName() or "?"),
        screen = { uiScale = UIParent:GetScale(), width = GetScreenWidth(), height = GetScreenHeight() },
        physical = try(function() local w, h = GetPhysicalScreenSize(); return { w = w, h = h } end),
        chat = captureChat(),
        cvars = nil,   -- set below
        actionBars = captureActionBars(),
        bindings = captureBindings(),
        addons = captureAddons(),
        editMode = captureEditMode(),
    }
    profile.cvars, profile.cvarInfo = captureCVars()
    db().profiles[name] = profile
    return profile
end

---------------------------------------------------------------------------
-- Restore
---------------------------------------------------------------------------

local function applyChat(chat)
    local ok, failed = 0, 0
    local function step(fn, ...)
        local good = pcall(fn, ...)
        if good then ok = ok + 1 else failed = failed + 1 end
    end
    for i = 1, (NUM_CHAT_WINDOWS or 10) do
        local w = chat[i]
        if w then
            local frame = _G["ChatFrame" .. i]
            if (not frame or not select(7, GetChatWindowInfo(i))) and w.shown
                and FCF_OpenNewWindow and i > 2 then
                step(FCF_OpenNewWindow, w.name)
                frame = _G["ChatFrame" .. i]
            end
            if frame then
                step(SetChatWindowName, i, w.name)
                step(SetChatWindowSize, i, w.fontSize)
                step(SetChatWindowColor, i, w.r, w.g, w.b)
                step(SetChatWindowAlpha, i, w.alpha)
                step(SetChatWindowLocked, i, w.locked)
                if w.groups and ChatFrame_RemoveAllMessageGroups and ChatFrame_AddMessageGroup then
                    step(ChatFrame_RemoveAllMessageGroups, frame)
                    for _, g in ipairs(w.groups) do step(ChatFrame_AddMessageGroup, frame, g) end
                end
                if w.channels and ChatFrame_RemoveAllChannels and ChatFrame_AddChannel then
                    step(ChatFrame_RemoveAllChannels, frame)
                    for _, c in ipairs(w.channels) do step(ChatFrame_AddChannel, frame, c) end
                end
                if not w.docked and w.point then
                    step(function()
                        if FCF_UnDockFrame and frame.isDocked then FCF_UnDockFrame(frame) end
                        frame:ClearAllPoints()
                        frame:SetPoint(w.point, UIParent, w.relPoint or w.point, w.x or 0, w.y or 0)
                        frame:SetSize(w.width, w.height)
                        if FCF_SavePositionAndDimensions then FCF_SavePositionAndDimensions(frame) end
                    end)
                elseif w.docked and i > 1 and FCF_DockFrame and not frame.isDocked then
                    step(FCF_DockFrame, frame, w.docked, true)
                end
            end
        end
    end
    return ok, failed
end

-- Sets every saved CVar that differs from its current value. useUiScale goes first
-- because uiScale depends on it. Returns counts and the names that could not be set.
local function applyCVars(cvars)
    local set = (C_CVar and C_CVar.SetCVar) or SetCVar
    local r = { changed = 0, matched = 0, skipped = 0, failed = {} }
    local function one(n)
        local value = cvars[n]
        if isDenied(n) then r.skipped = r.skipped + 1; return end
        if GetCVar(n) == value then r.matched = r.matched + 1; return end
        local ok, res = pcall(set, n, value)
        if ok and res ~= false then r.changed = r.changed + 1 else r.failed[#r.failed + 1] = n end
    end
    if cvars.useUiScale ~= nil then one("useUiScale") end
    if cvars.uiScale ~= nil then one("uiScale") end
    local names = {}
    for n in pairs(cvars) do
        if n ~= "useUiScale" and n ~= "uiScale" then names[#names + 1] = n end
    end
    table.sort(names)
    for _, n in ipairs(names) do one(n) end
    return r
end

-- SetActionBarToggles stores the wanted state for the next load, so this needs the reload.
local function applyActionBars(ab)
    if not (ab and ab.bars and SetActionBarToggles) then return false end
    local b = ab.bars
    local always = ab.alwaysShow
    if always == nil then always = _G.ALWAYS_SHOW_MULTIBARS end
    return (pcall(SetActionBarToggles, b[1], b[2], b[3], b[4], b[5], b[6], b[7], always))
end

-- Compare the saved enabled-addon list with what is enabled now.
local function addonDiff(saved)
    local now = {}
    for _, n in ipairs(captureAddons()) do now[n] = true end
    local want, missing, extra = {}, {}, {}
    for _, n in ipairs(saved) do
        want[n] = true
        if not now[n] then missing[#missing + 1] = n end
    end
    for n in pairs(now) do
        if not want[n] then extra[#extra + 1] = n end
    end
    table.sort(missing); table.sort(extra)
    return missing, extra
end

---------------------------------------------------------------------------
-- Copy box (Edit Mode strings are pasted into Edit Mode's Import by hand)
---------------------------------------------------------------------------

local copyFrame
local function showCopyBox(title, text)
    if not copyFrame then
        local f = CreateFrame("Frame", "UISnapshotCopyFrame", UIParent, "BasicFrameTemplateWithInset")
        f:SetSize(560, 220)
        f:SetPoint("CENTER")
        f:SetFrameStrata("DIALOG")
        f:SetMovable(true)
        f:EnableMouse(true)
        f:RegisterForDrag("LeftButton")
        f:SetScript("OnDragStart", f.StartMoving)
        f:SetScript("OnDragStop", f.StopMovingOrSizing)
        f.title = f:CreateFontString(nil, "OVERLAY", "GameFontNormal")
        f.title:SetPoint("TOP", 0, -6)
        local sf = CreateFrame("ScrollFrame", "UISnapshotCopyScroll", f, "UIPanelScrollFrameTemplate")
        sf:SetPoint("TOPLEFT", 12, -30)
        sf:SetPoint("BOTTOMRIGHT", -32, 12)
        local eb = CreateFrame("EditBox", nil, sf)
        eb:SetMultiLine(true)
        eb:SetFontObject(ChatFontNormal)
        eb:SetWidth(500)
        eb:SetAutoFocus(false)
        eb:SetMaxLetters(0)
        eb:SetScript("OnEscapePressed", function() f:Hide() end)
        sf:SetScrollChild(eb)
        f.edit = eb
        copyFrame = f
    end
    copyFrame.title:SetText(title)
    copyFrame.edit:SetText(text)
    copyFrame:Show()
    copyFrame.edit:SetFocus()
    copyFrame.edit:HighlightText()
    local got = copyFrame.edit:GetText()
    return type(got) == "string" and #got or nil
end

ns.showCopyBox = showCopyBox

---------------------------------------------------------------------------
-- Export / import
---------------------------------------------------------------------------

local EXPORT_VERSION = 1

local function trim(s) return (tostring(s or "")):match("^%s*(.-)%s*$") end

local function str(v, max)
    if type(v) == "string" and #v <= (max or 200) then return v end
end
local function num(v)
    if type(v) == "number" and v == v and v > -1e9 and v < 1e9 then return v end
end
local function strList(t, maxItems, maxLen)
    local out = {}
    if type(t) == "table" then
        for i = 1, math.min(#t, maxItems) do
            local x = str(t[i], maxLen)
            if x then out[#out + 1] = x end
        end
    end
    return out
end

-- Copies only the fields we know, with type and size checks. Imported data is
-- never trusted as-is. Returns a clean profile, or nil plus a reason.
local function sanitizeProfile(p)
    if type(p) ~= "table" then return nil, "The export has no profile in it." end
    local out = {
        saved = str(p.saved, 40) or "?",
        character = str(p.character, 80) or "?",
        chat = {}, cvars = {}, editMode = { layouts = {} },
    }
    if type(p.screen) == "table" then
        out.screen = { uiScale = num(p.screen.uiScale), width = num(p.screen.width), height = num(p.screen.height) }
    end
    if type(p.physical) == "table" and num(p.physical.w) and num(p.physical.h) then
        out.physical = { w = p.physical.w, h = p.physical.h }
    end
    if type(p.chat) == "table" then
        for i = 1, 50 do
            local w = p.chat[i]
            if type(w) == "table" and str(w.name, 64) then
                out.chat[i] = {
                    name = w.name, fontSize = num(w.fontSize) or 14,
                    r = num(w.r) or 0, g = num(w.g) or 0, b = num(w.b) or 0, alpha = num(w.alpha) or 1,
                    shown = w.shown and true or false, locked = w.locked and true or false,
                    uninteractable = w.uninteractable and true or false,
                    docked = num(w.docked),
                    width = num(w.width), height = num(w.height), x = num(w.x), y = num(w.y),
                    point = str(w.point, 20), relPoint = str(w.relPoint, 20),
                    groups = strList(w.groups, 100, 40), channels = strList(w.channels, 50, 100),
                }
            end
        end
    end
    if type(p.actionBars) == "table" and type(p.actionBars.bars) == "table" then
        local bars = {}
        for i = 1, 7 do bars[i] = p.actionBars.bars[i] and true or false end
        local always = p.actionBars.alwaysShow
        if not (type(always) == "boolean" or type(always) == "number" or (type(always) == "string" and #always <= 10)) then always = nil end
        out.actionBars = { bars = bars, alwaysShow = always }
    end
    if type(p.bindings) == "table" then
        local list = {}
        for i = 1, 3000 do
            local e = p.bindings[i]
            if type(e) ~= "string" then break end
            local cmd, keys = splitBinding(e)
            local ok = #e <= 400 and cleanName(cmd) and #cmd <= 100 and not e:find("[%c|]")
            for _, k in ipairs(keys) do if #k > 64 then ok = false end end
            if ok then list[#list + 1] = e end
        end
        out.bindings = list
    end
    if type(p.cvarInfo) == "table" then
        out.cvarInfo = { mode = str(p.cvarInfo.mode, 60) or "?", scanned = num(p.cvarInfo.scanned) or 0 }
    end
    if type(p.cvars) == "table" then
        local n = 0
        for k, v in pairs(p.cvars) do
            local value = (type(v) == "string" or type(v) == "number" or type(v) == "boolean") and tostring(v)
            if type(k) == "string" and #k <= 64 and k:match("^[%w_]+$") and value and #value <= 200 and n < 1500 then
                out.cvars[k] = value
                n = n + 1
            end
        end
    end
    out.addons = strList(p.addons, 500, 100)
    if type(p.editMode) == "table" then
        out.editMode.active = str(p.editMode.active, 100)
        out.editMode.activeIndex = num(p.editMode.activeIndex)
        out.editMode.error = str(p.editMode.error, 200)
        if type(p.editMode.layouts) == "table" then
            for i = 1, math.min(#p.editMode.layouts, 30) do
                local l = p.editMode.layouts[i]
                if type(l) == "table" and str(l.str, 60000) and str(l.name, 100) then
                    out.editMode.layouts[#out.editMode.layouts + 1] = { name = l.name, str = l.str }
                end
            end
        end
    end
    return out
end

-- Returns the profile name on success; nil plus a message on failure; or
-- false, "exists", name when a profile with that name exists and force is not set.
function ns.importString(text, saveAs, force)
    local data, err = ns.codec.decode(text)
    if not data then return nil, err end
    if type(data.v) ~= "number" or data.v > EXPORT_VERSION then
        return nil, "This export was made by a newer version of UI Snapshot. Update the addon and try again."
    end
    local clean, why = sanitizeProfile(data.profile)
    if not clean then return nil, why end
    local name = trim(saveAs)
    if name == "" then name = trim(data.name) end
    name = name:gsub("[%c]", "")
    if name == "" then name = "imported" end
    if #name > 64 then name = name:sub(1, 64) end
    if db().profiles[name] and not force then return false, "exists", name end
    clean.importedOn = date("%Y-%m-%d %H:%M")
    db().profiles[name] = clean
    local names = {}
    for c in pairs(clean.cvars) do names[#names + 1] = c end
    table.sort(names)
    say(("Imported '%s': %d chat windows, %d CVars, %d addons, %d Edit Mode layouts."):format(
        name, count(clean.chat), #names, #clean.addons, #clean.editMode.layouts))
    if #names > 0 then
        local shown = {}
        for i = 1, math.min(#names, 12) do shown[i] = names[i] end
        say("Load will set these game settings: " .. table.concat(shown, ", ")
            .. (#names > 12 and (" ...and " .. (#names - 12) .. " more") or "")
            .. ". /uisnap cvars " .. name .. " lists them all; check them first if the export came from someone else.")
    end
    if ns.refresh then ns.refresh() end
    return name
end

---------------------------------------------------------------------------
-- Slash commands
---------------------------------------------------------------------------

local function need(name)
    local p = name and db().profiles[name]
    if not p then say("No profile named '" .. tostring(name) .. "'. /uisnap list") end
    return p
end

local function warnIfResolutionDiffers(p)
    local saved = p.physical
    if type(saved) ~= "table" or not saved.w then return end
    local now = try(function() local w, h = GetPhysicalScreenSize(); return { w = w, h = h } end)
    if now and (now.w ~= saved.w or now.h ~= saved.h) then
        say(("Heads up: saved at %dx%d, this client is %dx%d. Positions saved in pixels-from-edge may not line up."):format(
            saved.w, saved.h, now.w, now.h))
    end
end

---------------------------------------------------------------------------
-- Reload after a change, and show the report once the game is back
---------------------------------------------------------------------------

local RELOAD_DELAY = 1.5

-- Called after Load, Enable addons and Import. If auto-reload is on, stores the
-- messages so they can be shown after the reload, then reloads shortly.
function ns.afterChange(lines)
    lines = lines or {}
    if db().settings.autoReload then
        db().pendingReport = { when = date("%Y-%m-%d %H:%M"), lines = lines }
        say(("Reloading the UI in %.1f seconds (turn this off in the window if you prefer to /reload yourself)."):format(RELOAD_DELAY))
        local function go()
            local ok = pcall(ReloadUI)
            if not ok then say("Could not reload automatically; type /reload.") end
        end
        if C_Timer and C_Timer.After then C_Timer.After(RELOAD_DELAY, go) else go() end
    else
        say("Type /reload to finish; some changes need a reload or relog.")
    end
end

local function showPendingReport()
    local r = db().pendingReport
    if not r then return end
    db().pendingReport = nil
    local function show()
        print("|cff33ccffUI Snapshot:|r finished before the reload (" .. tostring(r.when) .. "):")
        for _, line in ipairs(r.lines or {}) do print(line) end
    end
    if C_Timer and C_Timer.After then C_Timer.After(3, show) else show() end
end

local events = CreateFrame("Frame")
events:RegisterEvent("PLAYER_LOGIN")
events:SetScript("OnEvent", function(self, event)
    if event == "PLAYER_LOGIN" then showPendingReport() end
end)
ns.showPendingReport = showPendingReport   -- exposed for the mock test

local commands = {}

function commands.save(name)
    name = (name and name ~= "") and name or "default"
    local p = capture(name)
    say(("Saved '%s': %d chat windows, %d addons, %d Edit Mode layouts."):format(name, count(p.chat), #p.addons, #p.editMode.layouts))
    if p.cvarInfo and p.cvarInfo.scanned > 0 then
        say(("Game settings: %d CVars changed from default (of %d checked), %s."):format(count(p.cvars), p.cvarInfo.scanned, "action bars: " .. barsText(p.actionBars)))
    else
        say(("WARNING: only %d settings were saved (tracked list plus the Advanced Options ones): the game's list of all settings could not be read. Run /uisnap watch for the reason. Action bars: %s."):format(count(p.cvars), barsText(p.actionBars)))
    end
    if p.bindings then
        say(("Key bindings: %d commands with keys saved (of %d listed)."):format(bindingsWithKeys(p.bindings), #p.bindings))
    else
        say("Key bindings: not captured (GetNumBindings/GetBinding not available).")
    end
    if p.editMode.error then say("Edit Mode: " .. p.editMode.error) end
    if ns.refresh then ns.refresh() end
end

function commands.list()
    local any = false
    for name, p in pairs(db().profiles) do
        any = true
        say(("%s  (saved %s by %s)"):format(name, p.saved or "?", p.character or "?"))
    end
    if not any then say("No profiles yet. /uisnap save <name>") end
end

function commands.show(name)
    local p = need(name); if not p then return end
    say(("%s: %d chat windows, %d CVars (%s), %d addons, %d Edit Mode layouts, UI scale %.3f, UI size %dx%d%s")
        :format(name, count(p.chat), count(p.cvars), (p.cvarInfo and p.cvarInfo.mode) or "tracked list only", #p.addons, #p.editMode.layouts,
            (p.screen and p.screen.uiScale) or 0, (p.screen and p.screen.width) or 0,
            (p.screen and p.screen.height) or 0,
            (p.physical and p.physical.w) and (", window " .. p.physical.w .. "x" .. p.physical.h) or ""))
    say("Action bars saved: " .. barsText(p.actionBars) .. ". /uisnap cvars " .. name .. " lists every saved setting.")
    say(p.bindings and ("Key bindings saved: " .. bindingsWithKeys(p.bindings) .. " commands with keys. /uisnap keys " .. name .. " lists them.")
        or "Key bindings: none saved in this profile (save again with 0.6.0 or later).")
    say("Edit Mode active layout: " .. tostring(p.editMode.active or "not detected")
        .. " (raw index " .. tostring(p.editMode.activeIndex) .. ")")
end

function commands.diff(name)
    local p = need(name); if not p then return end
    warnIfResolutionDiffers(p)
    local missing, extra = addonDiff(p.addons)
    say(("Addons: %d saved but not enabled now, %d enabled now but not in the profile."):format(#missing, #extra))
    if #missing > 0 then say("Not enabled / not installed: " .. table.concat(missing, ", ")) end
    if #extra > 0 then say("Not in profile: " .. table.concat(extra, ", ")) end
    local diffs = {}
    for cv, v in pairs(p.cvars) do
        if not isDenied(cv) and GetCVar(cv) ~= v then diffs[#diffs + 1] = cv end
    end
    table.sort(diffs)
    if #diffs == 0 then
        say("CVars: all " .. count(p.cvars) .. " saved settings match.")
    else
        say(("CVars: %d of %d saved settings differ from now."):format(#diffs, count(p.cvars)))
        for i = 1, math.min(#diffs, 25) do
            say(("  %s: now %s, saved %s"):format(diffs[i], tostring(GetCVar(diffs[i])), tostring(p.cvars[diffs[i]])))
        end
        if #diffs > 25 then say(("  ...and %d more."):format(#diffs - 25)) end
    end
    if p.bindings then
        local bd, unknown = bindingDiff(p.bindings)
        if bd then
            if #bd == 0 then
                say("Key bindings: all match" .. (unknown > 0 and (" (" .. unknown .. " saved commands are not in this client)") or "") .. ".")
            else
                say(("Key bindings: %d commands differ from now."):format(#bd))
                for i = 1, math.min(#bd, 25) do
                    local d = bd[i]
                    say(("  %s: now %s, saved %s"):format(d.command,
                        #d.now > 0 and table.concat(d.now, "/") or "none", #d.want > 0 and table.concat(d.want, "/") or "none"))
                end
                if #bd > 25 then say(("  ...and %d more."):format(#bd - 25)) end
            end
        end
    end
    local nowBars = captureActionBars()
    if p.actionBars and nowBars then
        if barsText(p.actionBars) == barsText(nowBars) then
            say("Action bars: match (" .. barsText(nowBars) .. ").")
        else
            say("Action bars: now " .. barsText(nowBars) .. ", saved " .. barsText(p.actionBars) .. ".")
        end
    end
end

function commands.load(name)
    local p = need(name); if not p then return end
    if InCombatLockdown() then say("Not in combat, please."); return end
    ns.beginCapture()
    warnIfResolutionDiffers(p)
    if p.actionBars then
        if applyActionBars(p.actionBars) then
            say("Action bars set to: " .. barsText(p.actionBars) .. " (shows after the reload).")
        else
            say("Could not set the action bars; turn them on in the game's settings.")
        end
    end
    if p.bindings then
        local br = applyBindings(p.bindings)
        if br then
            say(("Key bindings: %d keys set, %d cleared, %d failed, %d commands changed%s%s."):format(
                br.bound, br.unbound, br.failed, br.commands,
                br.unknown > 0 and (", " .. br.unknown .. " saved commands skipped (not in this client; enable that addon and load again)") or "",
                br.saved and ", saved" or ", NOT saved (SaveBindings failed or is missing)"))
        else
            say("Key bindings: could not be applied (binding API not available).")
        end
    end
    local r = applyCVars(p.cvars)
    local hOk, hFail = applyChat(p.chat)
    say(("Applied '%s': %d CVars changed, %d already matched, %d could not be set; chat steps %d ok / %d failed."):format(
        name, r.changed, r.matched, #r.failed, hOk, hFail))
    if #r.failed > 0 then
        local shown = {}
        for i = 1, math.min(#r.failed, 15) do shown[i] = r.failed[i] end
        say("Could not set: " .. table.concat(shown, ", ") .. (#r.failed > 15 and (" ...and " .. (#r.failed - 15) .. " more") or ""))
    end
    local missing = addonDiff(p.addons)
    if #missing > 0 then
        say(#missing .. " saved addons are not enabled; /uisnap diff " .. name .. " lists them.")
    end
    if #p.editMode.layouts > 0 then
        say("Edit Mode layouts are not applied automatically: use the Edit Mode strings button (or /uisnap editmode "
            .. name .. ") and paste one into Edit Mode > Layout > Import.")
    end
    ns.afterChange(ns.endCapture())
end

function commands.addons(name)
    local p = need(name); if not p then return end
    local enable = (C_AddOns and C_AddOns.EnableAddOn) or EnableAddOn
    if not enable then say("EnableAddOn not available."); return end
    local missing = addonDiff(p.addons)
    local n = 0
    for _, a in ipairs(missing) do
        if pcall(enable, a, UnitName("player")) then n = n + 1 end
    end
    ns.beginCapture()
    say(("Enabled %d addon(s). Addons that are not installed stay missing."):format(n))
    ns.afterChange(ns.endCapture())
end

function commands.editmode(name)
    local p = need(name); if not p then return end
    local layouts = p.editMode.layouts
    if #layouts == 0 then say("No Edit Mode layouts in '" .. name .. "'. " .. (p.editMode.error or "")); return end
    local parts = {}
    for _, l in ipairs(layouts) do
        parts[#parts + 1] = "-- layout: " .. tostring(l.name) .. (l.name == p.editMode.active and " (was active)" or "")
        parts[#parts + 1] = l.str
    end
    showCopyBox("Edit Mode layouts: copy one string line into Import", table.concat(parts, "\n"))
end

function commands.delete(name)
    if need(name) then
        db().profiles[name] = nil
        say("Deleted '" .. name .. "'.")
        if ns.refresh then ns.refresh() end
    end
end

function commands.cvar(arg)
    local action, cv = (arg or ""):match("^(%S+)%s*(%S*)")
    local list = db().cvars
    if action == "add" and cv ~= "" then
        for _, x in ipairs(list) do if x == cv then say(cv .. " already tracked."); return end end
        list[#list + 1] = cv
        say(("Tracking %s (current value %s)."):format(cv, tostring(GetCVar(cv))))
    elseif action == "remove" and cv ~= "" then
        for i, x in ipairs(list) do if x == cv then table.remove(list, i); say("Removed " .. cv); return end end
        say(cv .. " was not tracked.")
    else
        say("Tracked CVars: " .. table.concat(list, ", "))
        say("/uisnap cvar add <name>  |  /uisnap cvar remove <name>")
    end
end

function commands.cvars(name)
    local p = need(name); if not p then return end
    local names = {}
    for n in pairs(p.cvars) do names[#names + 1] = n end
    table.sort(names)
    local lines = {}
    for _, n in ipairs(names) do lines[#lines + 1] = n .. " = " .. tostring(p.cvars[n]) end
    local keys = bindingLines(p.bindings)
    if #lines == 0 and #keys == 0 then say("No settings saved in '" .. name .. "'."); return end
    local text = table.concat(lines, "\n")
    if #keys > 0 then text = text .. (#lines > 0 and "\n\n" or "") .. "-- Key bindings --\n" .. table.concat(keys, "\n") end
    showCopyBox(("%d saved settings and %d key bindings in '%s'"):format(#lines, #keys, name), text)
end

function commands.keys(name)
    local p = need(name); if not p then return end
    local keys = bindingLines(p.bindings)
    if #keys == 0 then say("No key bindings saved in '" .. name .. "'. Save again to capture them."); return end
    showCopyBox(("%d key bindings in '%s'"):format(#keys, name), table.concat(keys, "\n"))
end

-- Finding the CVar behind a setting. Some Forever settings (Damage Meter, Swing Timer,
-- Cooldown Manager...) have no documented CVar name, so these commands show it.
local function saveVerdict(name, v, d, locked, ro)
    if isDenied(name) then return "never saved (machine-specific deny list)" end
    if locked then return "locked from users: skipped" end
    if ro then return "read-only: skipped" end
    if v == nil then return "no value" end
    if d == nil then return "no default reported: only saved if tracked" end
    if v == d then return "equals its default: not saved (a fresh install already has it)" end
    return "differs from default: Save captures it"
end

local watchSnap

function commands.watch()
    local names = allCVarNames()
    if not names then
        local _, why = allCommands()
        say("The game's list of settings is not available (" .. tostring(why) .. "), so settings cannot be watched.")
        return
    end
    watchSnap = {}
    for _, n in ipairs(names) do watchSnap[n] = GetCVar(n) end
    say(("Watching %d CVars. Now change ONE setting in the game's Options (tick or untick the box), then type /uisnap changed."):format(#names))
end

function commands.changed()
    if not watchSnap then say("Type /uisnap watch first, then change a setting."); return end
    local names = allCVarNames() or {}
    local n = 0
    for _, name in ipairs(names) do
        local now = GetCVar(name)
        local before = watchSnap[name]
        if now ~= before then
            n = n + 1
            if n <= 25 then
                local v, d, locked, ro = cvarInfo(name)
                say(("%s: %s -> %s (default %s): %s"):format(name, tostring(before), tostring(now), tostring(d), saveVerdict(name, v, d, locked, ro)))
            end
        end
    end
    if n == 0 then
        say("No CVar changed. That setting is probably not stored as a CVar (UI Snapshot cannot capture it yet); send the name of the setting.")
    elseif n > 25 then
        say(("...and %d more."):format(n - 25))
    end
end

-- /uisnap find <text> [profile]: CVars whose name or help text contains <text>.
function commands.find(arg)
    local text, profile = (arg or ""):match("^%s*(%S+)%s*(.-)%s*$")
    if not text then say("/uisnap find <text> [profile]  (e.g. /uisnap find damage)"); return end
    local cmds, why = allCommands()
    if not cmds then say("The game's list of settings is not available (" .. tostring(why) .. ")."); return end
    local ct = cvarType()
    local needle = text:lower()
    local p = profile ~= "" and db().profiles[profile] or nil
    if profile ~= "" and not p then say("No profile named '" .. profile .. "'; showing live values only.") end
    local hits = {}
    for _, c in ipairs(cmds) do
        if c.commandType == ct and type(c.command) == "string" then
            local help = type(c.help) == "string" and c.help or ""
            if c.command:lower():find(needle, 1, true) or help:lower():find(needle, 1, true) then
                hits[#hits + 1] = c
            end
        end
    end
    table.sort(hits, function(a, b) return a.command < b.command end)
    if #hits == 0 then
        say("No CVar name or help text contains '" .. text .. "'. The setting may not be a CVar.")
        return
    end
    say(("%d CVars match '%s':"):format(#hits, text))
    for i = 1, math.min(#hits, 30) do
        local name = hits[i].command
        local v, d, locked, ro = cvarInfo(name)
        local line = ("%s = %s (default %s): %s"):format(name, tostring(v), tostring(d), saveVerdict(name, v, d, locked, ro))
        if p then line = line .. (p.cvars[name] ~= nil and ("; in '" .. profile .. "': " .. tostring(p.cvars[name])) or ("; NOT in '" .. profile .. "'")) end
        say(line)
    end
    if #hits > 30 then say(("...and %d more; use a longer word."):format(#hits - 30)) end
end

-- Prints what the game reports for the action bars, to help find where they are stored.
function commands.bars()
    local t = GetActionBarToggles and { pcall(GetActionBarToggles) } or nil
    if not t or not t[1] then say("GetActionBarToggles is not available."); return end
    local parts = {}
    for i = 2, #t do parts[#parts + 1] = tostring(t[i]) end
    say("GetActionBarToggles: " .. table.concat(parts, ", "))
    for i = 1, 8 do
        local v = _G["SHOW_MULTI_ACTIONBAR_" .. i]
        if v ~= nil then say(("SHOW_MULTI_ACTIONBAR_%d = %s"):format(i, tostring(v))) end
    end
    say("ALWAYS_SHOW_MULTIBARS = " .. tostring(_G.ALWAYS_SHOW_MULTIBARS))
end

function commands.export(name)
    local p = need(name); if not p then return end
    local ok, text = pcall(ns.codec.encode, { v = EXPORT_VERSION, name = name, profile = p }, true)
    if not ok then say("Export failed: " .. tostring(text)); return end
    local shown = showCopyBox("Export of '" .. name .. "': Ctrl+C to copy", text)
    say(("Export of '%s' is %d characters. Copy the whole box into a text file for safekeeping."):format(name, #text))
    if shown and shown ~= #text then
        say(("WARNING: the box holds %d of the %d characters, so the copy would be incomplete. Tell the author."):format(shown, #text))
    end
    -- Which saved settings contain characters that needed escaping (a likely cause of a blank box).
    local odd = {}
    for k, v in pairs(p.cvars or {}) do
        if ns.codec.escapeCount(tostring(v)) > 0 then odd[#odd + 1] = k end
    end
    table.sort(odd)
    if #odd > 0 then
        say(("Note: %d settings have unusual characters in their value and were escaped in the export: %s%s.")
            :format(#odd, table.concat(odd, ", ", 1, math.min(#odd, 8)), #odd > 8 and ", ..." or ""))
    end
end

function commands.import()
    if ns.openImport then ns.openImport()
    else say("Open /uisnap and press Import (the import box needs the window).") end
end

function commands.help()
    say("/uisnap opens the window. Commands: save|load|show|diff|delete|export|cvars|keys <name>, list, import, bars, find <text>, watch, changed, addons <name>, editmode <name>, minimap, cvar [add|remove <name>]")
end

SLASH_UISNAPSHOT1 = "/uisnap"
SlashCmdList["UISNAPSHOT"] = function(msg)
    local cmd, rest = (msg or ""):match("^(%S*)%s*(.-)%s*$")
    if cmd == "" or cmd == "ui" then
        if ns.toggleUI then ns.toggleUI() else commands.help() end
        return
    end
    local fn = commands[cmd]
    if fn then fn(rest) else commands.help() end
end

ns.commands = commands
