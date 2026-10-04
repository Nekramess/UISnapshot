# CurseForge listing for UI Snapshot (copy these into the project form)

| Field | Value |
|---|---|
| Name | UI Snapshot |
| Game / Class | World of Warcraft / Addons |
| Main category | Chat & Communication or Miscellaneous (pick what the dropdown offers; Miscellaneous is safe) |
| Summary | Save your chat windows, game settings, Edit Mode layouts and addon list under a name, then restore or export them on a fresh install. |
| License | MIT |
| Logo | `docs/logo.png` (400x400 PNG, original artwork, same style as the other addons) |
| File | `UISnapshot-v0.5.1-forever.zip` (from `tools/package.sh`) |
| Game version | WoW Forever 1.60.1 (the version Chronicle Forever's listing shows; confirm it is in the dropdown) |
| Release type | Release |
| Changelog | `CHANGELOG.md`, 0.5.1 section |
| Source link | https://github.com/Nekramess/UISnapshot |

Release type: CurseForge's app only syncs a project once it has a Release file. Beta is the honest label while action-bar restore and Export/Import with large profiles are untested live; switch to Release when you are happy.

License: CurseForge requires one. Options: MIT (anyone may reuse), or All Rights Reserved (what Chronicle Forever uses). Either is allowed; it is your decision, so I did not add a LICENSE file.

Screenshots: add your screenshot of the window (the one you sent earlier). Not required for addons.

## Description (paste into the description box; headings and lists survive CurseForge's editor)

**UI Snapshot saves your whole configured UI under a name and puts it back on a fresh install or another character.**

You spend hours tuning chat windows, game settings and Edit Mode layouts. UI Snapshot records them in one click, and restores them in one click.

### What it saves
- Chat windows: names, positions, sizes, docking, message groups and channels
- Game settings (CVars) that differ from the defaults, including which Action Bars 2-8 are switched on
- Your key bindings (every command the game lists, including keys you removed)
- Your Edit Mode layouts, saved as text strings
- The list of enabled addons

### What it does not save
What is on your action bars, keys bound directly to spells or macros (not confirmed), raid frame profiles, and other addons' own settings. Edit Mode layouts are saved but not applied automatically; you paste them into Edit Mode's own Import box (see below).

### Open it
Type `/uisnap`, or click the gear button on the minimap (drag it to move it; it can be turned off in the window).

### Save and load on the same install
1. Open the window, type a name, press **Save**.
2. On another character, select the profile and press **Load**. The UI reloads by itself and prints a report of what changed.

### Export and import (move a profile to a new install)
Profiles live in your WTF folder, which a fresh install does not have, so use text:

**Export (old install)**
1. Open `/uisnap`, select the profile, press **Export**.
2. Press Ctrl+C in the box that opens (click in it first if the text is not highlighted).
3. Paste it into a text file and keep it (tens of thousands of characters for a full UI, so use a text file, not a chat message).

**Import (new install)**
1. Open `/uisnap` and press **Import**.
2. Paste the text. Optionally type a name in "Save as" (blank keeps the exported name).
3. Press **Import**. The UI reloads and prints a report.

**Edit Mode layouts:** select the profile and press **Edit Mode strings**. Copy one string, then open Edit Mode, use its layout menu's Import option, and paste it.

A cut-off or altered export is rejected with a message instead of half-importing.

### Safety
- Imports are read as data only; pasted text is never run as code.
- Every imported field is type- and size-checked.
- Key bindings can only be set on commands the game lists; an import cannot bind a key to a macro or script.
- Settings tied to your computer (graphics device, resolution, sound output, locale, account and realm) are never saved or applied.
- Only import text you made or trust: loading a profile sets the game settings it lists, and the import message names them.

### Commands
`/uisnap` open or close the window, `save <name>`, `load <name>`, `diff <name>` (what differs from now), `export <name>`, `import`, `list`, `show <name>`, `delete <name>`, `cvars <name>`, `keys <name>`, `editmode <name>`, `addons <name>`, `minimap on|off`.

### Status (Forever beta, interface 16001)
Confirmed working in the Forever beta: saving, loading chat windows and channels, restoring changed settings, the window and minimap button opening, Export/Import of a profile.
Not yet confirmed live: restoring key bindings, restoring Action Bar toggles, automatic reload after load, and Export/Import of very large profiles through the clipboard. Please report problems on GitHub.

Free and open source (MIT): https://github.com/Nekramess/UISnapshot
