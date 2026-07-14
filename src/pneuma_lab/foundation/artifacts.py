"""Canonical, ancestry-bound writers for repository and build artifacts."""

from __future__ import annotations

from collections.abc import Iterable, Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
import errno
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import posixpath
import re
import secrets
import stat as stat_module
import sys
import tempfile
from typing import Any


_HASH_CHUNK_BYTES = 1024 * 1024
_UNSUPPORTED_FSYNC_ERRNOS = frozenset(
    value
    for value in (
        getattr(errno, "EINVAL", None),
        getattr(errno, "ENOSYS", None),
        getattr(errno, "ENOTSUP", None),
    )
    if value is not None
)


class ArtifactPublicationError(OSError):
    """Raised when output ancestry cannot remain bound and verified."""


@dataclass
class _PublishedArtifact:
    name: str
    expected_sha256: str
    expected_size: int
    backup_name: str | None = None
    backup_created: bool = False
    published: bool = False


@dataclass(frozen=True)
class _LinuxMountInfo:
    mount_id: int
    parent_id: int
    device: str
    root: PurePosixPath
    mountpoint: PurePosixPath


def _unescape_linux_mount_field(field: str) -> str:
    result: list[str] = []
    index = 0
    while index < len(field):
        character = field[index]
        if character != "\\":
            result.append(character)
            index += 1
            continue
        octal = field[index + 1:index + 4]
        if len(octal) != 3 or any(value not in "01234567" for value in octal):
            raise ArtifactPublicationError(
                "Linux mount provenance contains an invalid escape"
            )
        decoded = chr(int(octal, 8))
        if decoded == "\x00":
            raise ArtifactPublicationError(
                "Linux mount provenance contains a null path byte"
            )
        result.append(decoded)
        index += 4
    return "".join(result)


def _normalized_mount_path(field: str) -> PurePosixPath:
    value = _unescape_linux_mount_field(field)
    normalized = posixpath.normpath(value)
    if not normalized.startswith("/"):
        raise ArtifactPublicationError(
            "Linux mount provenance path must be absolute"
        )
    return PurePosixPath(normalized)


def _parse_linux_mountinfo(value: str) -> dict[int, _LinuxMountInfo]:
    mounts: dict[int, _LinuxMountInfo] = {}
    try:
        for line in value.splitlines():
            fields = line.split()
            separator = fields.index("-")
            if separator < 6 or len(fields) < separator + 4:
                raise ValueError("mountinfo field count")
            mount_id = int(fields[0])
            parent_id = int(fields[1])
            device = fields[2]
            if not re.fullmatch(r"\d+:\d+", device):
                raise ValueError("mountinfo device")
            if mount_id in mounts:
                raise ValueError("duplicate mount ID")
            mounts[mount_id] = _LinuxMountInfo(
                mount_id=mount_id,
                parent_id=parent_id,
                device=device,
                root=_normalized_mount_path(fields[3]),
                mountpoint=_normalized_mount_path(fields[4]),
            )
    except (IndexError, TypeError, ValueError) as exc:
        raise ArtifactPublicationError(
            "Linux mount provenance cannot be parsed consistently"
        ) from exc
    if not mounts:
        raise ArtifactPublicationError("Linux mount provenance is empty")
    return mounts


def _read_linux_mountinfo() -> dict[int, _LinuxMountInfo]:
    try:
        with open("/proc/self/mountinfo", encoding="utf-8") as stream:
            return _parse_linux_mountinfo(stream.read())
    except OSError as exc:
        raise ArtifactPublicationError(
            "Linux mount provenance cannot be inspected"
        ) from exc


def _underlying_location_for_mount(
    mount: _LinuxMountInfo,
    path: PurePosixPath,
) -> tuple[str, PurePosixPath]:
    normalized_path = PurePosixPath(posixpath.normpath(path.as_posix()))
    try:
        relative = normalized_path.relative_to(mount.mountpoint)
    except ValueError as exc:
        raise ArtifactPublicationError(
            "Linux fd path is inconsistent with its mountpoint"
        ) from exc
    underlying = PurePosixPath(
        posixpath.normpath(
            posixpath.join(mount.root.as_posix(), relative.as_posix())
        )
    )
    if not underlying.is_absolute():
        raise ArtifactPublicationError(
            "Linux underlying mount location is not absolute"
        )
    return mount.device, underlying


def _linux_underlying_location(
    descriptor: int,
    path: Path,
    mounts: Mapping[int, _LinuxMountInfo],
) -> tuple[str, PurePosixPath]:
    mount_id = _linux_mount_id_from_fd(descriptor)
    try:
        mount = mounts[mount_id]
    except KeyError as exc:
        raise ArtifactPublicationError(
            "Linux fd mount identity is absent from mount provenance"
        ) from exc
    return _underlying_location_for_mount(
        mount,
        PurePosixPath(path.as_posix()),
    )


