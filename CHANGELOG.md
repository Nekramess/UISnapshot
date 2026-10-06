# Changelog

## 0.6.7
- The minimap button now follows a square (or other non-round) minimap: it uses `GetMinimapShape`, which minimap addons define, the same way other addon buttons do. `/uisnap minimap square`, `round` or `auto` overrides it if your minimap addon does not report its shape. Not yet seen in the live client.

## 0.6.6
- New "Reload UI" button in the window (same as `/reload`; refuses in combat). Handy after pasting an Edit Mode layout.

## 0.6.5
- `agentUID`, `engineSurvey*` and `currentGameMode` are never saved or applied (they describe the install or client, not your preferences; seen in a real Forever export). Profiles that already contain them skip them on Load.

## 0.6.4
- View settings, Diff, Find and Changed now show `|` doubled and odd bytes as `?`, so settings with unusual characters (for example `nameplateStackingTypes`) cannot garble the output or blank the View settings box.

## 0.6.3
- Fix: the Export box could open empty (seen with a 23,808-character export of a full 0.6.2 profile). Exports are now plain printable ASCII (`UISNAP1E:`): any unusual character in a saved setting, plus `|` and `~`, is written as `~HH`. Older `UISNAP1:` exports still import.
- Export warns if the box holds fewer characters than the export, and names saved settings that contained unusual characters.

## 0.6.2
- Fix: on Forever, Save only captured the 7 tracked settings, because the list of all settings is `ConsoleGetAllCommands` there, not `C_Console.GetAllCommands`. Save now reads the full list, so every changed setting is captured. Save again to get them.
- Damage Meter, Damage Meter auto-reset, Swing Timer and Cooldown Manager are always saved.
- Save prints a warning if the full list cannot be read; `/uisnap watch` says why.

## 0.6.1
- New `/uisnap find <text> [profile]`, `/uisnap watch` and `/uisnap changed` to find which CVar a game setting uses (for settings like Damage Meter whose CVar name is not documented) and whether Save captures it.

## 0.6.0
- Save, diff, load and export/import key bindings (all commands the game lists; keys that should not be bound are cleared). `/uisnap keys <name>` lists them; the settings view includes them.

## 0.5.1
- Fix: the window needed two presses (minimap button or `/uisnap`) before it opened.

## 0.5.0
- Capture and restore every changed game setting (CVar) plus Action Bar 2-8 toggles; deny list for machine-specific settings.
- Edit Mode auto-apply removed (did not work in the beta); layouts stay as strings to paste into Edit Mode's Import.

## 0.4.x
- Button window, Export/Import as text, automatic reload after Load/Import, minimap button.

## 0.1.x - 0.3.x
- Save, load, diff, addon list and Edit Mode layout strings.
