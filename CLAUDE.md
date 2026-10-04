# UI Snapshot: working notes

Read `claude/wow-forever-addons-overview.md` (project doc) first.

## Layout
- `UISnapshot/UISnapshot.toc`, `UISnapshot.lua` (logic and slash commands) and `Minimap.lua` (own minimap button, no library) and `UI.lua` (button window and import box; wraps `ns.commands`, adds no restore logic) and `Codec.lua` (export text format; pure Lua, no WoW calls). Interface 16001, plain `.toc`, `## SavedVariables: UISnapshotDB`.
- `tests/codec_test.py`: round-trip, damage and fuzz tests for `Codec.lua` under Lua 5.1.
- `tests/mock_test.py`: runs the Lua under Lua 5.1 (lupa) against a simulated client. Not the live client.
- `tools/package.sh`, `.github/workflows/package.yml`: build `UISnapshot-v<Version>-forever.zip` from the `.toc` version.

## Conventions
- Every client call that might not exist in Forever goes through `pcall`/existence checks; one failure must not abort a save or load.
- Edit Mode layouts are saved as strings and pasted by hand; do not apply them from code (taint risk, untested).
- Bump `## Version` for every release; never re-upload a version under a new name.
- Never commit to `main`: branch, PR, Anthony merges.

## Import safety rules (keep these)
- Never `loadstring`/execute pasted text. `Codec.decode` is a data parser only.
- Everything imported goes through `sanitizeProfile` (known fields only, types and sizes checked, CVar names `^[%w_]+$`). Add new profile fields there or they are dropped on import.
- Edit Mode layouts are still never applied from code, imported or not.

## Edit Mode
- Auto-applying Edit Mode layouts was tried in 0.4.0 (add-only, with backups) and did not work in the beta (user report, 1 Oct 2026), so it was removed. Do not re-add it without a verified approach: the wiki marks `C_EditMode.SaveLayouts`/`SetActiveLayout` `AllowedWhenUntainted`, and LibEditModeOverride says it cannot create layouts from strings. Layouts stay manual (saved as strings, pasted into Edit Mode's Import).

## Game settings rules (keep these)
- Capture = every CVar changed from default (via `C_Console.GetAllCommands` + `C_CVar.GetCVarInfo`) plus the tracked list, minus the deny list. The deny list also applies on load, so an imported profile cannot set machine-specific settings.
- Importing must not add names to the tracked list (it did in 0.3.0 and polluted it).
- Action bars: `GetActionBarToggles`/`SetActionBarToggles`; the second only registers state for the next load, so it needs the reload. Slot `i` is shown as "Action Bar i+1" (naming from the wiki's description, not verified in Forever).

## Key binding rules (keep these)
- Entries are `COMMAND key1 key2` strings, space separated (not tab: tabs may not survive the game's edit boxes). Names with spaces, control characters or `|` are skipped on capture and dropped on import.
- Load only touches commands the client lists now, so an imported profile cannot bind a key to `MACRO`, `CLICK`, `RUNSCRIPT` or anything else unlisted.
- Order: unbind keys that should not be there, then bind, then `SaveBindings(GetCurrentBindingSet())`. Not in combat.
- Spell/macro/item bindings are probably not in the `GetBinding` list (unverified); 0.6.0 does not capture them.
- `tests/keybind_test.py` (30 checks, mutation-checked) covers this against a simulated binding API; nothing here is confirmed in the live client yet.

## Window lessons (keep these)
- Frames from `CreateFrame` start SHOWN in the real client. Any lazily built frame must `Hide()` at the end of its build, or a build-then-toggle opens-then-hides it (0.5.0 needed two presses; fixed in 0.5.1, user report 4 Oct 2026; the fix is verified only in the mock until the user confirms).
- `tests/mock_env.py` is the shared mock client (its frames start shown, like the real one). `tests/first_open_test.py` checks first-use behaviour on fresh runtimes; it fails (9 checks) against the 0.5.0 `UI.lua`.

## Confirmed vs untested (update when you learn more)
- Confirmed in the Forever beta, 1 Oct 2026 (user screenshots/export): `C_EditMode.GetLayouts()` and `ConvertLayoutInfoToString` work (6 custom layouts exported as strings); `GetChatWindowInfo` works (10 windows); all 7 default CVar names returned values; 26 addons listed; `/uisnap save`, `show` and `editmode` ran and the copy box opened and showed the strings.
- Bug found in 0.1.0: "(was active)" never appeared. `GetLayouts().activeLayout` is probably offset by the preset layouts (unconfirmed). 0.1.1 asks `EditModeManagerFrame:GetActiveLayoutInfo()` instead; that call is untested in the live client.
- Confirmed by user test, 1 Oct 2026 (screenshots, visual check only): after `/uisnap save` then moving two chat windows, `/uisnap load` put them back in their saved bottom-centre positions and the custom channels on all three windows looked right.
- Confirmed by user test, 1 Oct 2026: `diff` listed a flipped `chatMouseScroll` CVar, `load` restored it, and a second `diff` reported all CVars match.
- Confirmed in the beta 1 Oct 2026 (user screenshot and report): the button window opens and renders; Save, Delete, list selection and the output log work; saving and loading the UI on another character worked.
- Confirmed in the beta 1 Oct 2026 (user): chat windows restored to the right places on the new character; action bars (and other game settings) were NOT restored in 0.4.0 because only 7 CVars were tracked. 0.5.0 fixes that in code; not yet seen working live.
- Untested in the live client (0.6.0): key binding capture/diff/load, `SaveBindings`, whether spell/macro bindings are listed.
- Untested in the live client (0.5.0): capture/restore of all changed CVars, action bar toggles, the deny list, auto-reload via `ReloadUI`, post-reload report, minimap button, Export/Import with large profiles.
- `show` prints UI-unit size (`GetScreenWidth/Height`, 4096x1152 at scale 0.667 in the test) and, from 0.1.1, the physical window size.
- Launch install path and whether WTF files carry over are unconfirmed.