def _reject_protected_underlying_alias(
    bound_locations: Iterable[tuple[str, PurePosixPath]],
    protected_locations: Iterable[tuple[str, PurePosixPath]],
) -> None:
    protected = tuple(protected_locations)
    for device, location in bound_locations:
        for protected_device, protected_location in protected:
            if device != protected_device:
                continue
            try:
                location.relative_to(protected_location)
            except ValueError:
                continue
            raise ArtifactPublicationError(
                "artifact publication underlying location aliases a protected root"
            )


def _parse_linux_mount_id(fdinfo: str) -> int:
    for line in fdinfo.splitlines():
        key, separator, value = line.partition(":")
        if key == "mnt_id" and separator:
            try:
                return int(value.strip())
            except ValueError as exc:
                raise ArtifactPublicationError(
                    "artifact publication mount identity is malformed"
                ) from exc
    raise ArtifactPublicationError(
        "artifact publication mount identity is unavailable"
    )


def _linux_mount_id_from_fd(descriptor: int) -> int:
    try:
        with open(
            f"/proc/self/fdinfo/{descriptor}",
            encoding="utf-8",
        ) as stream:
            return _parse_linux_mount_id(stream.read())
    except OSError as exc:
        raise ArtifactPublicationError(
            "artifact publication mount identity cannot be inspected"
        ) from exc


def _require_single_mount_identity(
    anchor_mount_id: int,
    ancestry_mount_ids: Iterable[int],
) -> None:
    if any(mount_id != anchor_mount_id for mount_id in ancestry_mount_ids):
        raise ArtifactPublicationError(
            "artifact publication ancestry crosses a mount boundary"
        )


def _reject_protected_identity_alias(
    bound_identities: Iterable[tuple[int, int, int]],
    protected_identities: Iterable[tuple[int, int, int]],
) -> None:
    protected_objects = {
        (device, inode)
        for device, inode, _ in protected_identities
    }
    if any(
        (device, inode) in protected_objects
        for device, inode, _ in bound_identities
    ):
        raise ArtifactPublicationError(
            "artifact publication ancestry aliases a protected root"
        )


def sha256_file(path: Path) -> str:
    """Hash one repository/build artifact without loading it into memory."""

    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        while chunk := stream.read(_HASH_CHUNK_BYTES):
            digest.update(chunk)
    return digest.hexdigest()


def _fsync_data(stream) -> None:
    try:
        os.fsync(stream.fileno())
    except OSError as exc:
        if exc.errno not in _UNSUPPORTED_FSYNC_ERRNOS:
            raise


def _fsync_descriptor(descriptor: int) -> None:
    try:
        os.fsync(descriptor)
    except OSError as exc:
        if exc.errno not in _UNSUPPORTED_FSYNC_ERRNOS:
            raise


def _absolute_lexical_path(path: Path, *, label: str) -> Path:
    candidate = Path(path)
    if ".." in candidate.parts:
        raise ArtifactPublicationError(f"{label} may not contain parent traversal")
    if not candidate.is_absolute():
        candidate = Path.cwd() / candidate
    try:
        return Path(os.path.abspath(candidate))
    except (OSError, TypeError, ValueError) as exc:
        raise ArtifactPublicationError(f"{label} cannot be normalized") from exc


def _path_identity(path: Path) -> str:
    try:
        raw_path = os.fspath(path)
        if not isinstance(raw_path, str) or not Path(raw_path).is_absolute():
            raise ValueError("path is not absolute")
        return os.path.normcase(os.path.normpath(raw_path))
    except (OSError, TypeError, ValueError) as exc:
        raise ArtifactPublicationError(
            "artifact publication path cannot be normalized"
        ) from exc


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _nearest_existing_directory(path: Path) -> Path:
    candidate = path
    while True:
        try:
            metadata = candidate.lstat()
        except FileNotFoundError:
            parent = candidate.parent
            if parent == candidate:
                raise ArtifactPublicationError(
                    "artifact publication has no existing filesystem ancestor"
                )
            candidate = parent
            continue
        except OSError as exc:
            raise ArtifactPublicationError(
                "artifact publication ancestry cannot be inspected"
            ) from exc
        if not stat_module.S_ISDIR(metadata.st_mode):
            raise ArtifactPublicationError(
                "artifact publication ancestor must be a directory"
            )
        return candidate


def _linux_final_path_from_fd(descriptor: int) -> Path:
    try:
        final_path = Path(os.readlink(f"/proc/self/fd/{descriptor}"))
    except OSError as exc:
        raise ArtifactPublicationError(
            "artifact publication descriptor final path cannot be inspected"
        ) from exc
    if not final_path.is_absolute():
        raise ArtifactPublicationError(
            "artifact publication descriptor final path is not absolute"
        )
    return final_path


def _windows_api():
    import ctypes
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    create_file = kernel32.CreateFileW
    create_file.argtypes = (
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.LPVOID,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.HANDLE,
    )
    create_file.restype = wintypes.HANDLE
    close_handle = kernel32.CloseHandle
    close_handle.argtypes = (wintypes.HANDLE,)
    close_handle.restype = wintypes.BOOL
    final_path = kernel32.GetFinalPathNameByHandleW
    final_path.argtypes = (
        wintypes.HANDLE,
        wintypes.LPWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
    )
    final_path.restype = wintypes.DWORD
    information = kernel32.GetFileInformationByHandleEx
    information.argtypes = (
        wintypes.HANDLE,
        wintypes.INT,
        wintypes.LPVOID,
        wintypes.DWORD,
    )
    information.restype = wintypes.BOOL
    return ctypes, wintypes, create_file, close_handle, final_path, information


