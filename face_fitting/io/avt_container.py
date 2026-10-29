"""Byte-faithful reader/writer for CLO `.avt` files (magic prefix + ZIP archive)."""

from __future__ import annotations

import struct
import zlib
from dataclasses import dataclass, field
from pathlib import Path

AVT_MAGIC = b' AVT        CLO '

_LFH_SIG = b'PK\x03\x04'
_CDH_SIG = b'PK\x01\x02'
_EOCD_SIG = b'PK\x05\x06'

# Byte offsets of the size/crc triple inside a local file header.
_LFH_CRC_OFFSET = 14
_LFH_CSIZE_OFFSET = 18
_LFH_USIZE_OFFSET = 22


@dataclass
class AvtEntry:
    """One archive member, carrying its original header bytes so untouched entries round-trip exactly."""
    name: str
    local_header: bytes
    compressed: bytes
    crc: int
    compressed_size: int
    uncompressed_size: int
    method: int
    flags: int
    mod_time: int
    mod_date: int
    version_made_by: int
    version_needed: int
    internal_attr: int
    external_attr: int
    disk_start: int
    comment: bytes = b''
    replaced: bool = False

    def decompress(self) -> bytes:
        if self.method == 0:
            return self.compressed
        return zlib.decompress(self.compressed, -15)


@dataclass
class AvtContainer:
    """A parsed `.avt`: the opaque header blob plus the ZIP members that follow it."""
    prefix: bytes
    entries: list[AvtEntry]
    eocd_comment: bytes = b''
    _index: dict[str, int] = field(default_factory=dict, repr=False)

    @property
    def prefix_size(self) -> int:
        return len(self.prefix)

    def names(self) -> list[str]:
        return [entry.name for entry in self.entries]

    def entry(self, name: str) -> AvtEntry:
        if name not in self._index:
            raise KeyError(f'No such entry in .avt: {name}')
        return self.entries[self._index[name]]

    def read_entry(self, name: str) -> bytes:
        return self.entry(name).decompress()

    def replaced_names(self) -> list[str]:
        return [entry.name for entry in self.entries if entry.replaced]

    def replace_entry(self, name: str, payload: bytes, *, compress_level: int = 6) -> None:
        """Swap an entry's contents, reusing its original header so unrelated bytes stay put."""
        entry = self.entry(name)
        compressor = zlib.compressobj(compress_level, zlib.DEFLATED, -15)
        compressed = compressor.compress(payload) + compressor.flush()
        crc = zlib.crc32(payload) & 0xFFFFFFFF

        header = bytearray(entry.local_header)
        struct.pack_into('<I', header, _LFH_CRC_OFFSET, crc)
        struct.pack_into('<I', header, _LFH_CSIZE_OFFSET, len(compressed))
        struct.pack_into('<I', header, _LFH_USIZE_OFFSET, len(payload))

        entry.local_header = bytes(header)
        entry.compressed = compressed
        entry.crc = crc
        entry.compressed_size = len(compressed)
        entry.uncompressed_size = len(payload)
        entry.method = 8
        entry.replaced = True


def read_avt(path: str | Path) -> AvtContainer:
    data = Path(path).read_bytes()
    if not data.startswith(AVT_MAGIC):
        raise ValueError(f'Not a CLO .avt file (bad magic): {path}')

    eocd_pos = data.rfind(_EOCD_SIG)
    if eocd_pos < 0:
        raise ValueError(f'No ZIP end-of-central-directory found in {path}')

    entry_count, = struct.unpack_from('<H', data, eocd_pos + 10)
    cd_size, = struct.unpack_from('<I', data, eocd_pos + 12)
    cd_offset, = struct.unpack_from('<I', data, eocd_pos + 16)
    comment_len, = struct.unpack_from('<H', data, eocd_pos + 20)
    eocd_comment = data[eocd_pos + 22: eocd_pos + 22 + comment_len]

    # Offsets inside the archive are relative to the first local header, not the file,
    # so the magic/thumbnail prefix shifts every one of them by this amount.
    prefix_size = eocd_pos - cd_size - cd_offset
    if prefix_size < 0 or data[prefix_size:prefix_size + 4] != _LFH_SIG:
        raise ValueError(f'Could not locate the ZIP prefix shift in {path}')

    entries: list[AvtEntry] = []
    index: dict[str, int] = {}
    pos = prefix_size + cd_offset

    for _ in range(entry_count):
        if data[pos:pos + 4] != _CDH_SIG:
            raise ValueError(f'Malformed central directory at byte {pos} in {path}')
        (_sig, version_made_by, version_needed, flags, method, mod_time, mod_date,
         crc, csize, usize, name_len, extra_len, comment_len_cd, disk_start,
         internal_attr, external_attr, local_offset) = struct.unpack_from('<IHHHHHHIIIHHHHHII', data, pos)

        name = data[pos + 46: pos + 46 + name_len].decode('utf-8')
        comment_at = pos + 46 + name_len + extra_len
        comment = data[comment_at: comment_at + comment_len_cd]

        lfh_pos = prefix_size + local_offset
        if data[lfh_pos:lfh_pos + 4] != _LFH_SIG:
            raise ValueError(f'Entry {name!r} does not point at a local header in {path}')
        lfh_name_len, = struct.unpack_from('<H', data, lfh_pos + 26)
        lfh_extra_len, = struct.unpack_from('<H', data, lfh_pos + 28)
        lfh_end = lfh_pos + 30 + lfh_name_len + lfh_extra_len

        entries.append(AvtEntry(
            name=name,
            local_header=data[lfh_pos:lfh_end],
            compressed=data[lfh_end:lfh_end + csize],
            crc=crc,
            compressed_size=csize,
            uncompressed_size=usize,
            method=method,
            flags=flags,
            mod_time=mod_time,
            mod_date=mod_date,
            version_made_by=version_made_by,
            version_needed=version_needed,
            internal_attr=internal_attr,
            external_attr=external_attr,
            disk_start=disk_start,
            comment=comment,
        ))
        index[name] = len(entries) - 1
        pos = comment_at + comment_len_cd

    return AvtContainer(prefix=data[:prefix_size], entries=entries,
                        eocd_comment=eocd_comment, _index=index)


def write_avt(container: AvtContainer, path: str | Path) -> None:
    out = bytearray(container.prefix)
    local_offsets: list[int] = []

    for entry in container.entries:
        local_offsets.append(len(out) - container.prefix_size)
        out += entry.local_header
        out += entry.compressed

    cd_offset = len(out) - container.prefix_size
    central = bytearray()
    for entry, local_offset in zip(container.entries, local_offsets):
        name = entry.name.encode('utf-8')
        central += struct.pack(
            '<IHHHHHHIIIHHHHHII', 0x02014B50, entry.version_made_by, entry.version_needed,
            entry.flags, entry.method, entry.mod_time, entry.mod_date, entry.crc,
            entry.compressed_size, entry.uncompressed_size, len(name), 0, len(entry.comment),
            entry.disk_start, entry.internal_attr, entry.external_attr, local_offset,
        )
        central += name
        central += entry.comment

    out += central
    out += struct.pack('<IHHHHIIH', 0x06054B50, 0, 0, len(container.entries),
                       len(container.entries), len(central), cd_offset,
                       len(container.eocd_comment))
    out += container.eocd_comment

    Path(path).write_bytes(bytes(out))
