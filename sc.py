#!/usr/bin/env python3
import os
import sys
import math
import struct
import subprocess
import zlib
import time

WIDTH = 512
HEIGHT = 512
FPS = 60
PIX_FMT = "rgb24"

BYTES_PER_FRAME = WIDTH * HEIGHT * 3

SIGNATURE = b"TVPK"
HEADER_FORMAT = "<4sQI"
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)

VERBOSE = True


# ------------------------------------------------------------
# LOGGING
# ------------------------------------------------------------
def log(msg):
    print(f"[+] {msg}")


def warn(msg):
    print(f"[!] {msg}")


def err(msg):
    print(f"[-] {msg}")


# ------------------------------------------------------------
# UTILITIES
# ------------------------------------------------------------
def crc(data):
    return zlib.crc32(data)


def bytes_to_bits(data):
    return "".join(f"{b:08b}" for b in data)


# ------------------------------------------------------------
# FFMPEG PIPE ENCODE
# ------------------------------------------------------------
def ffmpeg_encode_stream(payload, output_video):

    log("Starting ffmpeg encoder...")

    process = subprocess.Popen(
        [
            "ffmpeg",
            "-y",
            "-f",
            "rawvideo",
            "-pix_fmt",
            PIX_FMT,
            "-s",
            f"{WIDTH}x{HEIGHT}",
            "-r",
            str(FPS),
            "-i",
            "-",
            "-c:v",
            "ffv1",
            output_video,
        ],
        stdin=subprocess.PIPE,
    )

    process.stdin.write(payload)
    process.stdin.close()
    process.wait()

    log("Video encoding finished")


# ------------------------------------------------------------
# FFMPEG PIPE DECODE
# ------------------------------------------------------------
def ffmpeg_decode_stream(video_path):

    log("Starting ffmpeg decoder...")

    process = subprocess.Popen(
        [
            "ffmpeg",
            "-i",
            video_path,
            "-f",
            "rawvideo",
            "-pix_fmt",
            PIX_FMT,
            "-",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )

    data = process.stdout.read()
    process.wait()

    log(f"Decoded raw bytes: {len(data)}")

    return data


# ------------------------------------------------------------
# FRAME DEBUG
# ------------------------------------------------------------
def debug_frames(raw_data, max_frames=3):

    frames = math.ceil(len(raw_data) / BYTES_PER_FRAME)

    log(f"Frame count detected: {frames}")

    for i in range(min(frames, max_frames)):
        start = i * BYTES_PER_FRAME
        end = start + BYTES_PER_FRAME

        chunk = raw_data[start:end]

        bits = bytes_to_bits(chunk[:16])

        print(f"[frame {i}] first bits: {bits}")


# ------------------------------------------------------------
# PACK
# ------------------------------------------------------------
def pack(input_file, output_video, compress=True):

    if not os.path.exists(input_file):
        err("Input file not found")
        return

    with open(input_file, "rb") as f:
        data = f.read()

    log(f"Input size: {len(data)} bytes")

    if compress:
        log("Compressing payload...")
        data = zlib.compress(data)
        log(f"Compressed size: {len(data)}")

    checksum = crc(data)

    header = struct.pack(HEADER_FORMAT, SIGNATURE, len(data), checksum)

    payload = header + data

    frames = math.ceil(len(payload) / BYTES_PER_FRAME)

    log(f"Payload size: {len(payload)}")
    log(f"Frames required: {frames}")

    padding = frames * BYTES_PER_FRAME - len(payload)

    if padding > 0:
        log(f"Adding padding: {padding}")
        payload += b"\x00" * padding

    start = time.time()

    ffmpeg_encode_stream(payload, output_video)

    elapsed = time.time() - start

    log(f"Container created: {output_video}")
    log(f"Time: {elapsed:.2f}s")


# ------------------------------------------------------------
# UNPACK
# ------------------------------------------------------------
def unpack(video_file, output_file):

    if not os.path.exists(video_file):
        err("Video not found")
        return

    raw = ffmpeg_decode_stream(video_file)

    debug_frames(raw)

    if len(raw) < HEADER_SIZE:
        err("Invalid container")
        return

    signature, size, checksum = struct.unpack(HEADER_FORMAT, raw[:HEADER_SIZE])

    if signature != SIGNATURE:
        err("Signature mismatch")
        return

    log("Valid container detected")

    payload = raw[HEADER_SIZE : HEADER_SIZE + size]

    calc_crc = crc(payload)

    if calc_crc != checksum:
        warn("Checksum mismatch (corruption possible)")
    else:
        log("Checksum OK")

    try:
        payload = zlib.decompress(payload)
        log("Payload decompressed")
    except:
        warn("Payload not compressed")

    with open(output_file, "wb") as f:
        f.write(payload)

    log(f"File restored: {output_file}")
    log(f"Final size: {len(payload)} bytes")


# ------------------------------------------------------------
# CLI
# ------------------------------------------------------------
def main():

    if len(sys.argv) < 4:
        print("Usage:")
        print("  pack <input> <video>")
        print("  unpack <video> <output>")
        return

    mode = sys.argv[1]

    if mode == "pack":
        pack(sys.argv[2], sys.argv[3])

    elif mode == "unpack":
        unpack(sys.argv[2], sys.argv[3])

    else:
        err("Invalid mode")


if __name__ == "__main__":
    main()
