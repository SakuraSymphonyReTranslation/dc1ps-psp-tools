# Panduan Modifikasi Video & Lirik Lagu D.C.P.S. (PSP)

Folder ini (`custom/video/`) digunakan untuk menaruh video kustom berformat **PlayStation Movie Format (`.pmf`)**, seperti video Opening yang telah ditambahkan takarir (subtitle/karaoke) lirik Bahasa Indonesia atau Bahasa Inggris.

Saat Anda menjalankan `build_iso.py`, `build_indonesia.bat`, atau `build_english.bat`, sistem akan **secara otomatis mendeteksi file `.pmf` kustom di folder ini** dan merekolasikannya ke dalam ISO hasil build.

---

## 1. Daftar File Video di dalam ISO D.C.P.S. (NPJH50731)

Semua video game terletak di direktori ISO: `PSP_GAME/USRDIR/data/`

| Nama File PMF | Keterangan Video |
|---|---|
| `dc1_op.pmf` | **Opening Movie (D.C.P.S. Main OP)** |
| `gend.pmf` | **Grand Ending Movie** |

---

## 2. Alur Kerja Modifikasi Video & Lirik

```
 [Base ISO Game]
       │
       ▼ (tools\dc1_assets.py extract-video)
  File Asli: custom/video/*.pmf
       │
       ▼ (Demux PMF -> MP4 via ffmpeg / PMF player)
  Video H.264 & Audio MP3/WAV
       │
       ▼ (Aegisub / Subtitle Edit)
  Takarir Lirik Bahasa Indonesia / Inggris (.ass)
       │
       ▼ (Render Hardsub via ffmpeg / Premiere)
  Render Video MP4 (480x272, 29.97 fps)
       │
       ▼ (UMD Stream Composer / MPS2PMF)
  File Kustom Baru: custom/video/dc1_op.pmf
       │
       ▼ (build_iso.py / build_indonesia.bat)
 [ISO Terpasang Video Baru!]
```

---

## 3. Langkah Demi Langkah

1. **Ekstrak Video Asli dari ISO**:
   Jalankan menu `run_menu.bat` (Opsi 5) atau:
   ```bash
   python tools/dc1_assets.py extract-video
   ```
2. **Konversi ke MP4**:
   ```bash
   ffmpeg -i custom/video/dc1_op.pmf -c:v copy -c:a aac custom/video/dc1_op_raw.mp4
   ```
3. **Buat Subtitle di Aegisub**:
   Masukkan lirik lagu, atur timing/gaya teks, lalu simpan sebagai file `.ass`.
4. **Hardsub Video**:
   ```bash
   ffmpeg -i custom/video/dc1_op_raw.mp4 -vf "ass=custom/video/dc1_op.ass" -c:v libx264 -b:v 1500k -r 29.97 -s 480x272 -c:a aac -b:a 128k custom/video/dc1_op_subbed.mp4
   ```
5. **Konversi Kembali ke Format PMF**:
   Gunakan **UMD Stream Composer** dan **MPS2PMF** untuk menghasilkan `dc1_op.pmf` baru.
6. **Auto-Injeksi**:
   Letakkan file di `custom/video/dc1_op.pmf` dan jalankan script build ISO!