def _windows_handle_final_path(handle) -> Path:
    ctypes, _, _, _, get_final_path, _ = _windows_api()
    buffer_size = 512
    while True:
        buffer = ctypes.create_unicode_buffer(buffer_size)
        length = get_final_path(handle, buffer, buffer_size, 0)
        if length == 0:
            raise ctypes.WinError(ctypes.get_last_error())
        if length < buffer_size:
            value = buffer.value
            break
        buffer_size = length + 1
    extended_prefix = "\\\\?\\"
    if value.startswith(f"{extended_prefix}UNC\\"):
        value = f"\\\\{value[len(extended_prefix) + 4:]}"
    elif value.startswith(extended_prefix):
        value = value[len(extended_prefix):]
    final_path = Path(value)
    if not final_path.is_absolute():
        raise ArtifactPublicationError(
            "artifact publication handle final path is not absolute"
        )
    return final_path


def _windows_handle_attributes(handle) -> tuple[int, int]:
    ctypes, wintypes, _, _, _, get_information = _windows_api()

    class FileAttributeTagInfo(ctypes.Structure):
        _fields_ = (
            ("FileAttributes", wintypes.DWORD),
            ("ReparseTag", wintypes.DWORD),
        )

    info = FileAttributeTagInfo()
    if not get_information(handle, 9, ctypes.byref(info), ctypes.sizeof(info)):
        raise ctypes.WinError(ctypes.get_last_error())
    return int(info.FileAttributes), int(info.ReparseTag)


def _windows_handle_identity(handle) -> tuple[int, int, int]:
    import ctypes
    from ctypes import wintypes

    class ByHandleFileInformation(ctypes.Structure):
        _fields_ = (
            ("FileAttributes", wintypes.DWORD),
            ("CreationTime", wintypes.FILETIME),
            ("LastAccessTime", wintypes.FILETIME),
            ("LastWriteTime", wintypes.FILETIME),
            ("VolumeSerialNumber", wintypes.DWORD),
            ("FileSizeHigh", wintypes.DWORD),
            ("FileSizeLow", wintypes.DWORD),
            ("NumberOfLinks", wintypes.DWORD),
            ("FileIndexHigh", wintypes.DWORD),
            ("FileIndexLow", wintypes.DWORD),
        )

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    get_information = kernel32.GetFileInformationByHandle
    get_information.argtypes = (
        wintypes.HANDLE,
        ctypes.POINTER(ByHandleFileInformation),
    )
    get_information.restype = wintypes.BOOL
    information = ByHandleFileInformation()
    if not get_information(handle, ctypes.byref(information)):
        raise ctypes.WinError(ctypes.get_last_error())
    file_index = (
        int(information.FileIndexHigh) << 32
    ) | int(information.FileIndexLow)
    return int(information.VolumeSerialNumber), file_index, 0


def _open_windows_handle(path: Path, *, directory: bool):
    ctypes, _, create_file, close_handle, _, _ = _windows_api()
    file_list_directory = 0x0001
    file_read_attributes = 0x0080
    generic_read = 0x80000000
    file_share_read = 0x00000001
    file_share_write = 0x00000002
    open_existing = 3
    file_flag_backup_semantics = 0x02000000
    file_flag_open_reparse_point = 0x00200000
    access = (
        file_list_directory | file_read_attributes
        if directory
        else generic_read
    )
    flags = file_flag_open_reparse_point
    if directory:
        flags |= file_flag_backup_semantics
    handle = create_file(
        os.fspath(path),
        access,
        file_share_read | file_share_write,
        None,
        open_existing,
        flags,
        None,
    )
    invalid_handle = ctypes.c_void_p(-1).value
    if handle == invalid_handle:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        attributes, _ = _windows_handle_attributes(handle)
        is_directory = bool(attributes & 0x10)
        is_reparse = bool(attributes & 0x400)
        if is_reparse:
            raise ArtifactPublicationError(
                "artifact publication path contains a reparse point"
            )
        if is_directory != directory:
            raise ArtifactPublicationError(
                "artifact publication handle has the wrong file type"
            )
        if _path_identity(_windows_handle_final_path(handle)) != _path_identity(path):
            raise ArtifactPublicationError(
                "artifact publication handle final path differs from its bound path"
            )
        return handle
    except BaseException:
        close_handle(handle)
        raise


