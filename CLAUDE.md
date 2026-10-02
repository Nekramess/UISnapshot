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
- Confirmed in beta 1 Oct 2026 (user screenshot): `C_EditMode`, `C_EditMode.GetLayouts()`, `GetChatWindowInfo(1)` returns 10 values.
- Untested in the live client: everything else, including `ConvertLayoutInfoToString`, chat restore, CVar restore, `C_AddOns` calls, the copy box.
- The default tracked CVar list is a guess; names that return nil are skipped.
- Launch install path and whether WTF files carry over are unconfirmed.
