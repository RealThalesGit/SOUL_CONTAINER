#!/usr/bin/env python3
import os
import sys
import math
import struct
import subprocess
import zlib

WIDTH = 512
HEIGHT = 512
FPS = 60
PIX_FMT = "rgb24"

RAW_FILE = "container.raw"
RECOVERED_RAW = "recovered.raw"
BYTES_PER_FRAME = WIDTH * HEIGHT * 3

SIGNATURE = b"TVPK"
HEADER_FORMAT = "<4sQ"  # signature + original_size
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)

# ------------------------------------------------------------
# Utilities
# ------------------------------------------------------------
def run_ffmpeg_encode(raw_path, video_path):
    subprocess.run([
        "ffmpeg", "-y",
        "-f", "rawvideo",
        "-pix_fmt", PIX_FMT,
        "-s", f"{WIDTH}x{HEIGHT}",
        "-r", str(FPS),
        "-i", raw_path,
        "-c:v", "ffv1",
        video_path
    ], check=True)


def run_ffmpeg_decode(video_path, raw_path):
    subprocess.run([
        "ffmpeg", "-y",
        "-i", video_path,
        "-f", "rawvideo",
        "-pix_fmt", PIX_FMT,
        raw_path
    ], check=True)


def bytes_to_bits(data):
    return ''.join(f'{b:08b}' for b in data)


def checksum(data):
    return zlib.crc32(data)


def compare_bytes(a: bytes, b: bytes):
    min_len = min(len(a), len(b))
    mismatches = []
    for i in range(min_len):
        if a[i] != b[i]:
            mismatches.append((i, a[i], b[i]))
    return mismatches


def print_frame_bits(frame_data, frame_index, max_bytes=64):
    print(f"[*] Frame {frame_index}: first {max_bytes} bytes as bits")
    bits = bytes_to_bits(frame_data[:max_bytes])
    print(bits)


# ------------------------------------------------------------
# PACK
# ------------------------------------------------------------
def pack(input_file, output_video):
    if not os.path.exists(input_file):
        print("[-] Input file not found.")
        return

    with open(input_file, "rb") as f:
        data = f.read()

    original_size = len(data)
    header = struct.pack(HEADER_FORMAT, SIGNATURE, original_size)
    payload = header + data
    total_frames = math.ceil(len(payload) / BYTES_PER_FRAME)

    print(f"[+] Packing {input_file}")
    print(f"[+] Original size: {original_size} bytes")
    print(f"[+] Total frames: {total_frames}")
    print(f"[+] Payload checksum: {checksum(payload):08x}")

    with open(RAW_FILE, "wb") as out:
        for i in range(total_frames):
            start = i * BYTES_PER_FRAME
            end = start + BYTES_PER_FRAME
            chunk = payload[start:end]

            if len(chunk) < BYTES_PER_FRAME:
                chunk += b"\x00" * (BYTES_PER_FRAME - len(chunk))

            out.write(chunk)
            print(f"[frame {i+1}/{total_frames}] Written {len(chunk)} bytes")
            print_frame_bits(chunk, i+1, max_bytes=32)

    run_ffmpeg_encode(RAW_FILE, output_video)
    os.remove(RAW_FILE)
    print(f"[+] Video container created: {output_video}")


# ------------------------------------------------------------
# UNPACK
# ------------------------------------------------------------
def unpack(input_video, output_file, original_file=None):
    if not os.path.exists(input_video):
        print("[-] Video file not found.")
        return

    print(f"[+] Unpacking {input_video}")
    run_ffmpeg_decode(input_video, RECOVERED_RAW)

    with open(RECOVERED_RAW, "rb") as f:
        raw_data = f.read()
    os.remove(RECOVERED_RAW)

    if len(raw_data) < HEADER_SIZE:
        print("[-] Invalid container (too small)")
        return

    signature, original_size = struct.unpack(HEADER_FORMAT, raw_data[:HEADER_SIZE])
    if signature != SIGNATURE:
        print("[-] Invalid signature. Not a TVPK container.")
        return

    file_data = raw_data[HEADER_SIZE:HEADER_SIZE + original_size]
    print(f"[+] Extracted {len(file_data)} bytes (original size: {original_size})")
    print(f"[*] Payload checksum: {checksum(raw_data[:HEADER_SIZE] + file_data):08x}")

    # ----- DEBUG BIT A BIT POR FRAMES -----
    total_frames = math.ceil(len(raw_data) / BYTES_PER_FRAME)
    for i in range(total_frames):
        start = i * BYTES_PER_FRAME
        end = start + BYTES_PER_FRAME
        chunk = raw_data[start:end]
        print_frame_bits(chunk, i+1, max_bytes=32)

    # ----- COMPARAÇÃO COM ARQUIVO ORIGINAL -----
    if original_file and os.path.exists(original_file):
        with open(original_file, "rb") as f:
            orig = f.read()
        mismatches = compare_bytes(orig, file_data)
        if mismatches:
            print(f"[!] {len(mismatches)} mismatches found with original:")
            for idx, b1, b2 in mismatches[:10]:  # mostra só os primeiros 10
                print(f"  Byte {idx}: original={b1:02x}, reconstructed={b2:02x}")
        else:
            print("[+] Reconstruction matches original file exactly!")

    # ----- ANALISE DE PADDING -----
    padding_len = len(raw_data) - HEADER_SIZE - original_size
    if padding_len > 0:
        print(f"[*] Detected {padding_len} bytes of padding at the end of last frame")

    with open(output_file, "wb") as out:
        out.write(file_data)

    print(f"[+] File reconstructed: {output_file}")
    print(f"[+] Restored size: {len(file_data)} bytes")


# ------------------------------------------------------------
# CLI
# ------------------------------------------------------------
def main():
    if len(sys.argv) < 3:
        print("Usage:")
        print("  pack   <input_file> <output_video>")
        print("  unpack <input_video> <output_file> [original_file_for_comparison]")
        return

    mode = sys.argv[1]
    if mode == "pack" and len(sys.argv) == 4:
        pack(sys.argv[2], sys.argv[3])
    elif mode == "unpack" and len(sys.argv) >= 4:
        orig_file = sys.argv[4] if len(sys.argv) == 5 else None
        unpack(sys.argv[2], sys.argv[3], original_file=orig_file)
    else:
        print("[-] Invalid arguments")


if __name__ == "__main__":
    main()