class BoundArtifactPublication:
    """A publication transaction whose output ancestry stays handle-bound."""

    def __init__(
        self,
        directory: Path,
        *,
        anchor_root: Path,
        allowed_root: Path,
        forbidden_roots: Iterable[Path],
    ) -> None:
        self.directory = _absolute_lexical_path(directory, label="output directory")
        self.anchor_root = _absolute_lexical_path(anchor_root, label="anchor root")
        self.allowed_root = _absolute_lexical_path(allowed_root, label="allowed root")
        self.forbidden_roots = tuple(
            _absolute_lexical_path(path, label="forbidden root")
            for path in forbidden_roots
        )
        if not _is_within(self.allowed_root, self.anchor_root):
            raise ArtifactPublicationError(
                "allowed artifact root must remain under its anchor"
            )
        if not _is_within(self.directory, self.allowed_root):
            raise ArtifactPublicationError(
                "artifact output directory must remain under its allowed root"
            )
        for forbidden_root in self.forbidden_roots:
            if (
                _is_within(self.directory, forbidden_root)
                or _is_within(forbidden_root, self.directory)
            ):
                raise ArtifactPublicationError(
                    "artifact output directory overlaps a forbidden root"
                )
        self._bound: list[tuple[Path, int]] = []
        self._posix_identities: dict[int, tuple[int, int, int]] = {}
        self._anchor_mount_id: int | None = None
        self._published: list[_PublishedArtifact] = []
        self._committed = False

    @property
    def _directory_binding(self) -> int:
        if not self._bound:
            raise ArtifactPublicationError("artifact publication is not bound")
        return self._bound[-1][1]

    def bind(self) -> None:
        base = _nearest_existing_directory(self.anchor_root)
        try:
            relative = self.directory.relative_to(base)
        except ValueError as exc:
            raise ArtifactPublicationError(
                "artifact publication ancestry is not lexical"
            ) from exc
        current = base
        components = [base]
        for part in relative.parts:
            current /= part
            components.append(current)
        if os.name == "nt":
            self._bind_windows(components)
        else:
            self._bind_posix(components)
            anchor_binding = next(
                binding
                for expected, binding in self._bound
                if _path_identity(expected) == _path_identity(self.anchor_root)
            )
            self._anchor_mount_id = self._posix_identities[anchor_binding][2]
            _require_single_mount_identity(
                self._anchor_mount_id,
                (
                    self._posix_identities[binding][2]
                    for expected, binding in self._bound
                    if _is_within(expected, self.anchor_root)
                ),
            )
        self._verify_authorized_location()
        final_directory = self._final_directory_path()
        for forbidden_root in self.forbidden_roots:
            try:
                resolved_forbidden = forbidden_root.resolve(strict=False)
            except (OSError, RuntimeError, ValueError) as exc:
                raise ArtifactPublicationError(
                    "forbidden artifact root cannot be resolved"
                ) from exc
            if _is_within(final_directory, resolved_forbidden):
                raise ArtifactPublicationError(
                    "bound artifact output overlaps a forbidden root"
                )

    def _bind_windows(self, components: list[Path]) -> None:
        for index, component in enumerate(components):
            if index:
                try:
                    component.mkdir()
                except FileExistsError:
                    pass
            handle = _open_windows_handle(component, directory=True)
            self._bound.append((component, handle))

    def _bind_posix(self, components: list[Path]) -> None:
        flags = (
            os.O_RDONLY
            | getattr(os, "O_CLOEXEC", 0)
            | getattr(os, "O_DIRECTORY", 0)
            | getattr(os, "O_NOFOLLOW", 0)
        )
        descriptor: int | None = None
        for index, component in enumerate(components):
            if index == 0:
                descriptor = os.open(component, flags)
            else:
                assert descriptor is not None
                try:
                    os.mkdir(component.name, dir_fd=descriptor)
                except FileExistsError:
                    pass
                descriptor = os.open(component.name, flags, dir_fd=descriptor)
            self._bound.append((component, descriptor))
            metadata = os.fstat(descriptor)
            mount_id = _linux_mount_id_from_fd(descriptor)
            self._posix_identities[descriptor] = (
                metadata.st_dev,
                metadata.st_ino,
                mount_id,
            )

    def _verify_ancestry(self) -> None:
        if not self._bound:
            raise ArtifactPublicationError("artifact publication ancestry is unbound")
        for expected, binding in self._bound:
            if os.name == "nt":
                attributes, _ = _windows_handle_attributes(binding)
                if not attributes & 0x10 or attributes & 0x400:
                    raise ArtifactPublicationError(
                        "bound artifact ancestry changed file type"
                    )
                final_path = _windows_handle_final_path(binding)
            else:
                metadata = os.fstat(binding)
                if not stat_module.S_ISDIR(metadata.st_mode):
                    raise ArtifactPublicationError(
                        "bound artifact ancestry is no longer a directory"
                    )
                if not sys.platform.startswith("linux"):
                    raise ArtifactPublicationError(
                        "bound artifact ancestry cannot be proven on this platform"
                    )
                final_path = _linux_final_path_from_fd(binding)
                expected_identity = self._posix_identities.get(binding)
                current_identity = (
                    metadata.st_dev,
                    metadata.st_ino,
                    _linux_mount_id_from_fd(binding),
                )
                if current_identity != expected_identity:
                    raise ArtifactPublicationError(
                        "bound artifact ancestry changed mount or inode identity"
                    )
                if (
                    _is_within(expected, self.anchor_root)
                    and current_identity[2] != self._anchor_mount_id
                ):
                    raise ArtifactPublicationError(
                        "bound artifact ancestry changed mount identity"
                    )
            if _path_identity(final_path) != _path_identity(expected):
                raise ArtifactPublicationError(
                    "bound artifact output ancestry changed during publication"
                )

    def _bound_directory_identities(self) -> tuple[tuple[int, int, int], ...]:
        if os.name == "nt":
            return tuple(
                _windows_handle_identity(binding)
                for _, binding in self._bound
            )
        return tuple(
            self._posix_identities[binding]
            for _, binding in self._bound
        )

    def _protected_root_identities(self) -> tuple[tuple[int, int, int], ...]:
        identities: list[tuple[int, int, int]] = []
        for protected_root in self.forbidden_roots:
            try:
                protected_root.lstat()
            except FileNotFoundError:
                continue
            if os.name == "nt":
                handle = _open_windows_handle(protected_root, directory=True)
                try:
                    identities.append(_windows_handle_identity(handle))
                finally:
                    _, _, _, close_handle, _, _ = _windows_api()
                    close_handle(handle)
                continue
            descriptor = os.open(
                protected_root,
                os.O_RDONLY
                | getattr(os, "O_CLOEXEC", 0)
                | getattr(os, "O_DIRECTORY", 0)
                | getattr(os, "O_NOFOLLOW", 0),
            )
            try:
                if _path_identity(
                    _linux_final_path_from_fd(descriptor)
                ) != _path_identity(protected_root):
                    raise ArtifactPublicationError(
                        "protected root resolves through an alias"
                    )
                metadata = os.fstat(descriptor)
                identities.append(
                    (
                        metadata.st_dev,
                        metadata.st_ino,
                        _linux_mount_id_from_fd(descriptor),
                    )
                )
            finally:
                os.close(descriptor)
        return tuple(identities)

    def _reject_protected_aliases(self) -> None:
        _reject_protected_identity_alias(
            self._bound_directory_identities(),
            self._protected_root_identities(),
        )

    def _protected_root_underlying_locations(
        self,
        mounts: Mapping[int, _LinuxMountInfo],
    ) -> tuple[tuple[str, PurePosixPath], ...]:
        locations: list[tuple[str, PurePosixPath]] = []
        flags = (
            os.O_RDONLY
            | getattr(os, "O_CLOEXEC", 0)
            | getattr(os, "O_DIRECTORY", 0)
            | getattr(os, "O_NOFOLLOW", 0)
        )
        for protected_root in self.forbidden_roots:
            try:
                protected_root.lstat()
            except FileNotFoundError:
                continue
            descriptor = os.open(protected_root, flags)
            try:
                if _path_identity(
                    _linux_final_path_from_fd(descriptor)
                ) != _path_identity(protected_root):
                    raise ArtifactPublicationError(
                        "protected root resolves through an alias"
                    )
                locations.append(
                    _linux_underlying_location(
                        descriptor,
                        protected_root,
                        mounts,
                    )
                )
            finally:
                os.close(descriptor)
        return tuple(locations)

    @contextmanager
    def _fresh_posix_ancestry(self) -> Iterator[int]:
        """Rebind the lexical repo ancestry and yield its verified output fd."""

        flags = (
            os.O_RDONLY
            | getattr(os, "O_CLOEXEC", 0)
            | getattr(os, "O_DIRECTORY", 0)
            | getattr(os, "O_NOFOLLOW", 0)
        )
        descriptors: list[int] = []
        identities: list[tuple[int, int, int]] = []
        locations: list[tuple[str, PurePosixPath]] = []
        mounts = _read_linux_mountinfo()
        try:
            for index, (expected, binding) in enumerate(self._bound):
                if index == 0:
                    descriptor = os.open(expected, flags)
                else:
                    descriptor = os.open(
                        expected.name,
                        flags,
                        dir_fd=descriptors[-1],
                    )
                descriptors.append(descriptor)
                metadata = os.fstat(descriptor)
                identity = (
                    metadata.st_dev,
                    metadata.st_ino,
                    _linux_mount_id_from_fd(descriptor),
                )
                identities.append(identity)
                locations.append(
                    _linux_underlying_location(descriptor, expected, mounts)
                )
                if identity != self._posix_identities[binding]:
                    raise ArtifactPublicationError(
                        "artifact output no longer resolves to its bound mount and inode"
                    )
                if _path_identity(
                    _linux_final_path_from_fd(descriptor)
                ) != _path_identity(expected):
                    raise ArtifactPublicationError(
                        "artifact output no longer resolves to its authorized path"
                    )
                if (
                    _is_within(expected, self.anchor_root)
                    and identity[2] != self._anchor_mount_id
                ):
                    raise ArtifactPublicationError(
                        "artifact output no longer resolves on the repository mount"
                    )
            _reject_protected_identity_alias(
                identities,
                self._protected_root_identities(),
            )
            _reject_protected_underlying_alias(
                locations,
                self._protected_root_underlying_locations(mounts),
            )
            yield descriptors[-1]
        finally:
            for descriptor in reversed(descriptors):
                os.close(descriptor)

    def _verify_authorized_location(self) -> None:
        """Re-resolve every lexical component to the same held directory chain."""

        self._verify_ancestry()
        if os.name == "nt":
            self._reject_protected_aliases()
            for expected, _ in self._bound:
                fresh_handle = _open_windows_handle(expected, directory=True)
                try:
                    if _path_identity(
                        _windows_handle_final_path(fresh_handle)
                    ) != _path_identity(expected):
                        raise ArtifactPublicationError(
                            "artifact output no longer resolves to its authorized path"
                        )
                finally:
                    _, _, _, close_handle, _, _ = _windows_api()
                    close_handle(fresh_handle)
            return

        with self._fresh_posix_ancestry():
            pass

    def _final_directory_path(self) -> Path:
        binding = self._directory_binding
        if os.name == "nt":
            return _windows_handle_final_path(binding)
        return _linux_final_path_from_fd(binding)

    def _target_name(self, path: Path) -> str:
        target = _absolute_lexical_path(path, label="artifact target")
        if _path_identity(target.parent) != _path_identity(self.directory):
            raise ArtifactPublicationError(
                "artifact target is outside the bound output directory"
            )
        if not target.name or target.name in (".", ".."):
            raise ArtifactPublicationError("artifact target name is invalid")
        return target.name

    def _open_target_descriptor(self, name: str) -> int:
        expected = self.directory / name
        if os.name == "nt":
            handle = _open_windows_handle(expected, directory=False)
            try:
                import msvcrt

                return msvcrt.open_osfhandle(
                    int(handle),
                    os.O_RDONLY | getattr(os, "O_BINARY", 0),
                )
            except BaseException:
                _, _, _, close_handle, _, _ = _windows_api()
                close_handle(handle)
                raise
        flags = (
            os.O_RDONLY
            | getattr(os, "O_CLOEXEC", 0)
            | getattr(os, "O_NOFOLLOW", 0)
            | getattr(os, "O_NONBLOCK", 0)
        )
        descriptor = os.open(name, flags, dir_fd=self._directory_binding)
        try:
            metadata = os.fstat(descriptor)
            if not stat_module.S_ISREG(metadata.st_mode):
                raise ArtifactPublicationError(
                    "artifact publication target must be a regular file"
                )
            expected_final = self.directory / name
            if _path_identity(
                _linux_final_path_from_fd(descriptor)
            ) != _path_identity(expected_final):
                raise ArtifactPublicationError(
                    "artifact publication target final path changed"
                )
        except BaseException:
            os.close(descriptor)
            raise
        return descriptor

    def _bound_digest_size(self, name: str) -> tuple[str, int]:
        descriptor = self._open_target_descriptor(name)
        digest = hashlib.sha256()
        size = 0
        try:
            before = os.fstat(descriptor)
            while chunk := os.read(descriptor, _HASH_CHUNK_BYTES):
                digest.update(chunk)
                size += len(chunk)
            after = os.fstat(descriptor)
            if (
                (before.st_dev, before.st_ino, before.st_size)
                != (after.st_dev, after.st_ino, after.st_size)
                or getattr(before, "st_mtime_ns", None)
                != getattr(after, "st_mtime_ns", None)
                or getattr(before, "st_ctime_ns", None)
                != getattr(after, "st_ctime_ns", None)
            ):
                raise ArtifactPublicationError(
                    "artifact content changed while it was being verified"
                )
            if os.name == "nt":
                path_metadata = (self.directory / name).lstat()
            else:
                path_metadata = os.stat(
                    name,
                    dir_fd=self._directory_binding,
                    follow_symlinks=False,
                )
            if (path_metadata.st_dev, path_metadata.st_ino) != (
                after.st_dev,
                after.st_ino,
            ):
                raise ArtifactPublicationError(
                    "artifact target changed while it was being verified"
                )
        finally:
            os.close(descriptor)
        return digest.hexdigest(), size

    def _entry_exists(self, name: str) -> bool:
        try:
            if os.name == "nt":
                (self.directory / name).lstat()
            else:
                os.stat(
                    name,
                    dir_fd=self._directory_binding,
                    follow_symlinks=False,
                )
        except FileNotFoundError:
            return False
        return True

    def _rename(self, source: str, target: str) -> None:
        if os.name == "nt":
            os.rename(self.directory / source, self.directory / target)
            return
        os.rename(
            source,
            target,
            src_dir_fd=self._directory_binding,
            dst_dir_fd=self._directory_binding,
        )

    def _backup_existing_target(self, record: _PublishedArtifact) -> None:
        try:
            descriptor = self._open_target_descriptor(record.name)
        except FileNotFoundError:
            return
        try:
            metadata = os.fstat(descriptor)
            identity = (metadata.st_dev, metadata.st_ino)
        finally:
            os.close(descriptor)
        for _ in range(128):
            backup_name = (
                f".{record.name}.{secrets.token_hex(16)}.publication-backup"
            )
            if not self._entry_exists(backup_name):
                break
        else:
            raise ArtifactPublicationError(
                "artifact publication could not allocate a unique backup"
            )
        self._rename(record.name, backup_name)
        record.backup_name = backup_name
        record.backup_created = True
        backup_descriptor = self._open_target_descriptor(backup_name)
        try:
            backup_metadata = os.fstat(backup_descriptor)
            if (backup_metadata.st_dev, backup_metadata.st_ino) != identity:
                raise ArtifactPublicationError(
                    "artifact publication backup changed file identity"
                )
        finally:
            os.close(backup_descriptor)
        if os.name != "nt":
            _fsync_descriptor(self._directory_binding)

    def _temporary(self, name: str) -> tuple[int, str]:
        if os.name == "nt":
            descriptor, temporary_path = tempfile.mkstemp(
                prefix=f".{name}.",
                suffix=".tmp",
                dir=self.directory,
            )
            return descriptor, Path(temporary_path).name
        flags = (
            os.O_WRONLY
            | os.O_CREAT
            | os.O_EXCL
            | getattr(os, "O_CLOEXEC", 0)
            | getattr(os, "O_NOFOLLOW", 0)
        )
        for _ in range(128):
            temporary_name = f".{name}.{secrets.token_hex(16)}.tmp"
            try:
                descriptor = os.open(
                    temporary_name,
                    flags,
                    0o600,
                    dir_fd=self._directory_binding,
                )
            except FileExistsError:
                continue
            return descriptor, temporary_name
        raise ArtifactPublicationError(
            "artifact publication could not allocate a unique temporary"
        )

    def _replace(self, temporary_name: str, name: str) -> None:
        if os.name == "nt":
            os.replace(self.directory / temporary_name, self.directory / name)
            return
        with self._fresh_posix_ancestry() as fresh_directory:
            os.replace(
                temporary_name,
                name,
                src_dir_fd=fresh_directory,
                dst_dir_fd=fresh_directory,
            )

    def _unlink(self, name: str, *, rollback: bool = False) -> None:
        try:
            if os.name == "nt":
                (self.directory / name).unlink()
            else:
                os.unlink(name, dir_fd=self._directory_binding)
        except FileNotFoundError:
            if not rollback or not sys.platform.startswith("linux"):
                return
            try:
                Path(f"/proc/self/fd/{self._directory_binding}/{name}").unlink()
            except FileNotFoundError:
                raise ArtifactPublicationError(
                    "artifact rollback requires a verified ancestry rebind"
                )

    def _publish_bytes(self, name: str, payload: bytes) -> None:
        self._verify_ancestry()
        record = _PublishedArtifact(
            name=name,
            expected_sha256=hashlib.sha256(payload).hexdigest(),
            expected_size=len(payload),
        )
        self._published.append(record)
        self._backup_existing_target(record)
        descriptor, temporary_name = self._temporary(name)
        try:
            stream = os.fdopen(descriptor, "wb", closefd=True)
            descriptor = -1
            with stream:
                stream.write(payload)
                stream.flush()
                _fsync_data(stream)
            self._verify_ancestry()
            self._replace(temporary_name, name)
            temporary_name = ""
            record.published = True
            if os.name != "nt":
                _fsync_descriptor(self._directory_binding)
            self._verify_ancestry()
            digest, size = self._bound_digest_size(name)
            if (
                digest != record.expected_sha256
                or size != record.expected_size
            ):
                raise ArtifactPublicationError(
                    "published artifact content differs from its expected digest or size"
                )
        finally:
            if descriptor >= 0:
                os.close(descriptor)
            if temporary_name:
                self._unlink(temporary_name)

    def write_bytes(self, path: Path, payload: bytes) -> None:
        """Atomically publish bytes relative to this bound transaction."""

        if not isinstance(payload, bytes):
            raise TypeError("atomic artifact payload must be bytes")
        name = self._target_name(path)
        if any(record.name == name for record in self._published):
            raise ArtifactPublicationError(
                "artifact target was already published in this transaction"
            )
        self._publish_bytes(name, payload)

    def sha256(self, path: Path) -> str:
        """Hash a published target through the still-bound output ancestry."""

        name = self._target_name(path)
        self._verify_ancestry()
        digest, _ = self._bound_digest_size(name)
        self._verify_ancestry()
        return digest

    def _rollback_record(self, record: _PublishedArtifact) -> None:
        if record.published:
            self._unlink(record.name, rollback=True)
            record.published = False
        if record.backup_created:
            assert record.backup_name is not None
            self._rename(record.backup_name, record.name)
            record.backup_created = False
        if os.name != "nt":
            _fsync_descriptor(self._directory_binding)

    def rollback(self) -> None:
        pending: list[_PublishedArtifact] = []
        for record in reversed(self._published):
            try:
                self._rollback_record(record)
            except OSError:
                pending.append(record)
        if not pending:
            self._published.clear()
            return
        rebound_directory = self._final_directory_path()
        self.close()
        try:
            with bind_artifact_publication(
                rebound_directory,
                anchor_root=self.anchor_root,
                allowed_root=self.allowed_root,
                forbidden_roots=self.forbidden_roots,
            ) as rebound:
                for record in pending:
                    if record.published:
                        rebound._unlink(record.name)
                        record.published = False
                    if record.backup_created:
                        assert record.backup_name is not None
                        rebound._rename(record.backup_name, record.name)
                        record.backup_created = False
        except (OSError, RuntimeError, TypeError, ValueError) as exc:
            raise ArtifactPublicationError(
                "artifact publication rollback failed after ancestry changed"
            ) from exc
        self._published.clear()

    def _before_final_verify(self) -> None:
        """Internal deterministic race-injection point used only by tests."""

    def _final_verify(self) -> None:
        self._verify_authorized_location()
        for record in self._published:
            if not record.published:
                raise ArtifactPublicationError(
                    "artifact publication did not publish every tracked target"
                )
            digest, size = self._bound_digest_size(record.name)
            if (
                digest != record.expected_sha256
                or size != record.expected_size
            ):
                raise ArtifactPublicationError(
                    "published artifact content changed before commit"
                )
        self._verify_authorized_location()

    def _postcommit_cleanup(
        self,
        committed: tuple[_PublishedArtifact, ...],
    ) -> None:
        """Best-effort cleanup after the verified commit point; never invalidates it."""

        for record in committed:
            if record.backup_created:
                assert record.backup_name is not None
                try:
                    self._unlink(record.backup_name)
                except OSError:
                    continue
                record.backup_created = False
        if os.name != "nt":
            try:
                _fsync_descriptor(self._directory_binding)
            except OSError:
                pass

    def commit(self) -> None:
        """Finalize outputs in an operator-controlled repository build tree.

        POSIX directory descriptors cannot prevent a same-UID or privileged peer
        from mutating the namespace after the kernel's final verification and
        commit instant. The repository build tree is therefore an
        operator-controlled boundary. Final verification is the last fallible
        precommit operation; this narrows the scheduler window without claiming
        impossible cross-process POSIX rename prevention.
        """

        committed = tuple(self._published)
        self._before_final_verify()
        self._final_verify()
        self._committed = True
        self._published.clear()
        self._postcommit_cleanup(committed)

    def close(self) -> None:
        if os.name == "nt":
            _, _, _, close_handle, _, _ = _windows_api()
            for _, handle in reversed(self._bound):
                close_handle(handle)
        else:
            for _, descriptor in reversed(self._bound):
                os.close(descriptor)
        self._bound.clear()
        self._posix_identities.clear()


