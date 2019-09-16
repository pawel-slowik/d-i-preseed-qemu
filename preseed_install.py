#!/usr/bin/env python3
"""A QEMU wrapper for performing automated Debian installations in QEMU virtual machines."""

import sys
import os.path
import subprocess
import re
import tempfile
import shlex
from typing import Tuple, NamedTuple, Iterable, IO, Optional

Partition = NamedTuple("Partition", [
    ("type", str),
    ("sector_size", int),
    ("start_sector", int),
    ("size_in_sectors", int),
    ("bootable", bool),
])

def install(
        iso_filename: str,
        preseed_url: str,
        output_filename: str,
        vnc_display: Optional[str] = None,
    ) -> None:
    """Perform automated Debian installation from an ISO image into a QEMU disk image."""

    def get_command_for_arch(iso_filename: str) -> str:
        if "amd64" in iso_filename:
            return "qemu-system-x86_64"
        if "i386" in iso_filename:
            return "qemu-system-i386"
        if "arm64" in iso_filename:
            return "qemu-system-aarch64"
        raise ValueError("unsupported architecture: %s" % iso_filename)

    iso_kernel, iso_initrd = iso_get_boot_filenames(iso_filename)
    tmp_kernel = named_tmp(iso_extract_file(iso_filename, iso_kernel))
    tmp_initrd = named_tmp(iso_extract_file(iso_filename, iso_initrd))
    command = [
        get_command_for_arch(iso_filename),
        "-cpu", "max", "-m", "1G",
        "-append", " ".join("%s=%s" % (name, value) for name, value in [
            ("auto", "true"),
            ("priority", "critical"),
            ("url", preseed_url),
        ]),
        "-kernel", tmp_kernel.name,
        "-initrd", tmp_initrd.name,
        "-display", "vnc=%s" % vnc_display if vnc_display else "none",
        "-no-reboot",
    ]
    if iso_is_arm(iso_filename):
        command += [
            "-M", "virt",
            "-drive", "if=none,file=%s,format=qcow2,id=hd" % output_filename,
            "-device", "virtio-blk-pci,drive=hd",
            "-drive", "if=none,file=%s,id=cdrom,media=cdrom" % iso_filename,
            "-device", "virtio-scsi-device",
            "-device", "scsi-cd,drive=cdrom",
            "-netdev", "user,id=mynet",
            "-device", "virtio-net-pci,netdev=mynet",
        ]
    else:
        command += [
            "-enable-kvm", "-accel", "kvm",
            "-drive", "file=%s" % output_filename,
            "-cdrom", iso_filename,
            "-net", "nic", "-net", "user",
        ]
    subprocess.run(command, check=True)

def iso_get_boot_filenames(iso_filename: str) -> Tuple[str, str]:
    """Get the paths of the Debian installer kernel and initrd files for an ISO image."""
    va_path_map = {
        (9, "i386"): ("/install.386/vmlinuz", "/install.386/initrd.gz"),
        (9, "amd64"): ("/install.amd/vmlinuz", "/install.amd/initrd.gz"),
        (9, "arm64"): ("/install.a64/vmlinuz", "/install.a64/initrd.gz"),
        (10, "i386"): ("/install.386/vmlinuz", "/install.386/initrd.gz"),
        (10, "amd64"): ("/install.amd/vmlinuz", "/install.amd/initrd.gz"),
        (10, "arm64"): ("/install.a64/vmlinuz", "/install.a64/initrd.gz"),
    }
    version = get_debian_version(iso_filename)
    arch = get_debian_architecture(iso_filename)
    if (version, arch) in va_path_map:
        return va_path_map[(version, arch)]
    raise ValueError("unsupported Debian version or architecture: %s, %s" % (version, arch))

def get_debian_version(iso_filename: str) -> int:
    """Get the major Debian version for a ISO filename."""
    iso_filename = os.path.basename(iso_filename)
    match = re.search(r"^debian-([0-9]+)\.[0-9]+\.[0-9]+-", iso_filename)
    if not match:
        raise ValueError("can't read Debian version: %s" % iso_filename)
    return int(match.group(1))

def get_debian_architecture(iso_filename: str) -> str:
    """Get the Debian architecture for a ISO filename."""
    iso_filename = os.path.basename(iso_filename)
    match = re.search(r"^debian-[0-9.]+-([^-]+)-", iso_filename)
    if not match:
        raise ValueError("can't read Debian architecture: %s" % iso_filename)
    return match.group(1)

