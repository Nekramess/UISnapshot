-- UI Snapshot: minimap button (own implementation, no library).
-- UNTESTED in the live client. Uses the same textures other minimap buttons use;
-- if one is missing the button still works, it just looks plainer.

local ADDON, ns = ...
local db, say = ns.db, ns.say

local mm = {}
ns.minimap = mm

local button

-- Position on the minimap edge for an angle in radians (pure, tested in the mock).
function mm.position(angle, radius)
    return math.cos(angle) * radius, math.sin(angle) * radius
end

-- Angle from the minimap centre to the cursor (pure).
function mm.angleTo(cx, cy, px, py)
    return math.atan2(py - cy, px - cx)
end

-- Which quadrants of the minimap are round, per the GetMinimapShape convention
-- (https://warcraft.wiki.gg/wiki/GetMinimapShape). Order: bottom-right,
-- bottom-left, top-right, top-left. true = round, false = square corner.
local SHAPES = {
    ["ROUND"] = {true, true, true, true},
    ["SQUARE"] = {false, false, false, false},
    ["CORNER-TOPLEFT"] = {false, false, false, true},
    ["CORNER-TOPRIGHT"] = {false, false, true, false},
    ["CORNER-BOTTOMLEFT"] = {false, true, false, false},
    ["CORNER-BOTTOMRIGHT"] = {true, false, false, false},
    ["SIDE-LEFT"] = {false, true, false, true},
    ["SIDE-RIGHT"] = {true, false, true, false},
    ["SIDE-TOP"] = {false, false, true, true},
    ["SIDE-BOTTOM"] = {true, true, false, false},
    ["TRICORNER-TOPLEFT"] = {false, true, true, true},
    ["TRICORNER-TOPRIGHT"] = {true, false, true, true},
    ["TRICORNER-BOTTOMLEFT"] = {true, true, false, true},
    ["TRICORNER-BOTTOMRIGHT"] = {true, true, true, false},
}
mm.SHAPES = SHAPES

-- Shape name to use: the saved override ("round" or "square") or, in auto mode,
-- whatever the minimap addon reports through GetMinimapShape.
function mm.shape()
    local mode = db().settings.minimap.shape
    if mode == "square" then return "SQUARE" end
    if mode == "round" then return "ROUND" end
    local fn = _G.GetMinimapShape
    if type(fn) == "function" then
        local ok, name = pcall(fn)
        if ok and type(name) == "string" and SHAPES[name:upper()] then return name:upper() end
    end
    return "ROUND"
end

-- Offset from the minimap centre for an angle, following the minimap's shape.
-- halfW/halfH are the distances to the edge the button rides on. Pure.
function mm.shapedPosition(angle, halfW, halfH, shapeName)
    local x, y = math.cos(angle), math.sin(angle)
    local q = 1
    if x < 0 then q = q + 1 end
    if y > 0 then q = q + 2 end
    local quads = SHAPES[shapeName or "ROUND"] or SHAPES.ROUND
    if quads[q] then return x * halfW, y * halfH end
    -- square corner: push out to the box edge instead of the circle
    local dw = math.sqrt(2 * halfW * halfW) - 10
    local dh = math.sqrt(2 * halfH * halfH) - 10
    return math.max(-halfW, math.min(x * dw, halfW)), math.max(-halfH, math.min(y * dh, halfH))
end

local function parent()
    return _G.Minimap or UIParent
end

local function place()
    if not button then return end
    local m = parent()
    local w = m:GetWidth()
    if type(w) ~= "number" then w = 140 end
    local h = m.GetHeight and m:GetHeight()
    if type(h) ~= "number" then h = w end
    local halfW, halfH = w / 2 + 10, h / 2 + 10
    local x, y = mm.shapedPosition(math.rad(db().settings.minimap.angle or 215), halfW, halfH, mm.shape())
    button:ClearAllPoints()
    button:SetPoint("CENTER", m, "CENTER", x, y)
end

local function onDragUpdate(self)
    local m = parent()
    local cx, cy = m:GetCenter()
    local px, py = GetCursorPosition()
    local scale = m:GetEffectiveScale()
    if not (cx and px and scale) then return end
    local angle = mm.angleTo(cx, cy, px / scale, py / scale)
    db().settings.minimap.angle = math.deg(angle) % 360
    place()
end

local function build()
    local b = CreateFrame("Button", "UISnapshotMinimapButton", parent())
    b:SetSize(31, 31)
    b:SetFrameStrata("MEDIUM")
    b:SetFrameLevel(8)
    b:RegisterForClicks("AnyUp")
    b:RegisterForDrag("LeftButton")
    b:SetHighlightTexture("Interface\\Minimap\\UI-Minimap-ZoomButton-Highlight")

    local overlay = b:CreateTexture(nil, "OVERLAY")
    overlay:SetSize(53, 53)
    overlay:SetTexture("Interface\\Minimap\\MiniMap-TrackingBorder")
    overlay:SetPoint("TOPLEFT")
    local back = b:CreateTexture(nil, "BACKGROUND")
    back:SetSize(20, 20)
    back:SetTexture("Interface\\Minimap\\UI-Minimap-Background")
    back:SetPoint("TOPLEFT", 7, -5)
    local icon = b:CreateTexture(nil, "ARTWORK")
    icon:SetSize(17, 17)
    icon:SetTexture("Interface\\Icons\\INV_Misc_Gear_01")
    icon:SetTexCoord(0.05, 0.95, 0.05, 0.95)
    icon:SetPoint("TOPLEFT", 7, -6)

    b:SetScript("OnClick", function(self, mouseButton)
        if self.dragging then return end
        if ns.toggleUI then ns.toggleUI() end
    end)
    b:SetScript("OnDragStart", function(self)
        self.dragging = true
        self:SetScript("OnUpdate", onDragUpdate)
    end)
    b:SetScript("OnDragStop", function(self)
        self:SetScript("OnUpdate", nil)
        -- Let the click that ends a drag pass before clicks count again.
        if C_Timer and C_Timer.After then C_Timer.After(0.05, function() self.dragging = false end)
        else self.dragging = false end
    end)
    b:SetScript("OnEnter", function(self)
        GameTooltip:SetOwner(self, "ANCHOR_LEFT")
        GameTooltip:AddLine("UI Snapshot")
        GameTooltip:AddLine("Click: open or close the window", 1, 1, 1)
        GameTooltip:AddLine("Drag: move around the minimap", 1, 1, 1)
        GameTooltip:Show()
    end)
    b:SetScript("OnLeave", function() GameTooltip:Hide() end)
    button = b
    return b
end

-- Shows or hides the button according to the saved setting.
function mm.apply()
    local hide = db().settings.minimap.hide
    if hide then
        if button then button:Hide() end
        return
    end
    if not button then build() end
    place()
    button:Show()
end

function mm.setShown(shown)
    db().settings.minimap.hide = not shown
    mm.apply()
end

function mm.isShown()
    return not db().settings.minimap.hide
end

function ns.commands.minimap(arg)
    arg = (arg or ""):lower()
    if arg == "square" or arg == "round" or arg == "auto" then
        db().settings.minimap.shape = (arg ~= "auto") and arg or nil
        mm.apply()
        say("Minimap button shape: " .. arg .. (arg == "auto" and " (follows your minimap addon)." or "."))
        return
    end
    if arg == "on" or arg == "show" then mm.setShown(true)
    elseif arg == "off" or arg == "hide" then mm.setShown(false)
    else mm.setShown(not mm.isShown()) end
    say("Minimap button " .. (mm.isShown() and "shown." or "hidden. /uisnap minimap brings it back."))
    if ns.refreshSettings then ns.refreshSettings() end
end

-- Create the button once the game has loaded saved settings and the minimap exists.
local f = CreateFrame("Frame")
f:RegisterEvent("PLAYER_LOGIN")
f:SetScript("OnEvent", function() mm.apply() end)
