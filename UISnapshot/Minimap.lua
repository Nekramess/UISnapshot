-- UI Snapshot: minimap button, registered through the standard LibDBIcon-1.0 library
-- (embedded in Libs/), so minimap button managers treat it as a normal button instead of
-- flagging it as a custom one. LibDBIcon also follows square and other non-round minimaps
-- through GetMinimapShape. UNTESTED in the live client.

local ADDON, ns = ...
local db, say = ns.db, ns.say

local mm = {}
ns.minimap = mm

local ICON_NAME = "UISnapshot"

local LDB = LibStub and LibStub("LibDataBroker-1.1", true)
local DBIcon = LibStub and LibStub("LibDBIcon-1.0", true)
local registered = false

-- Saved settings. LibDBIcon keeps the angle in `minimapPos` (degrees) and the hidden flag
-- in `hide`. Settings from older versions used `angle` and `shape`; the angle carries over.
local function cfg()
    local s = db().settings
    local c = s.minimap
    if type(c) ~= "table" then c = {}; s.minimap = c end
    if c.minimapPos == nil then c.minimapPos = tonumber(c.angle) or 215 end
    c.angle, c.shape = nil, nil
    c.hide = c.hide and true or false
    return c
end

local function register()
    if registered or not (LDB and DBIcon) then return end
    local obj = LDB:NewDataObject(ICON_NAME, {
        type = "launcher",
        text = "UI Snapshot",
        icon = "Interface\\Icons\\INV_Misc_Gear_01",
        OnClick = function()
            if ns.toggleUI then ns.toggleUI() end
        end,
        OnTooltipShow = function(tt)
            tt:AddLine("UI Snapshot")
            tt:AddLine("Click: open or close the window", 1, 1, 1)
            tt:AddLine("Drag: move around the minimap", 1, 1, 1)
        end,
    })
    DBIcon:Register(ICON_NAME, obj, cfg())
    registered = true
end

-- Shows or hides the button according to the saved setting.
function mm.apply()
    register()
    if not registered then return end
    DBIcon:Refresh(ICON_NAME, cfg())
end

function mm.setShown(shown)
    cfg().hide = not shown
    mm.apply()
end

function mm.isShown()
    return not cfg().hide
end

-- /uisnap minimap [on|off]
function ns.commands.minimap(arg)
    arg = (arg or ""):lower()
    if arg == "on" or arg == "show" then mm.setShown(true)
    elseif arg == "off" or arg == "hide" then mm.setShown(false)
    else mm.setShown(not mm.isShown()) end
    say("Minimap button " .. (mm.isShown() and "shown." or "hidden. /uisnap minimap brings it back."))
    if ns.refreshSettings then ns.refreshSettings() end
end

-- Register once the game has loaded saved settings.
local f = CreateFrame("Frame")
f:RegisterEvent("PLAYER_LOGIN")
f:SetScript("OnEvent", function() mm.apply() end)