def iso_extract_file(iso_filename: str, extract_filename: str) -> bytes:
    """Extract a file from an ISO image and return its contents."""
    command = ["isoinfo", "-R", "-x", extract_filename, "-i", iso_filename]
    process = subprocess.run(command, capture_output=True, check=True)
    extracted: bytes = process.stdout
    if not extracted:
        raise ValueError(
            "failed to extract file: %s from ISO: %s"
            % (extract_filename, iso_filename)
        )
    return extracted

def create_image(filename: str, size: str) -> None:
    """Create a QEMU disk image. Will not overwrite an existing file."""
    if os.path.exists(filename):
        raise ValueError("already exists: %s" % filename)
    command = ["qemu-img", "create", "-f", "qcow2", filename, size]
    subprocess.run(command, check=True)

def extract_boot_files(image_filename: str) -> None:
    """Extract the Linux kernel and initrd files from a QEMU VM image.

    Will not overwrite an existing file."""
    if not os.path.exists(image_filename):
        raise ValueError("file not found: %s" % image_filename)
    image_base, _ = os.path.splitext(image_filename)
    kernel_filename = image_base + ".kernel"
    initrd_filename = image_base + ".initrd"
    # put temporary files on the same filesystem, because they might be too
    # large to fit elsewhere
    tmp_dir_base = os.path.dirname(os.path.realpath(image_filename))
    with tempfile.TemporaryDirectory(dir=tmp_dir_base) as tmp_dir:
        raw_filename = os.path.join(tmp_dir, image_base + ".raw")
        partition_filename = os.path.join(tmp_dir, image_base + ".bootable")
        image_to_raw(image_filename, raw_filename)
        extract_boot_partition(raw_filename, partition_filename)
        extract_partition_boot_files(partition_filename, kernel_filename, initrd_filename)

def image_to_raw(input_filename: str, output_filename: str) -> None:
    """Convert a QEMU disk image to raw format.

    Will not overwrite an existing file."""
    if not os.path.exists(input_filename):
        raise ValueError("file not found: %s" % input_filename)
    if os.path.exists(output_filename):
        raise ValueError("already exists: %s" % output_filename)
    command = ["qemu-img", "convert", "-O", "raw", input_filename, output_filename]
    subprocess.run(command, check=True)

def extract_boot_partition(image_filename: str, output_filename: str) -> None:
    """Extract the first bootable Linux partition from a disk image file.

    Will not overwrite an existing file. Does not support LVM."""
    if not os.path.exists(image_filename):
        raise ValueError("file not found: %s" % image_filename)
    if os.path.exists(output_filename):
        raise ValueError("already exists: %s" % output_filename)
    for partition in list_partitions(image_filename):
        if partition.type == "Linux" and partition.bootable:
            # use dd for sparse file support
            command = [
                "dd",
                "if=%s" % image_filename,
                "of=%s" % output_filename,
                "bs=%d" % partition.sector_size,
                "skip=%d" % partition.start_sector,
                "count=%d" % partition.size_in_sectors,
                "conv=sparse",
            ]
            subprocess.run(command, check=True, stderr=subprocess.DEVNULL)
            return
    raise ValueError("no bootable Linux partition found")

def list_partitions(image_filename: str) -> Iterable[Partition]:
    """List partitions in a disk image.

    Does not support LVM."""
    if not os.path.exists(image_filename):
        raise ValueError("file not found: %s" % image_filename)
    parser = [
        ("Type", r".+", lambda s: s.strip()),
        ("Start", r"[0-9]+", int),
        ("Sectors", r"[0-9]+", int),
        ("Boot", r"\*{0,1}", bool),
    ]
    column_spec = ",".join(header for header, _, _ in parser)
    header_regexp = r"\s+".join(header for header, _, _ in parser)
    data_regexp = r"\s+".join("(?P<%s>%s)" % (header, regexp) for header, regexp, _ in parser)
    postprocessors = {header: func for header, _, func in parser}
    command = ["/sbin/fdisk", "-l", "-o", column_spec, image_filename]
    process = subprocess.run(command, capture_output=True, text=True, check=True)
    sector_size = parse_fdisk_sector_size(process.stdout)
    units = parse_fdisk_units(process.stdout)
    if sector_size != units:
        raise ValueError(
            "partition table sector size and unit size differ: %d != %d"
            % (sector_size, units)
        )
    in_list = False
    for line in process.stdout.splitlines():
        if re.fullmatch(header_regexp, line):
            in_list = True
            continue
        if in_list:
            match = re.fullmatch(data_regexp, line)
            if not match:
                raise ValueError("unable to parse partition line: %s" % line)
            parsed = {
                header: postprocessors[header](value) # type: ignore
                for header, value in match.groupdict().items()
            }
            yield Partition(
                sector_size=sector_size,
                type=parsed["Type"],
                start_sector=parsed["Start"],
                size_in_sectors=parsed["Sectors"],
                bootable=parsed["Boot"],
            )