@contextmanager
def bind_artifact_publication(
    directory: Path,
    *,
    anchor_root: Path,
    allowed_root: Path,
    forbidden_roots: Iterable[Path] = (),
) -> Iterator[BoundArtifactPublication]:
    """Bind and hold verified output ancestry for one publication transaction."""

    publication = BoundArtifactPublication(
        directory,
        anchor_root=anchor_root,
        allowed_root=allowed_root,
        forbidden_roots=forbidden_roots,
    )
    try:
        publication.bind()
        try:
            yield publication
        except BaseException:
            publication.rollback()
            raise
        else:
            try:
                publication.commit()
            except BaseException:
                if not publication._committed:
                    publication.rollback()
                raise
    except ArtifactPublicationError:
        raise
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        raise ArtifactPublicationError(
            f"artifact publication failed: {exc}"
        ) from exc
    finally:
        publication.close()


def write_atomic_bytes(
    path: Path,
    payload: bytes,
    *,
    publication: BoundArtifactPublication | None = None,
) -> None:
    """Publish bytes atomically through verified, handle-bound ancestry."""

    if not isinstance(payload, bytes):
        raise TypeError("atomic artifact payload must be bytes")
    if publication is not None:
        publication.write_bytes(Path(path), payload)
        return
    target = Path(path)
    with bind_artifact_publication(
        target.parent,
        anchor_root=target.parent,
        allowed_root=target.parent,
    ) as bound:
        bound.write_bytes(target, payload)


