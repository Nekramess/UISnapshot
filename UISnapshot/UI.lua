-- UI Snapshot: button window. Wraps the slash commands; no new restore logic.
-- UNTESTED in the live client (only run against a simulated client).
-- Uses stock templates: BasicFrameTemplateWithInset, UIPanelButtonTemplate,
-- UIPanelScrollFrameTemplate, InputBoxTemplate.

local ADDON, ns = ...
local ui = ns.ui
local commands, db, say = ns.commands, ns.db, ns.say

local ROW_H = 20
local frame

local function trim(s) return (s or ""):match("^%s*(.-)%s*$") end

---------------------------------------------------------------------------
-- Confirmation popup (used for save-over, load and delete)
---------------------------------------------------------------------------

StaticPopupDialogs["UISNAPSHOT_CONFIRM"] = {
    text = "%s",
    button1 = ACCEPT,
    button2 = CANCEL,
    OnAccept = function(self, data)
        if data and data.fn then data.fn() end
    end,
    timeout = 0,
    whileDead = true,
    hideOnEscape = true,
    preferredIndex = 3,
}

local function confirm(text, fn)
    StaticPopup_Show("UISNAPSHOT_CONFIRM", text, nil, { fn = fn })
end

---------------------------------------------------------------------------
-- Profile list
---------------------------------------------------------------------------

