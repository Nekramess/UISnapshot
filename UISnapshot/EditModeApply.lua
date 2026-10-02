-- UI Snapshot: EXPERIMENTAL apply of saved Edit Mode layouts.
--
-- STATUS: untested in the live client. The wiki marks C_EditMode.SaveLayouts and
-- SetActiveLayout as "AllowedWhenUntainted", and LibEditModeOverride (an existing
-- addon library) says it cannot create layouts from layout strings, which is what
-- this does. So this may be blocked in Forever. Every call is pcall'd; on any
-- failure nothing is changed and the manual route (/uisnap editmode) still works.
--
-- Safety rules this module keeps:
--  * Add-only: a layout whose name already exists is skipped, never overwritten.
--  * Before writing, every current custom layout is backed up as an export string
--    (UISnapshotDB.editModeBackups, newest 3 kept).
--  * Not in combat, not while Edit Mode is open.
--  * Writes the same structure GetLayouts() returned, with new layouts appended.

local ADDON, ns = ...
local say, db = ns.say, ns.db

local MAX_BACKUPS = 3

local function try(fn, ...)
    local ok, a = pcall(fn, ...)
    if ok then return a end
    return nil, a
end

local function nameIndex(layouts, name)
    for i, l in ipairs(layouts or {}) do
        if l.layoutName == name then return i end
    end
end

local function maxPerType()
    local c = _G.Constants and _G.Constants.EditModeConsts
    return c and c.EditModeMaxLayoutsPerType or nil
end

