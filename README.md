# UI Snapshot

Saves your chat windows, selected CVars, Edit Mode layouts and enabled-addon list under a name, so you can restore them on a fresh install. Built for WoW: Forever (interface 16001). Personal-use tool for now.

## Install

Copy the `UISnapshot` folder into `World of Warcraft/_classic_beta_/Interface/AddOns/` (the beta path; the launch path is unconfirmed).

## Commands

| Command | Does |
|---|---|
| `/uisnap save <name>` | Capture the current setup |
| `/uisnap load <name>` | Re-apply chat windows and CVars (not in combat), then `/reload` |
| `/uisnap diff <name>` | Show addons and CVars that differ from the profile |
| `/uisnap addons <name>` | Enable the saved addons that are installed but off |
| `/uisnap editmode <name>` | Open a copy box with the saved Edit Mode layout strings |
| `/uisnap show\|delete <name>`, `/uisnap list` | Inspect, remove, list profiles |
| `/uisnap cvar [add\|remove <name>]` | Choose which CVars are tracked |

## Status

Confirmed in the Forever beta (screenshot, 1 Oct 2026): `C_EditMode` and `C_EditMode.GetLayouts()` exist, and `GetChatWindowInfo(1)` returns 10 values.

Everything else is **untested in the live client**: chat position/dock/channel restore, CVar restore, addon enabling, the copy box. Tests run only against a simulated client (`python3 tests/mock_test.py`, Lua 5.1).

Edit Mode layouts are saved as strings but are not applied automatically; paste them into Edit Mode's Import. Profiles live in `WTF/Account/<account>/SavedVariables/UISnapshot.lua` and need to be copied to the new install by hand.