def _canonical_json_bytes(value: Any, *, indent: int | None) -> bytes:
    payload = json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        indent=indent,
        separators=None if indent is not None else (",", ":"),
        sort_keys=True,
    )
    return (payload + "\n").encode("utf-8")


def write_atomic_json(
    path: Path,
    value: Any,
    *,
    publication: BoundArtifactPublication | None = None,
) -> None:
    """Write deterministic pretty JSON after complete serialization succeeds."""

    write_atomic_bytes(
        Path(path),
        _canonical_json_bytes(value, indent=4),
        publication=publication,
    )


def write_atomic_jsonl(
    path: Path,
    records: Iterable[Mapping],
    *,
    publication: BoundArtifactPublication | None = None,
) -> None:
    """Write compact deterministic JSONL without publishing partial output."""

    lines: list[bytes] = []
    for index, record in enumerate(records, start=1):
        if not isinstance(record, Mapping):
            raise TypeError(f"JSONL record {index} must be a mapping")
        lines.append(_canonical_json_bytes(dict(record), indent=None))
    write_atomic_bytes(
        Path(path),
        b"".join(lines),
        publication=publication,
    )


__all__ = [
    "ArtifactPublicationError",
    "BoundArtifactPublication",
    "bind_artifact_publication",
    "sha256_file",
    "write_atomic_bytes",
    "write_atomic_json",
    "write_atomic_jsonl",
]
