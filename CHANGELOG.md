# Changelog

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
