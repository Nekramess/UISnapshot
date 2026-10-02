-- UI Snapshot 0.1.1
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

local DB_VERSION = 1
local DEFAULT_CVARS = {
    "useUiScale", "uiScale", "chatStyle", "chatClassColorOverride",
    "whisperMode", "chatMouseScroll", "showTutorials",
}

local function say(msg)
    print("|cff33ccffUI Snapshot:|r " .. tostring(msg))
end

local function db()
    local d = UISnapshotDB
    d.version = d.version or DB_VERSION
    d.profiles = d.profiles or {}
    d.cvars = d.cvars or {}
    if #d.cvars == 0 then
        for _, name in ipairs(DEFAULT_CVARS) do d.cvars[#d.cvars + 1] = name end
    end
    return d
end

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

local function captureCVars()
    local out = {}
    for _, name in ipairs(db().cvars) do
        local v = GetCVar(name)
        if v ~= nil then out[name] = v end
    end
    return out
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
            out.layouts[#out.layouts + 1] = { name = layout.layoutName, str = str }
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
        cvars = captureCVars(),
        addons = captureAddons(),
        editMode = captureEditMode(),
    }
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

local function applyCVars(cvars)
    local ok, failed = 0, 0
    for name, value in pairs(cvars) do
        local set = C_CVar and C_CVar.SetCVar or SetCVar
        local good, result = pcall(set, name, value)
        if good and result ~= false then ok = ok + 1 else failed = failed + 1 end
    end
    return ok, failed
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

local commands = {}

function commands.save(name)
    name = (name and name ~= "") and name or "default"
    local p = capture(name)
    say(("Saved '%s': %d chat windows, %d CVars, %d addons, %d Edit Mode layouts.")
        :format(name, count(p.chat), count(p.cvars), #p.addons, #p.editMode.layouts))
    if p.editMode.error then say("Edit Mode: " .. p.editMode.error) end
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
    say(("%s: %d chat windows, %d CVars, %d addons, %d Edit Mode layouts, UI scale %.3f, UI size %dx%d%s")
        :format(name, count(p.chat), count(p.cvars), #p.addons, #p.editMode.layouts,
            (p.screen and p.screen.uiScale) or 0, (p.screen and p.screen.width) or 0,
            (p.screen and p.screen.height) or 0,
            (p.physical and p.physical.w) and (", window " .. p.physical.w .. "x" .. p.physical.h) or ""))
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
    local changed = 0
    for cv, v in pairs(p.cvars) do
        if GetCVar(cv) ~= v then
            changed = changed + 1
            say(("CVar %s: now %s, saved %s"):format(cv, tostring(GetCVar(cv)), tostring(v)))
        end
    end
    if changed == 0 then say("CVars: all match.") end
end

function commands.load(name)
    local p = need(name); if not p then return end
    if InCombatLockdown() then say("Not in combat, please."); return end
    warnIfResolutionDiffers(p)
    local cOk, cFail = applyCVars(p.cvars)
    local hOk, hFail = applyChat(p.chat)
    say(("Applied '%s': CVars %d ok / %d failed; chat steps %d ok / %d failed."):format(name, cOk, cFail, hOk, hFail))
    local missing = addonDiff(p.addons)
    if #missing > 0 then
        say(#missing .. " saved addons are not enabled; /uisnap diff " .. name .. " lists them.")
    end
    if #p.editMode.layouts > 0 then
        say("Edit Mode layouts are not applied automatically: /uisnap editmode " .. name
            .. ", then paste into Edit Mode > Layout > Import.")
    end
    say("Reload (/reload) to finish; some CVars need a reload or relog.")
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
    say(("Enabled %d addon(s); /reload to apply. Addons that are not installed stay missing."):format(n))
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
    if need(name) then db().profiles[name] = nil; say("Deleted '" .. name .. "'.") end
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

function commands.help()
    say("/uisnap save|load|show|diff|delete <name>, list, addons <name>, editmode <name>, cvar [add|remove <name>]")
end

SLASH_UISNAPSHOT1 = "/uisnap"
SlashCmdList["UISNAPSHOT"] = function(msg)
    local cmd, rest = (msg or ""):match("^(%S*)%s*(.-)%s*$")
    local fn = commands[cmd ~= "" and cmd or "help"]
    if fn then fn(rest) else commands.help() end
end

ns.commands = commands