local function sortedNames()
    local names = {}
    for n in pairs(db().profiles) do names[#names + 1] = n end
    table.sort(names, function(a, b) return a:lower() < b:lower() end)
    return names
end

local function choose(name)
    ui.selected = name
    if frame then frame.nameBox:SetText(name or "") end
    ns.refresh()
end

function ns.refresh()
    if not frame then return end
    local names = sortedNames()
    local profiles = db().profiles
    if ui.selected and not profiles[ui.selected] then ui.selected = nil end
    for i, n in ipairs(names) do
        local row = frame.rows[i]
        if not row then
            row = CreateFrame("Button", nil, frame.listChild)
            row:SetHeight(ROW_H)
            row:SetPoint("TOPLEFT", 0, -(i - 1) * ROW_H)
            row:SetPoint("TOPRIGHT", 0, -(i - 1) * ROW_H)
            row.bg = row:CreateTexture(nil, "BACKGROUND")
            row.bg:SetAllPoints()
            row.bg:SetColorTexture(1, 1, 1, 0.18)
            row.text = row:CreateFontString(nil, "OVERLAY", "GameFontHighlightSmall")
            row.text:SetPoint("LEFT", 6, 0)
            row:SetScript("OnClick", function(self) choose(self.profileName) end)
            frame.rows[i] = row
        end
        row.profileName = n
        row.text:SetText(n .. "  |cff888888" .. (profiles[n].saved or "") .. "|r")
        row.bg:SetShown(n == ui.selected)
        row:Show()
    end
    for i = #names + 1, #frame.rows do frame.rows[i]:Hide() end
    frame.listChild:SetHeight(math.max(1, #names * ROW_H))
    frame.empty:SetShown(#names == 0)
end

---------------------------------------------------------------------------
-- Actions
---------------------------------------------------------------------------

local function selected()
    local n = ui.selected
    if not n or not db().profiles[n] then
        say("Pick a profile from the list first.")
        return nil
    end
    return n
end

local actions = {}

function actions.save()
    local name = trim(frame.nameBox:GetText())
    if name == "" then name = "default" end
    local function doSave() commands.save(name); choose(name) end
    if db().profiles[name] then
        confirm("Overwrite saved profile '" .. name .. "' with your current setup?", doSave)
    else
        doSave()
    end
end

function actions.load()
    local n = selected(); if not n then return end
    confirm("Apply profile '" .. n .. "'? This changes your chat windows and tracked CVars.",
        function() commands.load(n) end)
end

function actions.diff() local n = selected(); if n then commands.diff(n) end end
function actions.show() local n = selected(); if n then commands.show(n) end end
function actions.addons() local n = selected(); if n then commands.addons(n) end end
function actions.editmode() local n = selected(); if n then commands.editmode(n) end end
function actions.export() local n = selected(); if n then commands.export(n) end end
function actions.cvars() local n = selected(); if n then commands.cvars(n) end end


function actions.delete()
    local n = selected(); if not n then return end
    confirm("Delete saved profile '" .. n .. "'?", function()
        commands.delete(n)
        choose(nil)
    end)
end

local function cvarName()
    local v = trim(frame.cvarBox:GetText())
    if v == "" then say("Type a CVar name first."); return nil end
    return v
end

function actions.cvarAdd() local v = cvarName(); if v then commands.cvar("add " .. v) end end
function actions.cvarRemove() local v = cvarName(); if v then commands.cvar("remove " .. v) end end
function actions.cvarList() commands.cvar("") end

---------------------------------------------------------------------------
-- Import box
---------------------------------------------------------------------------

local importFrame

local function runImport(force)
    local text = importFrame.edit:GetText()
    local saveAs = trim(importFrame.nameBox:GetText())
    ns.beginCapture()
    local name, why, existing = ns.importString(text, saveAs, force)
    local lines = ns.endCapture()
    if name then
        importFrame:Hide()
        importFrame.edit:SetText("")
        importFrame.nameBox:SetText("")
        choose(name)
        ns.afterChange(lines)
    elseif name == false then
        confirm("A profile named '" .. tostring(existing) .. "' already exists. Replace it with the imported one?",
            function() runImport(true) end)
    else
        say("Import failed: " .. tostring(why))
    end
end

local function buildImport()
    local f = CreateFrame("Frame", "UISnapshotImportFrame", UIParent, "BasicFrameTemplateWithInset")
    f:SetSize(560, 330)
    f:SetPoint("CENTER", 0, 40)
    f:SetFrameStrata("FULLSCREEN_DIALOG")
    f:SetMovable(true)
    f:EnableMouse(true)
    f:SetClampedToScreen(true)
    f:RegisterForDrag("LeftButton")
    f:SetScript("OnDragStart", f.StartMoving)
    f:SetScript("OnDragStop", f.StopMovingOrSizing)
    tinsert(UISpecialFrames, "UISnapshotImportFrame")

    local title = f:CreateFontString(nil, "OVERLAY", "GameFontNormal")
    title:SetPoint("TOP", 0, -6)
    title:SetText("Import a profile")

    local help = f:CreateFontString(nil, "OVERLAY", "GameFontHighlightSmall")
    help:SetPoint("TOPLEFT", 14, -30)
    help:SetWidth(530)
    help:SetJustifyH("LEFT")
    help:SetText("Click in the box, paste an export (Ctrl+V), then press Import. Only import exports you made or trust: loading the profile will set the CVars it lists.")

    local bg = f:CreateTexture(nil, "ARTWORK")
    bg:SetPoint("TOPLEFT", 14, -62)
    bg:SetPoint("BOTTOMRIGHT", -34, 62)
    bg:SetColorTexture(0, 0, 0, 0.45)
    local sf = CreateFrame("ScrollFrame", "UISnapshotImportScroll", f, "UIPanelScrollFrameTemplate")
    sf:SetPoint("TOPLEFT", 18, -66)
    sf:SetPoint("BOTTOMRIGHT", -38, 66)
    local eb = CreateFrame("EditBox", nil, sf)
    eb:SetMultiLine(true)
    eb:SetFontObject(ChatFontNormal)
    eb:SetWidth(490)
    eb:SetAutoFocus(false)
    eb:SetMaxLetters(0)
    eb:SetScript("OnEscapePressed", function(self) self:ClearFocus() end)
    sf:SetScrollChild(eb)
    f.edit = eb

    local lbl = f:CreateFontString(nil, "OVERLAY", "GameFontNormalSmall")
    lbl:SetPoint("BOTTOMLEFT", 16, 38)
    lbl:SetText("Save as (optional, blank keeps the exported name)")
    local nb = CreateFrame("EditBox", nil, f, "InputBoxTemplate")
    nb:SetSize(220, 22)
    nb:SetPoint("BOTTOMLEFT", 22, 12)
    nb:SetAutoFocus(false)
    nb:SetScript("OnEscapePressed", function(self) self:ClearFocus() end)
    f.nameBox = nb

    local go = CreateFrame("Button", nil, f, "UIPanelButtonTemplate")
    go:SetSize(110, 24)
    go:SetPoint("BOTTOMRIGHT", -130, 10)
    go:SetText("Import")
    go:SetScript("OnClick", function() runImport(false) end)
    local cancel = CreateFrame("Button", nil, f, "UIPanelButtonTemplate")
    cancel:SetSize(110, 24)
    cancel:SetPoint("BOTTOMRIGHT", -14, 10)
    cancel:SetText(CANCEL)
    cancel:SetScript("OnClick", function() f:Hide() end)

    f:Hide()
    importFrame = f
    return f
end

function ns.openImport()
    if not importFrame then buildImport() end
    importFrame:Show()
    importFrame.edit:SetFocus()
end
actions.import = ns.openImport

---------------------------------------------------------------------------
-- Window
---------------------------------------------------------------------------

local function button(parent, label, x, y, w, onClick)
    local b = CreateFrame("Button", nil, parent, "UIPanelButtonTemplate")
    b:SetSize(w, 24)
    b:SetPoint("TOPLEFT", x, y)
    b:SetText(label)
    b:SetScript("OnClick", onClick)
    return b
end

local function label(parent, text, x, y)
    local fs = parent:CreateFontString(nil, "OVERLAY", "GameFontNormalSmall")
    fs:SetPoint("TOPLEFT", x, y)
    fs:SetText(text)
    return fs
end

local function build()
    local f = CreateFrame("Frame", "UISnapshotFrame", UIParent, "BasicFrameTemplateWithInset")
    f:SetSize(560, 460)
    f:SetPoint("CENTER")
    f:SetFrameStrata("HIGH")
    f:SetMovable(true)
    f:EnableMouse(true)
    f:SetClampedToScreen(true)
    f:RegisterForDrag("LeftButton")
    f:SetScript("OnDragStart", f.StartMoving)
    f:SetScript("OnDragStop", f.StopMovingOrSizing)
    tinsert(UISpecialFrames, "UISnapshotFrame")   -- Escape closes it
    f.rows = {}

    local title = f:CreateFontString(nil, "OVERLAY", "GameFontNormal")
    title:SetPoint("TOP", 0, -6)
    title:SetText("UI Snapshot")

    -- Profile list (left)
    label(f, "Saved profiles", 14, -32)
    local sf = CreateFrame("ScrollFrame", "UISnapshotListScroll", f, "UIPanelScrollFrameTemplate")
    sf:SetPoint("TOPLEFT", 14, -50)
    sf:SetSize(214, 172)
    local child = CreateFrame("Frame", nil, sf)
    child:SetSize(214, 1)
    sf:SetScrollChild(child)
    f.listChild = child
    local bg = f:CreateTexture(nil, "ARTWORK")
    bg:SetPoint("TOPLEFT", sf, "TOPLEFT", -2, 2)
    bg:SetPoint("BOTTOMRIGHT", sf, "BOTTOMRIGHT", 24, -2)
    bg:SetColorTexture(0, 0, 0, 0.3)
    f.empty = f:CreateFontString(nil, "OVERLAY", "GameFontDisableSmall")
    f.empty:SetPoint("TOP", sf, "TOP", 0, -12)
    f.empty:SetText("No profiles yet.\nType a name and press Save.")

    -- Name box and buttons (right)
    label(f, "Profile name", 268, -32)
    local nb = CreateFrame("EditBox", nil, f, "InputBoxTemplate")
    nb:SetSize(240, 22)
    nb:SetPoint("TOPLEFT", 276, -50)
    nb:SetAutoFocus(false)
    nb:SetScript("OnEscapePressed", function(self) self:ClearFocus() end)
    nb:SetScript("OnEnterPressed", function(self) self:ClearFocus(); actions.save() end)
    f.nameBox = nb

    button(f, "Save", 268, -82, 126, actions.save)
    button(f, "Load", 400, -82, 126, actions.load)
    button(f, "Diff", 268, -112, 126, actions.diff)
    button(f, "Details", 400, -112, 126, actions.show)
    button(f, "Enable addons", 268, -142, 126, actions.addons)
    button(f, "Edit Mode strings", 400, -142, 126, actions.editmode)
    button(f, "Export", 268, -172, 126, actions.export)
    button(f, "Import", 400, -172, 126, actions.import)
    button(f, "Delete", 268, -202, 126, actions.delete)
    button(f, "View settings", 400, -202, 126, actions.cvars)

    -- Tracked CVars
    label(f, "Tracked CVars (saved and restored with each profile)", 14, -236)
    local cb = CreateFrame("EditBox", nil, f, "InputBoxTemplate")
    cb:SetSize(180, 22)
    cb:SetPoint("TOPLEFT", 20, -254)
    cb:SetAutoFocus(false)
    cb:SetScript("OnEscapePressed", function(self) self:ClearFocus() end)
    f.cvarBox = cb
    button(f, "Track", 210, -253, 80, actions.cvarAdd)
    button(f, "Untrack", 296, -253, 80, actions.cvarRemove)
    button(f, "List", 382, -253, 80, actions.cvarList)

    -- Settings
    f.checks = {}
    local function checkbox(y, text, get, set)
        local cb = CreateFrame("CheckButton", nil, f, "UICheckButtonTemplate")
        cb:SetSize(24, 24)
        cb:SetPoint("TOPLEFT", 12, y)
        local fs = f:CreateFontString(nil, "OVERLAY", "GameFontHighlightSmall")
        fs:SetPoint("LEFT", cb, "RIGHT", 2, 0)
        fs:SetText(text)
        cb:SetScript("OnClick", function(self) set(self:GetChecked() and true or false) end)
        cb.get = get
        f.checks[#f.checks + 1] = cb
        return cb
    end
    local settings = function() return ns.db().settings end
    checkbox(-282, "Reload the UI after Load, Enable addons and Import",
        function() return settings().autoReload end,
        function(v) settings().autoReload = v end)
    checkbox(-304, "Show the minimap button",
        function() return ns.minimap.isShown() end,
        function(v) ns.minimap.setShown(v) end)
    function ns.refreshSettings()
        for _, cb in ipairs(f.checks) do cb:SetChecked(cb.get() and true or false) end
    end
    ns.refreshSettings()

    -- Output log
    label(f, "Output", 14, -338)
    local lbg = f:CreateTexture(nil, "ARTWORK")
    lbg:SetPoint("TOPLEFT", 14, -354)
    lbg:SetPoint("BOTTOMRIGHT", -14, 14)
    lbg:SetColorTexture(0, 0, 0, 0.45)
    local log = CreateFrame("ScrollingMessageFrame", nil, f)
    log:SetPoint("TOPLEFT", 20, -358)
    log:SetPoint("BOTTOMRIGHT", -20, 18)
    log:SetFontObject(ChatFontNormal)
    log:SetJustifyH("LEFT")
    log:SetMaxLines(500)
    log:SetFading(false)
    log:EnableMouseWheel(true)
    log:SetScript("OnMouseWheel", function(self, delta)
        if delta > 0 then self:ScrollUp() else self:ScrollDown() end
    end)
    ui.log = log
    f:Hide()   -- CreateFrame frames start visible; the first /uisnap must open it, not hide it
    ui.frame = f
    frame = f

    log:AddMessage("Pick a profile in the list, or type a name and press Save.")
    return f
end

function ns.toggleUI()
    local fresh = not frame
    if fresh then build() end
    if not fresh and frame:IsShown() then
        frame:Hide()
    else
        frame:Show()
        ns.refresh()
        if ns.refreshSettings then ns.refreshSettings() end
    end
end

ns.actions = actions   -- exposed for the mock test
