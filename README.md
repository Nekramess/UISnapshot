# UI Snapshot

Saves your chat windows, selected CVars, Edit Mode layouts and enabled-addon list under a name, so you can restore them on a fresh install. Built for WoW: Forever (interface 16001). Personal-use tool for now.

## Install

Copy the `UISnapshot` folder into `World of Warcraft/_classic_beta_/Interface/AddOns/` (the beta path; the launch path is unconfirmed).

## Window

`/uisnap` (or `/uisnap ui`) opens a window: a list of saved profiles, a name box, and buttons for Save, Load, Diff, Details, Enable addons, Edit Mode strings and Delete, plus a box to track or untrack CVars. Export and Import buttons move a profile as text (see below). Save-over, Load, Delete and replacing an imported profile ask for confirmation. Output appears in the window while it is open. Escape closes it. Two checkboxes control: reload after Load/Enable addons/Import (default on) and the minimap button (default on).

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
| `/uisnap cvars <name>` | Open a box listing every saved game setting and key binding |
| `/uisnap keys <name>` | Open a box listing only the saved key bindings |
| `/uisnap bars` | Print what the game reports for the action bars |
| `/uisnap export <name>` | Open a box with the profile as one block of text |
| `/uisnap import` | Open the paste box (also the Import button) |
| `/uisnap show\|delete <name>`, `/uisnap list` | Inspect, remove, list profiles |
| `/uisnap cvar [add\|remove <name>]` | Choose which CVars are tracked |

## Reload, report and minimap button

After Load, Enable addons and a successful Import, the UI reloads by itself 1.5 seconds later (turn it off with the checkbox). The messages from that run are kept and printed again about 3 seconds after you log back in, so you can see what happened.

The minimap button (gear icon) opens or closes the window on click and can be dragged around the minimap edge. Hide it with the checkbox or `/uisnap minimap off`. It is my own implementation, not a shared library.

## Game settings and action bars

`Save` records every game setting (CVar) that differs from its default, found with `C_Console.GetAllCommands` and `C_CVar.GetCVarInfo`, plus anything on the tracked list, plus which of Action Bars 2-8 are switched on (`GetActionBarToggles`). `Load` sets the ones that differ from the current value, `useUiScale` before `uiScale`, and applies the action bar toggles with `SetActionBarToggles`, which the wiki says registers the state for the next load, so the reload is what makes them show.

Never captured or applied, even from an imported profile: settings that belong to the computer or session, namely names starting with `gx` (graphics device, resolution, window), `last`, `Sound_Output`, `videoOptions`, `hwDetect`, `installType`, `locale`, `textLocale`, `audioLocale`, `accountName`, `portal`, `realm`, `wowVersion`. Locked and read-only CVars are skipped too.

Check what was captured with `/uisnap cvars <name>` (or **View settings**), and compare with `/uisnap diff <name>`. `/uisnap bars` prints what the game reports for the action bars.

Not covered: what is on the action bars, raid frame profiles, anything in addons' own settings. Profiles saved before 0.5.0 only hold the 7 tracked CVars; save them again.

## Key bindings (0.6.0)

`Save` records the keys of every command the game lists (`GetNumBindings` / `GetBinding`), including commands with no key. `Load` clears keys that should not be there, sets the saved ones with `SetBinding`, then calls `SaveBindings` for the binding set that is active (account-wide or character-specific). Not allowed in combat. A saved command the client does not list (an addon that is off) is skipped and reported, so enable the addon and load again. An imported profile can only bind keys to commands the client lists.

Not captured (unverified expectation, not yet tested live): keys bound to spells, macros, items or `CLICK` commands that are not in the game's binding list. Check with `/uisnap diff <name>` and `/uisnap keys <name>`. Profiles saved before 0.6.0 have no key bindings; save again.

## Moving a profile to a new install (Export / Import / Load)
Profiles live in your WTF folder, which a fresh install does not have, so move them as text. **Import only stores the profile; Load is what applies it.** Edit Mode layouts are the one part you paste in by hand.

**On the old install**
1. Open `/uisnap`, select the profile, press **Export**.
2. Press Ctrl+C in the box that opens (click in it first if the text is not highlighted).
3. Paste it into a text file and keep it (tens of thousands of characters for a full UI, so use a text file, not a chat message).
4. Press **Edit Mode strings**, and copy each layout string you want into the same text file (the box shows the layout name above each string).

**On the new install** (UI Snapshot installed and enabled)
1. Open `/uisnap` and press **Import**. Paste the export text, optionally type a name in "Save as" (blank keeps the exported name), press **Import**. This only saves the profile in the addon; nothing in your game has changed yet. The UI reloads and prints what was imported.
2. Open `/uisnap` again, select the imported profile, press **Load**. This applies your chat windows, game settings and key bindings. The UI reloads by itself and prints a report of what changed.
3. Open Edit Mode and use its own Import option to paste your layout string. UI Snapshot cannot apply Edit Mode layouts for you.
4. Type `/reload` once more so everything settles.

If you switch off "Reload the UI after Load..." in the window, type `/reload` yourself after steps 1 and 2.

To copy a profile between characters on the same install, skip Export and Import: just select the profile and press **Load**.

The export starts with `UISNAP1:`, then a length and a checksum, so a cut-off or altered copy is rejected with a message instead of half-importing. Importing never runs the pasted text as code; every field is type- and size-checked, and CVar names are limited to letters, digits and underscores. Only import exports you made or trust: loading a profile sets the CVars it lists (the import message lists them).

## Status

Confirmed in the Forever beta (1 Oct 2026): saving works (chat windows, CVars, addon list, Edit Mode layouts as strings), `/uisnap show` works, and the copy box displays the layout strings.

`load` restored moved chat windows to their saved positions and the custom channels looked right (visual check, 1 Oct 2026).

`diff` and CVar restore also passed a flip-and-restore test (1 Oct 2026).

**0.6.0:** adds key bindings (save, diff, load, export/import). Tested in the Forever beta by the author, 4 Oct 2026 (his report: "i have tested all features"; no per-feature details recorded).

**0.5.1:** fixes the window needing two presses to open (cause: new frames start visible, so the first toggle hid it). Verified in the mock only; not yet confirmed live.

**Untested in the live client (0.5.0):** capturing and restoring all changed game settings, the action bar toggles (including whether they are the setting that controls "enable Action Bar 2" in Forever), the deny list, auto-reload (is `ReloadUI` allowed from addon code?), the post-reload report, the minimap button, Export and Import with ~100 or more CVars in a profile (the text will be longer, which has not been tried through a real clipboard), and the button window beyond screenshots.

Edit Mode layouts are saved as strings but are not applied automatically (an attempt to do that in 0.4.0 did not work in the beta and was removed); paste one into Edit Mode's Import. Profiles live in `WTF/Account/<account>/SavedVariables/UISnapshot.lua` and need to be copied to the new install by hand.
