# UI Snapshot: working notes

Read `claude/wow-forever-addons-overview.md` (project doc) first.

## Layout
- `UISnapshot/UISnapshot.toc` and `UISnapshot.lua`: the whole addon. Interface 16001, plain `.toc`, `## SavedVariables: UISnapshotDB`.
- `tests/mock_test.py`: runs the Lua under Lua 5.1 (lupa) against a simulated client. Not the live client.
- `tools/package.sh`, `.github/workflows/package.yml`: build `UISnapshot-v<Version>-forever.zip` from the `.toc` version.

## Conventions
- Every client call that might not exist in Forever goes through `pcall`/existence checks; one failure must not abort a save or load.
- Edit Mode layouts are saved as strings and pasted by hand; do not apply them from code (taint risk, untested).
- Bump `## Version` for every release; never re-upload a version under a new name.
- Never commit to `main`: branch, PR, Anthony merges.

## Confirmed vs untested (update when you learn more)
- Confirmed in the Forever beta, 1 Oct 2026 (user screenshots/export): `C_EditMode.GetLayouts()` and `ConvertLayoutInfoToString` work (6 custom layouts exported as strings); `GetChatWindowInfo` works (10 windows); all 7 default CVar names returned values; 26 addons listed; `/uisnap save`, `show` and `editmode` ran and the copy box opened and showed the strings.
- Bug found in 0.1.0: "(was active)" never appeared. `GetLayouts().activeLayout` is probably offset by the preset layouts (unconfirmed). 0.1.1 asks `EditModeManagerFrame:GetActiveLayoutInfo()` instead; that call is untested in the live client.
- Untested in the live client: `load`, `diff`, `addons`, chat position/dock/channel restore, CVar restore, `GetPhysicalScreenSize` warning.
- `show` prints UI-unit size (`GetScreenWidth/Height`, 4096x1152 at scale 0.667 in the test) and, from 0.1.1, the physical window size.
- Launch install path and whether WTF files carry over are unconfirmed.
