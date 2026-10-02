# UI Snapshot

Saves your chat windows, selected CVars, Edit Mode layouts and enabled-addon list under a name, so you can restore them on a fresh install. Built for WoW: Forever (interface 16001). Personal-use tool for now.

## Install

Copy the `UISnapshot` folder into `World of Warcraft/_classic_beta_/Interface/AddOns/` (the beta path; the launch path is unconfirmed).

## Window

`/uisnap` (or `/uisnap ui`) opens a window: a list of saved profiles, a name box, and buttons for Save, Load, Diff, Details, Enable addons, Edit Mode strings and Delete, plus a box to track or untrack CVars. Export and Import buttons move a profile as text (see below). Save-over, Load, Delete and replacing an imported profile ask for confirmation. Output appears in the window while it is open. Escape closes it. Three checkboxes control: reload after Load/Enable addons/Import (default on), apply Edit Mode layouts on Load (default off, experimental), and the minimap button (default on).

## Commands (also work typed)

| Command | Does |
|---|---|
| `/uisnap` or `/uisnap ui` | Open or close the window |
| `/uisnap save <name>` | Capture the current setup |
| `/uisnap load <name>` | Re-apply chat windows and CVars (not in combat), then `/reload` |
| `/uisnap diff <name>` | Show addons and CVars that differ from the profile |
| `/uisnap addons <name>` | Enable the saved addons that are installed but off |
| `/uisnap editmode <name>` | Open a copy box with the saved Edit Mode layout strings |
| `/uisnap minimap [on\|off]` | Show, hide or toggle the minimap button |
| `/uisnap applyeditmode <name>` | Add the profile's Edit Mode layouts to the game (experimental) |
| `/uisnap backups`, `/uisnap backup <n>` | List or open the automatic Edit Mode backups |
| `/uisnap export <name>` | Open a box with the profile as one block of text |
| `/uisnap import` | Open the paste box (also the Import button) |
| `/uisnap show\|delete <name>`, `/uisnap list` | Inspect, remove, list profiles |
| `/uisnap cvar [add\|remove <name>]` | Choose which CVars are tracked |

## Reload, report and minimap button

After Load, Enable addons and a successful Import, the UI reloads by itself 1.5 seconds later (turn it off with the checkbox). The messages from that run are kept and printed again about 3 seconds after you log back in, so you can see what happened.

The minimap button (gear icon) opens or closes the window on click and can be dragged around the minimap edge. Hide it with the checkbox or `/uisnap minimap off`. It is my own implementation, not a shared library.

## Edit Mode auto-apply (experimental)

Without it, you paste each layout into Edit Mode's own Import by hand. With **Apply Edit Mode** (button, `/uisnap applyeditmode <name>`, or the Load checkbox) the addon tries to add the saved layouts itself. It is built to be harmless if it fails:

- **Add-only.** A layout whose name already exists is skipped, never overwritten.
- **Backup first.** Your current layouts are saved as export strings before anything is written (newest 3 kept; `/uisnap backups`).
- **Refuses** in combat and while Edit Mode is open.
- **Falls back.** If the game refuses the save, nothing is changed and the message points you to `/uisnap editmode` for the manual paste.

It may simply be blocked: the wiki marks `C_EditMode.SaveLayouts` and `SetActiveLayout` as `AllowedWhenUntainted`, and the LibEditModeOverride library says it cannot create layouts from layout strings. Test it by hand once before turning on the Load checkbox.

## Moving a profile to a new install (Export / Import)

Profiles live in `WTF\Account\<account>\SavedVariables\UISnapshot.lua`, which a fresh install does not have. To carry one over without copying files:

1. In the old install: select the profile, press **Export**, press Ctrl+C in the box, and paste it into a text file you keep (about 20,000 characters for a full UI).
2. In the new install: press **Import**, paste, press Import. Blank "Save as" keeps the exported name.

The export starts with `UISNAP1:`, then a length and a checksum, so a cut-off or altered copy is rejected with a message instead of half-importing. Importing never runs the pasted text as code; every field is type- and size-checked, and CVar names are limited to letters, digits and underscores. Only import exports you made or trust: loading a profile sets the CVars it lists (the import message lists them).

## Status

Confirmed in the Forever beta (1 Oct 2026): saving works (chat windows, CVars, addon list, Edit Mode layouts as strings), `/uisnap show` works, and the copy box displays the layout strings.

`load` restored moved chat windows to their saved positions and the custom channels looked right (visual check, 1 Oct 2026).

`diff` and CVar restore also passed a flip-and-restore test (1 Oct 2026).

**Untested in the live client (0.4.0):** auto-reload (is `ReloadUI` allowed from addon code in Forever?), the post-reload report, the minimap button (look, position, drag), the three checkboxes, and Edit Mode auto-apply (may be blocked, see above). Also: Export and Import (new in 0.3.0; the text format has been tested heavily in a simulated client, but copying ~20,000 characters out of and into a real game edit box has not), the button window beyond a screenshot of it opening, `addons`, dock/undock restore, active-layout detection (fixed in 0.1.1), and the resolution-change warning. Tests run only against a simulated client (`python3 tests/mock_test.py`, Lua 5.1).

Edit Mode layouts are saved as strings but are not applied automatically; paste one into Edit Mode's Import. Profiles live in `WTF/Account/<account>/SavedVariables/UISnapshot.lua` and need to be copied to the new install by hand.
