# UI Snapshot: working notes

Read `claude/wow-forever-addons-overview.md` (project doc) first.

## Layout
- `UISnapshot/UISnapshot.toc`, `UISnapshot.lua` (logic and slash commands) and `EditModeApply.lua` (experimental add-only Edit Mode apply with backups), `Minimap.lua` (own minimap button, no library) and `UI.lua` (button window and import box; wraps `ns.commands`, adds no restore logic) and `Codec.lua` (export text format; pure Lua, no WoW calls). Interface 16001, plain `.toc`, `## SavedVariables: UISnapshotDB`.
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

## Edit Mode apply rules (keep these)
- Add-only, backup first, never overwrite, refuse in combat or with Edit Mode open, pcall every call, fall back to the manual string route.
- Default OFF until the user has watched it work once. Do not turn it on by default without live confirmation.
- `GetLayouts()` lists custom layouts only; `SetActiveLayout` may count presets. The offset is derived from the currently active layout; if that cannot be derived, do not guess.

## Confirmed vs untested (update when you learn more)
- Confirmed in the Forever beta, 1 Oct 2026 (user screenshots/export): `C_EditMode.GetLayouts()` and `ConvertLayoutInfoToString` work (6 custom layouts exported as strings); `GetChatWindowInfo` works (10 windows); all 7 default CVar names returned values; 26 addons listed; `/uisnap save`, `show` and `editmode` ran and the copy box opened and showed the strings.
- Bug found in 0.1.0: "(was active)" never appeared. `GetLayouts().activeLayout` is probably offset by the preset layouts (unconfirmed). 0.1.1 asks `EditModeManagerFrame:GetActiveLayoutInfo()` instead; that call is untested in the live client.
- Confirmed by user test, 1 Oct 2026 (screenshots, visual check only): after `/uisnap save` then moving two chat windows, `/uisnap load` put them back in their saved bottom-centre positions and the custom channels on all three windows looked right.
- Confirmed by user test, 1 Oct 2026: `diff` listed a flipped `chatMouseScroll` CVar, `load` restored it, and a second `diff` reported all CVars match.
- Confirmed in the beta 1 Oct 2026 (user screenshot and report): the button window opens and renders; Save, Delete, list selection and the output log work; saving and loading the UI on another character worked.
- Untested in the live client (0.4.0): auto-reload via `ReloadUI`, post-reload report, minimap button, checkboxes, Edit Mode apply (wiki marks SaveLayouts/SetActiveLayout `AllowedWhenUntainted`; LibEditModeOverride says it cannot create layouts from strings). Also: Export and Import (0.3.0; the clipboard path for ~21,000 characters is the open question), the rest of the button window (0.2.0; the mock frame accepts any method, so it does not prove real widget calls exist), `addons`, the `GetPhysicalScreenSize` warning, dock/undock restore, creating missing chat windows, pasting a saved Edit Mode string into Import, and the 0.1.1 active-layout name.
- `show` prints UI-unit size (`GetScreenWidth/Height`, 4096x1152 at scale 0.667 in the test) and, from 0.1.1, the physical window size.
- Launch install path and whether WTF files carry over are unconfirmed.
