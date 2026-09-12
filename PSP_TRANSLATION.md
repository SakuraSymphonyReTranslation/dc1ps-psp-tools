# D.C.P.S. (Da Capo Plus Situation Portable) - Translation & Tooling Documentation

Title ID: `NPJH50731` / `ULJM05718`
Corpus Source: PC *Da Capo Plus Communication* (`E:\Games\Da Capo Plus Communication`)

---

## 1. Executive Summary

This document serves as the single source of truth for the English port of **D.C.P.S. (Da Capo 1 Plus Situation Portable)**, matching the standard established in the DC2 PSP project.

### Pipeline Status: COMPLETE & VERIFIED
- **Script Extraction & Token Analysis**: 1,046 script blobs inside container `PSP_GAME/USRDIR/data/script.bin`.
- **Scene Mapping**: 334 paired scenes matched between PC English and PSP Japanese (`analysis/scene_pairs.json`).
- **Dialogue Alignment & Recovery**: 25,353 matched lines (up from 22,049) with 1:1 lockstep scene pairing and expanded multi-speaker tag resolution (`output/transfer.json`).
- **Script Rebuild & Relocation**: 31,877 replacements (dialogue + choices + names) spliced into `work/script_en.bin` with **9,009 relative jumps re-anchored** (0 mismatches, 100% verified target opcodes).
- **Choice Restoration**: Fixed regex/period heuristic filter in `dc1_transfer.py` restoring all 290+ player interactive choices.
- **Font Optimization**: `PSP_GAME/USRDIR/data/font.pgf` shrunk from 18px to 13.5px (scale 0.75) to prevent English text overflow.
- **Protagonist Default Name**: Decrypted EBOOT patched (`朝倉 純一` -> `Asakura Junichi`) across all 3 engine reference points (`0x099B70`, `0x099B78`, `0x09A2E0`).
- **System UI Translation**: 57 system menu, confirmation, name prompt, and save/load strings translated directly in the EBOOT ELF.
- **Patched ISO Built**: `output/D.C.P.S. [NPJH50731]_en.iso` verified with byte-accurate re-extraction and hash matching.

---

## 2. Directory Structure

```text
F:\Games\PSP\dc1ps-psp-tools\
├── analysis\
│   ├── dc1_script.json            # Extracted PSP script dump
│   ├── dc1_script.index.json      # Structural token and opcode index
│   ├── scene_pairs.json           # 334 EN <-> PSP scene mapping pairs
│   └── line_align.json            # Dialogue line alignment mappings
├── output\
│   ├── transfer.json              # Ready-to-inject text replacements
│   ├── D.C.P.S. [NPJH50731]_en.iso  # Definitive full English ISO build
│   ├── D.C.P.S. [NPJH50731]_en1.iso # Baseline script+font build
│   └── D.C.P.S. [NPJH50731]_en2.iso # Synced full build (+ EBOOT patch)
├── tools\
│   ├── dc1_iso.py                 # ISO unpacker, replacer, and relocator
│   ├── dc1_script.py              # DC1 container and token parser
│   ├── line_align.py              # Sequence aligner for EN/JP dialogue
│   ├── dc1_transfer.py            # Text normalization, wrapping, transfer builder
│   ├── dc1_import.py              # Script blob rebuilder & jump re-anchor tool
│   ├── dc1_eboot_patch.py         # EBOOT ELF patcher for names and UI strings
│   └── verify_rebuild.py          # Structural & jump integrity validator
└── work\
    ├── extracted\                 # Extracted original assets (script, font, EBOOT)
    ├── script_en.bin              # Rebuilt English script container
    └── eboot_patched.elf          # Patched English ELF executable (1,426,736 B)
```

---

## 3. Protagonist Default Name & [name] Handling

### The Problem
In Japanese D.C.P.S., the protagonist name defaults to **朝倉 純一** (*Asakura Jun'ichi*). In dialogue scripts, the game engine uses the literal placeholder `[name]`. When rendered, the engine substitutes the player's custom name (defaulting to the given name stored in the save/engine state).

On PC, the translation mapped `$n` to `Junichi` / `Asakura`. On PSP, dialogue lines referencing `$n` were aligned to PSP narration/dialogue, and inline `$n` was converted to `[name]`.

### The EBOOT Solution
PPSSPP's `DumpFileTypes = 255` setting dumped the decrypted ELF (`ULJM05718_EBOOT.BIN`, 1,426,736 bytes). Analysis located the critical reference points:
1. `0x099B70` (Given Name): `8f 83 88 ea 00 00 00 00` (`純一\0\0\0\0`) -> `Junichi\0` (`4a 75 6e 69 63 68 69 00`)
2. `0x099B78` (Surname): `92 a9 91 71 00 00 00 00` (`朝倉\0\0\0\0`) -> `Asakura\0` (`41 73 61 6b 75 72 61 00`)
3. `0x09A2E0` (Engine Init): `8f 83 88 ea 00 00 00 00` (`純一\0\0\0\0`) -> `Junichi\0` (`4a 75 6e 69 63 68 69 00`)
4. `0x097CB4` (Reset Prompt): `名前を『純一』に戻します。` -> `Reset name to Junichi.`

Because `"Junichi"` (7 chars + NUL = 8 bytes) and `"Asakura"` (7 chars + NUL = 8 bytes) match the exact 8-byte slots in the executable, the patches fit cleanly in-place with zero pointer shifts or code relocations.

---

## 4. System UI Translation Table

57 curated UI strings are translated in `work/eboot_patched.elf`:
- **Protagonist Default Name**: `Junichi`, `Asakura`, and name reset prompt.
- **Name Entry Prompts**: Character selection, cursor movement, delete, space, and confirmation dialogs.
- **Yes/No Buttons & Dialogs**: `はい` -> `Yes`, `いいえ` -> `No`, `標準に戻しますか？` -> `Reset to default?`, `設定を反映させますか？` -> `Apply settings?`, `設定を保存しますか？` -> `Save settings?`.
- **System Configuration Descriptions**: All 20 configuration menu descriptions translated into clear English.
- **CG / Scenario Gallery**: Selection instructions, page navigation, replay confirmation, and mode switching hints.
- **In-Game Save / Load**: Quick Save, Quick Load, and unsaved progress loss warning dialogs.

> Note: `sceUtilitySavedataInitStart` strings (`システムデータ`, `セーブデータ`) are left intact to ensure 100% stability with PSP firmware save utility routines.

---

## 5. Verification Hashes

Extracted files from `output/D.C.P.S. [NPJH50731]_en.iso` match local rebuilt files 100%:
- **font.pgf**: `CB2C3A33F6E48F741FE8B88361276D8C` (1,043,588 bytes, MATCH)
- **EBOOT.BIN**: `8E933FDA07C301434D0A1FF0ABB094D9` (1,426,736 bytes, MATCH)
- **script.bin**: `2BEA54DBB338AB7286DD5C25A01B06E3` (4,558,102 bytes, MATCH)
- **D.C.P.S. [NPJH50731]_en.iso**: `4C33A276A86BE18B909DE0BE23E298D2` (1,000,312,832 bytes)
