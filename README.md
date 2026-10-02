# UI Snapshot

Saves your chat windows, selected CVars, Edit Mode layouts and enabled-addon list under a name, so you can restore them on a fresh install. Built for WoW: Forever (interface 16001). Personal-use tool for now.

## Install

Copy the `UISnapshot` folder into `World of Warcraft/_classic_beta_/Interface/AddOns/` (the beta path; the launch path is unconfirmed).

## Window

`/uisnap` (or `/uisnap ui`) opens a window: a list of saved profiles, a name box, and buttons for Save, Load, Diff, Details, Enable addons, Edit Mode strings and Delete, plus a box to track or untrack CVars. Save-over, Load and Delete ask for confirmation. Output appears in the window while it is open. Escape closes it.

## Commands (also work typed)

| Command | Does |
|---|---|
| `/uisnap` or `/uisnap ui` | Open or close the window |
| `/uisnap save <name>` | Capture the current setup |
| `/uisnap load <name>` | Re-apply chat windows and CVars (not in combat), then `/reload` |
| `/uisnap diff <name>` | Show addons and CVars that differ from the profile |
| `/uisnap addons <name>` | Enable the saved addons that are installed but off |
| `/uisnap editmode <name>` | Open a copy box with the saved Edit Mode layout strings |
| `/uisnap show\|delete <name>`, `/uisnap list` | Inspect, remove, list profiles |
| `/uisnap cvar [add\|remove <name>]` | Choose which CVars are tracked |

## Status

Confirmed in the Forever beta (1 Oct 2026): saving works (chat windows, CVars, addon list, Edit Mode layouts as strings), `/uisnap show` works, and the copy box displays the layout strings.

`load` restored moved chat windows to their saved positions and the custom channels looked right (visual check, 1 Oct 2026).

`diff` and CVar restore also passed a flip-and-restore test (1 Oct 2026).

**Untested in the live client:** the button window (new in 0.2.0, only run against a simulated client), `addons`, dock/undock restore, active-layout detection (fixed in 0.1.1), and the resolution-change warning. Tests run only against a simulated client (`python3 tests/mock_test.py`, Lua 5.1).

Edit Mode layouts are saved as strings but are not applied automatically; paste one into Edit Mode's Import. Profiles live in `WTF/Account/<account>/SavedVariables/UISnapshot.lua` and need to be copied to the new install by hand.
