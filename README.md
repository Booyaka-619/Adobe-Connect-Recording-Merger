# Adobe Connect Recording Merger

A Python script that merges Adobe Connect recording segments (`.flv` files) into a single `.mp4` video using FFmpeg.

Adobe Connect stores recordings as multiple separate FLV streams (screen share, camera, VoIP) with an XML timeline. This script reconstructs the full recording by parsing the timeline and combining all streams into one output file.

## Requirements

- **Python 3+**
- **FFmpeg** and **ffprobe** installed and available on your system PATH

No third-party Python packages are needed — only standard library modules are used (`os`, `subprocess`, `xml.etree.ElementTree`, `pathlib`).

## Getting the Recording Files

1. Open the Adobe Connect recording link.
2. Download the recording archive by appending `output/custom-name.zip?download=zip` to the URL:
   http://your-site-domain/xxxxxxx/output/custom-name.zip?download=zip
3. Extract the ZIP. You should have a folder containing `mainstream.xml` and one or more `.flv` files.

## Usage
```bash
python3 merge_adobe_connect.py
```

The script will prompt you interactively:


Adobe Connect Recording Merger
Enter Adobe Connect recording folder path:

Enter the path to the extracted recording folder. The script will:

1. Parse `mainstream.xml` for `streamAdded` events.
2. Match each stream to its corresponding `.flv` file.
3. Classify streams as video (`screenshare`) or audio (`camera`, `voip`) based on naming conventions.
4. Build an FFmpeg filter graph to overlay video segments and mix audio segments on a timeline.
5. Produce `merged_recording.mp4` in the same folder.

## How It Works

- **Timeline parsing:** Reads `mainstream.xml`, extracts `streamAdded` events sorted by `startTime` (converted from ms to seconds).
- **File matching:** For each stream name (e.g. `/screenshare_0_2`), finds the matching `.flv` file in the folder.
- **Media probing:** Uses `ffprobe` to get duration and dimensions of each FLV file.
- **Stream classification:**
  - `screenshare` in name → video segment
  - `camera` or `voip` in name → audio segment
- **Merging:** Constructs an FFmpeg `filter_complex` with a black background canvas, overlays video segments at their timeline positions, delays and mixes audio segments, and encodes to H.264 + AAC.

## Output

- **File:** `merged_recording.mp4` (saved in the recording folder)
- **Video codec:** libx264, yuv420p
- **Audio codec:** AAC
- **Flags:** `+faststart` for web streaming compatibility

## Limitations

- Relies on Adobe Connect naming conventions (`screenshare`, `camera`, `voip`) to classify streams.
- Only processes `.flv` input files.
- Does not support arbitrary or custom stream types.
- Will fail if `ffmpeg` or `ffprobe` are not installed or not on PATH.

---

# ادغام‌کننده ضبط Adobe Connect

یک اسکریپت پایتون برای ادغام بخش‌های ضبط‌شده Adobe Connect (فایل‌های `.flv`) در یک فایل `.mp4` با استفاده از FFmpeg.

نرم افزار Adobe Connect ضبط‌ها را به صورت استریم‌های FLV جداگانه (اشتراک صفحه، دوربین، VoIP) به همراه یک تایم‌لاین XML ذخیره می‌کند. این اسکریپت با تجزیه تایم‌لاین، ضبط کامل را بازسازی و تمام استریم‌ها را در یک فایل خروجی ترکیب می‌کند.

## پیش‌نیازها

- **Python 3+**
- **FFmpeg** و **ffprobe** نصب‌شده و در PATH سیستم موجود باشد

هیچ پکیج خارجی پایتون نیاز نیست — فقط از کتابخانه‌های استاندارد استفاده شده است.

## دریافت فایل‌های ضبط

1. لینک ضبط Adobe Connect را باز کنید.
2. آرشیو ضبط را با اضافه کردن عبارت `output/custom-name.zip?download=zip` دانلود کنید:
   http://your-site-domain/xxxxxxx/output/custom-name.zip?download=zip
3. فایل ZIP را استخراج کنید. باید پوشه‌ای شامل `mainstream.xml` و یک یا چند فایل `.flv` داشته باشید.

## نحوه استفاده

bash
python3 merge_adobe_connect.py

اسکریپت به صورت تعاملی مسیر پوشه ضبط را می‌پرسد. پس از وارد کردن مسیر، فایل `merged_recording.mp4` در همان پوشه ساخته می‌شود.

## محدودیت‌ها

- به قراردادهای نام‌گذاری Adobe Connect وابسته است (`screenshare`، `camera`، `voip`).
- فقط فایل‌های ورودی `.flv` را پردازش می‌کند.
- در صورت نبود `ffmpeg` یا `ffprobe` در PATH، با خطا مواجه می‌شود.