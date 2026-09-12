# Panduan Modifikasi Grafis UI & Tekstur D.C.P.S. (PSP)

Folder ini (`custom/ui/`) digunakan untuk menaruh modifikasi grafis antarmuka (User Interface) game D.C.P.S. PSP (`NPJH50731` / `ULJM05718`).

Terdapat dua jenis grafis UI di dalam game:
1. **File PNG Lepas Langsung pada ISO**.
2. **Tekstur di dalam Arsip `catfile.bin` (815 entri gambar MIG)**.

---

## 1. Daftar File UI di dalam Game

### A. File PNG Lepas di ISO (`PSP_GAME/USRDIR/data/`)

| Nama File | Resolusi / Ukuran | Fungsi Antarmuka |
|---|---|---|
| `sav_bg.png` | 480 × 272 px | Background layar Simpan / Muat (Save / Load) |
| `dc1_new.png` | Grafis Badge | Label penanda slot "NEW" pada save |
| `sav_dc1.png` | Banner / Ikon | Ikon file save D.C.P.S. |
| `sys_dc1.png` | Banner / Ikon | Ikon file sistem D.C.P.S. |
| `ICON0.PNG` | 144 × 80 px | Ikon game di menu XMB PSP |
| `PIC1.PNG` | 480 × 272 px | Wallpaper background game di menu XMB PSP |

*Cukup letakkan file PNG editan Anda di dalam folder ini (`custom/ui/`), dan script builder akan langsung menggantikannya di dalam ISO.*

---

### B. Tekstur di dalam Arsip `catfile.bin`

Arsip `catfile.bin` berisi 815 file gambar berformat Sony MIG/GIM (`MIG.00.1PSP`) yang mencakup tombol menu, bingkai dialog, dan elemen sistem.

#### Alur Modifikasi Tekstur CAT:
1. **Ekstrak Arsip**:
   Jalankan menu `run_menu.bat` (Opsi 6) atau:
   ```bash
   python tools/dc1_assets.py extract-ui
   ```
   Arsip akan di-unpack ke `custom/ui/catfile_extracted/`.
2. **Edit Gambar**:
   Edit gambar yang diinginkan dengan resolusi yang tetap sama.
3. **Repack Arsip**:
   Pilih menu `[7]` di `run_menu.bat` atau:
   ```bash
   python tools/dc1_assets.py repack-catfile
   ```
   File `custom/ui/catfile.bin` baru akan dibuat dan otomatis diinjeksikan saat build ISO!

---

## 2. Alternatif: Fitur Texture Replacement PPSSPP

Selain memodifikasi ISO secara langsung, Anda juga bisa mengganti tekstur game secara *live* di emulator PPSSPP:
1. Buka folder: `memstick/PSP/TEXTURES/NPJH50731/`
2. Taruh file tekstur PNG pengganti di folder tersebut.
3. Aktifkan opsi **"Replace Textures"** pada pengaturan PPSSPP.