def parse_fdisk_units(fdisk_output: str) -> int:
    """Parse unit size in bytes from fdisk output."""
    regexp = r"^Units: sectors of [0-9]+ \* [0-9]+ = ([0-9]+) bytes$"
    match = re.search(regexp, fdisk_output, re.MULTILINE)
    if not match:
        raise ValueError("can't parse partition table units")
    return int(match.group(1))

def parse_fdisk_sector_size(fdisk_output: str) -> int:
    """Parse sector size in bytes from fdisk output."""
    regexp = r"^Sector size \(logical/physical\): ([0-9]+) bytes / ([0-9]+) bytes"
    match = re.search(regexp, fdisk_output, re.MULTILINE)
    if not match:
        raise ValueError("can't parse partition table sector size")
    if match.group(1) != match.group(2):
        raise ValueError(
            "partition table logical and physical sector sizes differ: %s != %s"
            % (match.group(1), match.group(2))
        )
    return int(match.group(1))

def extract_partition_boot_files(
        partition_filename: str,
        output_kernel_filename: str,
        output_initrd_filename: str,
    ) -> None:
    """Extract the Linux kernel and initrd files from a partition image.

    Will not overwrite an existing file."""
    if not os.path.exists(partition_filename):
        raise ValueError("file not found: %s" % partition_filename)
    if os.path.exists(output_kernel_filename):
        raise ValueError("already exists: %s" % output_kernel_filename)
    if os.path.exists(output_initrd_filename):
        raise ValueError("already exists: %s" % output_initrd_filename)
    kernel = parse_symlink_target(debugfs_command(partition_filename, "stat /vmlinuz"))
    initrd = parse_symlink_target(debugfs_command(partition_filename, "stat /initrd.img"))
    debugfs_command(partition_filename, "dump %s %s" % (kernel, output_kernel_filename))
    debugfs_command(partition_filename, "dump %s %s" % (initrd, output_initrd_filename))

def debugfs_command(partition_filename: str, command: str) -> str:
    """Run a debugfs command."""
    if not os.path.exists(partition_filename):
        raise ValueError("file not found: %s" % partition_filename)
    cmd = ["/sbin/debugfs", "-f", "-", partition_filename]
    process = subprocess.Popen(
        cmd,
        universal_newlines=True,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    stdout, stderr = process.communicate(command)
    if process.returncode != 0:
        raise subprocess.CalledProcessError(process.returncode, cmd, stdout, stderr)
    return stdout

def parse_symlink_target(debugfs_output: str) -> str:
    """Extract symlink target from debugfs stat command output."""
    regexp = "^Fast link dest: (\".+\")$"
    match = re.search(regexp, debugfs_output, re.MULTILINE)
    if not match:
        raise ValueError("can't parse symlink target")
    split_to_unquote = shlex.split(match.group(1))
    if len(split_to_unquote) != 1:
        raise ValueError("can't parse symlink target")
    return split_to_unquote[0]

def iso_is_arm(iso_filename: str) -> bool:
    """Does the installation ISO image correspond to an ARM architecture?"""
    return get_debian_architecture(iso_filename) in ("arm64", "armel", "armhf")

def named_tmp(content: bytes) -> IO:
    """Create a named temporary file with given content."""
    script_base = os.path.splitext(os.path.basename(sys.argv[0]))[0]
    tmp_file = tempfile.NamedTemporaryFile(prefix=script_base + ".")
    tmp_file.write(content)
    return tmp_file

def main() -> None:
    """Simple CLI for the module."""
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("-i", dest="iso_filename", required=True, help="ISO filename")
    parser.add_argument("-u", dest="preseed_url", required=True, help="preseed URL")
    parser.add_argument("-o", dest="output_filename", required=True, help="output filename")
    parser.add_argument("-d", dest="vnc_display", help="VNC display")
    parser.add_argument("-s", dest="image_size", help="output image size", default="10G")
    args = parser.parse_args()
    create_image(args.output_filename, args.image_size)
    install(args.iso_filename, args.preseed_url, args.output_filename, args.vnc_display)
    if iso_is_arm(args.iso_filename):
        extract_boot_files(args.output_filename)

if __name__ == "__main__":
    main()
