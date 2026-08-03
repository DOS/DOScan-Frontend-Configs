#!/usr/bin/env python3

import json
import re
import struct
import sys
import xml.etree.ElementTree as ET
import zlib
from pathlib import Path
from urllib.parse import urlparse

ICON_PREFIX = "https://raw.githubusercontent.com/DOS/DOScan-Frontend-Configs/main/"
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
MAX_PNG_DECOMPRESSED_BYTES = 32 * 1024 * 1024
BLOCKED_SVG_TAGS = {"embed", "foreignobject", "iframe", "object", "script", "style"}
EXTERNAL_SCHEME = re.compile(r"(?:https?:|data:|file:|javascript:|//)", re.IGNORECASE)
CSS_URL = re.compile(r"url\(\s*(['\"]?)(.*?)\1\s*\)", re.IGNORECASE)
CSS_ESCAPE = re.compile(
    r"\\(?:([0-9a-fA-F]{1,6})(?:\r\n|[ \t\r\n\f])?|(\r\n|[\n\r\f])|(.))",
    re.DOTALL,
)


def fail(message: str) -> None:
    raise ValueError(message)


def local_name(value: str) -> str:
    return value.rsplit("}", 1)[-1].lower()


def decode_css_escapes(value: str) -> str:
    def replace(match: re.Match[str]) -> str:
        if match.group(1):
            codepoint = int(match.group(1), 16)
            if codepoint == 0 or codepoint > 0x10FFFF:
                return "\uFFFD"
            return chr(codepoint)
        if match.group(2):
            return ""
        return match.group(3) or ""

    decoded = value
    for _ in range(4):
        next_value = CSS_ESCAPE.sub(replace, decoded)
        if next_value == decoded:
            break
        decoded = next_value
    return decoded


def validate_text_references(value: str, source: Path) -> None:
    if "/*" in value or "*/" in value:
        fail(f"CSS comments are not allowed in {source}")
    value = decode_css_escapes(value)
    if "/*" in value or "*/" in value:
        fail(f"CSS comments are not allowed in {source}")
    if "@import" in value.lower() or EXTERNAL_SCHEME.search(value):
        fail(f"External SVG reference is not allowed in {source}")
    for match in CSS_URL.finditer(value):
        target = match.group(2).strip()
        if target and not target.startswith("#"):
            fail(f"Only fragment SVG URLs are allowed in {source}: {target}")


def validate_svg(path: Path) -> None:
    for _event, _instruction in ET.iterparse(path, events=("pi",)):
        fail(f"XML processing instructions are not allowed in {path}")
    root = ET.parse(path).getroot()
    for element in root.iter():
        if local_name(element.tag) in BLOCKED_SVG_TAGS:
            fail(f"Active SVG element is not allowed in {path}: {local_name(element.tag)}")
        if element.text:
            validate_text_references(element.text, path)
        if element.tail:
            validate_text_references(element.tail, path)
        for attribute, value in element.attrib.items():
            name = local_name(attribute)
            if name.startswith("on"):
                fail(f"SVG event handler is not allowed in {path}: {name}")
            if name == "style":
                fail(f"SVG style attributes are not allowed in {path}")
            if name == "href" and value and not value.startswith("#"):
                fail(f"External SVG href is not allowed in {path}: {value}")
            validate_text_references(value, path)


def validate_png(path: Path) -> None:
    data = path.read_bytes()
    if not data.startswith(PNG_SIGNATURE):
        fail(f"Invalid PNG signature: {path}")

    offset = len(PNG_SIGNATURE)
    chunk_index = 0
    idat = bytearray()
    saw_ihdr = False
    saw_iend = False

    while offset < len(data):
        if offset + 12 > len(data):
            fail(f"Truncated PNG chunk: {path}")
        length = struct.unpack(">I", data[offset : offset + 4])[0]
        chunk_type = data[offset + 4 : offset + 8]
        chunk_end = offset + 12 + length
        if chunk_end > len(data):
            fail(f"Truncated PNG payload: {path}")

        payload = data[offset + 8 : offset + 8 + length]
        expected_crc = struct.unpack(">I", data[offset + 8 + length : chunk_end])[0]
        actual_crc = zlib.crc32(chunk_type + payload) & 0xFFFFFFFF
        if actual_crc != expected_crc:
            fail(f"Invalid PNG chunk checksum: {path}")

        if chunk_index == 0:
            if chunk_type != b"IHDR" or length != 13:
                fail(f"PNG must start with a valid IHDR chunk: {path}")
            width, height = struct.unpack(">II", payload[:8])
            if width == 0 or height == 0:
                fail(f"PNG dimensions must be non-zero: {path}")
            saw_ihdr = True
        elif chunk_type == b"IDAT":
            idat.extend(payload)
        elif chunk_type == b"IEND":
            if length != 0 or chunk_end != len(data):
                fail(f"PNG must end at an empty IEND chunk: {path}")
            saw_iend = True
            break

        chunk_index += 1
        offset = chunk_end

    if not saw_ihdr or not idat or not saw_iend:
        fail(f"PNG is missing IHDR, IDAT, or IEND: {path}")

    decompressor = zlib.decompressobj()
    decompressed = decompressor.decompress(bytes(idat), MAX_PNG_DECOMPRESSED_BYTES + 1)
    if len(decompressed) > MAX_PNG_DECOMPRESSED_BYTES or not decompressor.eof:
        fail(f"PNG image data is invalid or exceeds the safety limit: {path}")


def validate_token_list(list_path: Path, repository_root: Path) -> None:
    token_list = json.loads(list_path.read_text(encoding="utf-8"))
    for token in token_list["tokens"]:
        logo_uri = token["logoURI"]
        parsed = urlparse(logo_uri)
        if not logo_uri.startswith(ICON_PREFIX) or parsed.query or parsed.fragment:
            fail(f"Non-canonical logoURI: {logo_uri}")

        asset_path = repository_root / logo_uri.removeprefix(ICON_PREFIX)
        if not asset_path.is_file() or asset_path.stat().st_size == 0:
            fail(f"Token icon is missing or empty: {asset_path}")
        if asset_path.suffix.lower() == ".svg":
            validate_svg(asset_path)
        elif asset_path.suffix.lower() == ".png":
            validate_png(asset_path)
        else:
            fail(f"Unsupported token icon type: {asset_path}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: validate_assets.py TOKEN_LIST_JSON")
    source = Path(sys.argv[1]).resolve()
    validate_token_list(source, Path.cwd().resolve())
