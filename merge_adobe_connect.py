#!/usr/bin/env python3

import os
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path


def gettext(elem):
    if elem is None:
        return ""
    return "".join(elem.itertext()).strip()


def parse_stream_timeline(xml_path):

    tree = ET.parse(xml_path)
    root = tree.getroot()

    timeline = []

    for message in root.iter("Message"):

        obj = message.find("Object")
        string_elem = message.find("String")
        array_elem = message.find("Array")

        if obj is None or string_elem is None or array_elem is None:
            continue

        event_type = gettext(string_elem)

        if event_type != "streamAdded":
            continue

        stream_obj = array_elem.find("Object")

        if stream_obj is None:
            continue

        start_time = gettext(stream_obj.find("startTime"))
        stream_name = gettext(stream_obj.find("streamName"))
        stream_type = gettext(stream_obj.find("streamType"))
        stream_id = gettext(stream_obj.find("streamId"))

        if not stream_name:
            continue

        try:
            start_seconds = int(start_time) / 1000.0
        except:
            start_seconds = 0

        timeline.append({
            "start": start_seconds,
            "stream_name": stream_name,
            "stream_type": stream_type,
            "stream_id": stream_id
        })

    timeline.sort(key=lambda x: x["start"])

    print(f"Parsed {len(timeline)} streamAdded events")

    return timeline



def find_flv_file(folder, stream_name):
    """
    Find matching FLV file for stream.
    """

    base = stream_name.lstrip("/")

    folder = Path(folder)

    for f in folder.glob("*.flv"):

        name = f.stem

        if name == base:
            return f

        if base in name:
            return f

    return None


def get_media_info(path):
    """
    Get duration + dimensions using ffprobe.
    """

    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=width,height",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=0",
        str(path)
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True
    )

    duration = 0
    width = 1280
    height = 720

    for line in result.stdout.splitlines():

        if line.startswith("duration="):
            try:
                duration = float(line.split("=")[1])
            except:
                pass

        elif line.startswith("width="):
            try:
                width = int(line.split("=")[1])
            except:
                pass

        elif line.startswith("height="):
            try:
                height = int(line.split("=")[1])
            except:
                pass

    return duration, width, height


def merge_segments(folder_path, timeline, output_file):

    folder = Path(folder_path)

    video_segments = []
    audio_segments = []

    print("\nScanning streams...\n")

    for seg in timeline:

        stream_name = seg["stream_name"]

        flv = find_flv_file(folder, stream_name)

        if not flv:
            print(f"Missing FLV for {stream_name}")
            continue

        duration, width, height = get_media_info(flv)

        item = {
            "file": flv,
            "start": seg["start"],
            "duration": duration,
            "end": seg["start"] + duration,
            "width": width,
            "height": height,
            "stream_name": stream_name
        }

        lower = stream_name.lower()

        if "screenshare" in lower:
            video_segments.append(item)

            print(
                f"[VIDEO] {stream_name} "
                f"start={item['start']:.2f}s "
                f"duration={duration:.2f}s"
            )

        elif "camera" in lower or "voip" in lower:
            audio_segments.append(item)

            print(
                f"[AUDIO] {stream_name} "
                f"start={item['start']:.2f}s "
                f"duration={duration:.2f}s"
            )

    if not video_segments:
        print("No video streams found.")
        return

    total_duration = 0

    for v in video_segments:
        total_duration = max(total_duration, v["end"])

    for a in audio_segments:
        total_duration = max(total_duration, a["end"])

    print(f"\nFinal duration: {total_duration:.2f} seconds")

    max_width = max(v["width"] for v in video_segments)
    max_height = max(v["height"] for v in video_segments)

    print(f"Canvas size: {max_width}x{max_height}")

    cmd = ["ffmpeg", "-y"]

    all_inputs = []

    for seg in video_segments + audio_segments:
        if seg["file"] not in all_inputs:
            all_inputs.append(seg["file"])

    for inp in all_inputs:
        cmd.extend(["-i", str(inp)])

    # Background canvas
    cmd.extend([
        "-f",
        "lavfi",
        "-i",
        f"color=c=black:s={max_width}x{max_height}:d={total_duration}"
    ])

    bg_index = len(all_inputs)

    filters = []

    current_video = f"[{bg_index}:v]"

    # ---------------- VIDEO OVERLAY ----------------

    for idx, seg in enumerate(video_segments):

        input_idx = all_inputs.index(seg["file"])

        start = seg["start"]
        end = seg["end"]

        filters.append(
            f"[{input_idx}:v]"
            f"setpts=PTS-STARTPTS+{start}/TB,"
            f"scale={max_width}:{max_height}"
            f"[v{idx}]"
        )

        out_label = f"vtmp{idx}"

        filters.append(
            f"{current_video}[v{idx}]"
            f"overlay="
            f"enable='between(t,{start},{end})':"
            f"eof_action=pass"
            f"[{out_label}]"
        )

        current_video = f"[{out_label}]"

    # ---------------- AUDIO MIX ----------------

    audio_labels = []

    for idx, seg in enumerate(audio_segments):

        input_idx = all_inputs.index(seg["file"])

        delay_ms = int(seg["start"] * 1000)

        filters.append(
            f"[{input_idx}:a]"
            f"adelay={delay_ms}|{delay_ms},"
            f"aresample=async=1"
            f"[a{idx}]"
        )

        audio_labels.append(f"[a{idx}]")

    if audio_labels:

        filters.append(
            "".join(audio_labels) +
            f"amix=inputs={len(audio_labels)}:"
            f"duration=longest:"
            f"dropout_transition=0"
            f"[aout]"
        )

    filter_complex = ";".join(filters)

    cmd.extend([
        "-filter_complex",
        filter_complex
    ])

    cmd.extend([
        "-map",
        current_video
    ])

    if audio_labels:
        cmd.extend([
            "-map",
            "[aout]"
        ])

    cmd.extend([
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "23",

        "-c:a", "aac",
        "-b:a", "192k",

        "-pix_fmt", "yuv420p",

        "-movflags", "+faststart",

        "-t", str(total_duration),

        str(output_file)
    ])

    print("\nRunning FFmpeg...\n")
    print(" ".join(cmd))
    print()

    result = subprocess.run(cmd)

    if result.returncode == 0:
        print(f"\nDone: {output_file}")
    else:
        print("\nFFmpeg failed.")


def main():

    print("Adobe Connect Recording Merger\n")

    folder_path = input("Enter Adobe Connect recording folder path: ").strip()

    folder = Path(folder_path)

    if not folder.exists():
        print("Folder does not exist.")
        return

    xml_path = folder / "mainstream.xml"

    if not xml_path.exists():
        print("mainstream.xml not found.")
        return

    print("\nParsing XML timeline...\n")

    timeline = parse_stream_timeline(xml_path)

    for item in timeline[:10]:
        print(item)

    if not timeline:
        print("No timeline entries found.")
        return

    print(f"Found {len(timeline)} timeline entries.\n")

    for seg in timeline[:20]:
        print(
            f"{seg['start']:10.2f}s | "
            f"{seg['stream_name']}"
        )

    if len(timeline) > 20:
        print(f"... and {len(timeline) - 20} more")

    output_file = folder / "merged_recording.mp4"

    merge_segments(
        folder,
        timeline,
        output_file
    )


if __name__ == "__main__":
    main()