-- Returns a report: { added = {names}, skipped = {{name, why}}, failed = {{name, why}},
--                     backedUp = n, activated = name|nil, activateNote = string|nil, error = string|nil }
function ns.applyEditMode(profile)
    local report = { added = {}, skipped = {}, failed = {} }
    local function finish(err)
        report.error = err
        if err then say("Edit Mode: " .. err) end
        for _, n in ipairs(report.added) do say("Edit Mode: added layout '" .. n .. "'.") end
        for _, s in ipairs(report.skipped) do say(("Edit Mode: skipped '%s' (%s)."):format(s[1], s[2])) end
        for _, f in ipairs(report.failed) do say(("Edit Mode: could not add '%s' (%s)."):format(f[1], f[2])) end
        if report.activated then say("Edit Mode: active layout set to '" .. report.activated .. "'.") end
        if report.activateNote then say("Edit Mode: " .. report.activateNote) end
        return report
    end

    local saved = profile and profile.editMode and profile.editMode.layouts or {}
    if #saved == 0 then return finish("this profile has no Edit Mode layouts.") end
    local EM = _G.C_EditMode
    if not (EM and EM.GetLayouts and EM.SaveLayouts and EM.ConvertStringToLayoutInfo
            and EM.ConvertLayoutInfoToString) then
        return finish("the Edit Mode layout API is not available here; use /uisnap editmode and paste by hand.")
    end
    if InCombatLockdown() then return finish("not while in combat.") end
    local mgr = _G.EditModeManagerFrame
    if mgr and mgr.IsShown and mgr:IsShown() then return finish("close Edit Mode first, then try again.") end

    local info, err = try(EM.GetLayouts)
    if type(info) ~= "table" or type(info.layouts) ~= "table" then
        return finish("could not read your current layouts (" .. tostring(err) .. "); nothing was changed.")
    end

    -- 1. Back up what is there now.
    local backup = { when = date("%Y-%m-%d %H:%M"), layouts = {} }
    for _, l in ipairs(info.layouts) do
        local str = try(EM.ConvertLayoutInfoToString, l)
        if str then backup.layouts[#backup.layouts + 1] = { name = l.layoutName, str = str, layoutType = l.layoutType } end
    end
    local d = db()
    d.editModeBackups = d.editModeBackups or {}
    table.insert(d.editModeBackups, 1, backup)
    while #d.editModeBackups > MAX_BACKUPS do table.remove(d.editModeBackups) end
    report.backedUp = #backup.layouts

    -- 2. Append the missing layouts.
    local perType = {}
    for _, l in ipairs(info.layouts) do perType[l.layoutType] = (perType[l.layoutType] or 0) + 1 end
    local cap = maxPerType()
    local newNames = {}
    for _, l in ipairs(saved) do
        local lt = l.layoutType == 2 and 2 or 1
        if nameIndex(info.layouts, l.name) then
            report.skipped[#report.skipped + 1] = { l.name, "a layout with that name already exists; left as it is" }
        elseif cap and (perType[lt] or 0) >= cap then
            report.skipped[#report.skipped + 1] = { l.name, "you already have the maximum of " .. cap .. " of that kind" }
        else
            local li, cerr = try(EM.ConvertStringToLayoutInfo, l.str)
            if type(li) == "table" then
                li.layoutName = l.name
                li.layoutType = lt
                info.layouts[#info.layouts + 1] = li
                perType[lt] = (perType[lt] or 0) + 1
                newNames[#newNames + 1] = l.name
            else
                report.failed[#report.failed + 1] = { l.name, "string not accepted: " .. tostring(cerr) }
            end
        end
    end

    -- 3. Save (only if something was added).
    if #newNames > 0 then
        local ok, serr = pcall(EM.SaveLayouts, info)
        if not ok then
            for _, n in ipairs(newNames) do report.failed[#report.failed + 1] = { n, "save was refused: " .. tostring(serr) } end
            return finish("saving layouts failed (" .. tostring(serr) .. "); nothing was changed. Use /uisnap editmode and paste by hand.")
        end
        for _, n in ipairs(newNames) do report.added[#report.added + 1] = n end
    end

    -- 4. Activate the layout that was active when the profile was saved.
    local target = profile.editMode.active
    if target and EM.SetActiveLayout then
        local fresh = try(EM.GetLayouts)
        local custom = fresh and fresh.layouts or {}
        local tIdx = nameIndex(custom, target)
        if not tIdx then
            report.activateNote = "'" .. target .. "' was the active layout but is not among your layouts; pick one in Edit Mode."
        else
            -- GetLayouts lists custom layouts only, while SetActiveLayout may count the
            -- preset layouts too. Work out the offset from the layout that is active now.
            local cur = mgr and mgr.GetActiveLayoutInfo and try(mgr.GetActiveLayoutInfo, mgr)
            local curIdx = type(cur) == "table" and nameIndex(custom, cur.layoutName)
            if curIdx and fresh.activeLayout then
                if cur.layoutName == target then
                    report.activateNote = "'" .. target .. "' is already the active layout."
                else
                    local offset = fresh.activeLayout - curIdx
                    local ok = pcall(EM.SetActiveLayout, tIdx + offset)
                    if ok then
                        report.activated = target
                    else
                        report.activateNote = "could not switch the active layout; pick '" .. target .. "' in Edit Mode."
                    end
                end
            else
                report.activateNote = "could not work out the layout numbering; pick '" .. target .. "' in Edit Mode."
            end
        end
    end
    return finish(nil)
end

function ns.commands.applyeditmode(name)
    local p = name and db().profiles[name]
    if not p then say("No profile named '" .. tostring(name) .. "'. /uisnap list"); return end
    ns.beginCapture()
    ns.applyEditMode(p)
    ns.afterChange(ns.endCapture())
end

-- Lists backups so a layout can be recovered: /uisnap backups
function ns.commands.backups()
    local b = db().editModeBackups or {}
    if #b == 0 then say("No Edit Mode backups yet. One is made automatically before any Edit Mode apply."); return end
    for i, entry in ipairs(b) do
        say(("Backup %d: %s, %d layouts. /uisnap backup %d opens the strings."):format(i, entry.when or "?", #entry.layouts, i))
    end
end

function ns.commands.backup(arg)
    local i = tonumber(arg) or 1
    local entry = (db().editModeBackups or {})[i]
    if not entry then say("No backup number " .. tostring(arg)); return end
    local parts = {}
    for _, l in ipairs(entry.layouts) do
        parts[#parts + 1] = "-- layout: " .. tostring(l.name)
        parts[#parts + 1] = l.str
    end
    ns.showCopyBox("Edit Mode backup " .. i .. " (" .. tostring(entry.when) .. ")", table.concat(parts, "\n"))
end
