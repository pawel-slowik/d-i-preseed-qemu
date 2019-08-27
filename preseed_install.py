#!/usr/bin/env python3
"""A QEMU wrapper for performing automated Debian installations in QEMU virtual machines."""

import sys
import os.path
import subprocess
import re
import tempfile
from typing import Tuple, IO, Optional

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
        raise ValueError("unsupported architecture: %s" % iso_filename)

    iso_kernel, iso_initrd = iso_find_bootfiles(iso_filename)
    tmp_kernel = named_tmp(iso_extract_file(iso_filename, iso_kernel))
    tmp_initrd = named_tmp(iso_extract_file(iso_filename, iso_initrd))
    command = [
        get_command_for_arch(iso_filename),
        "-enable-kvm", "-accel", "kvm",
        "-cpu", "max", "-m", "1G",
        "-net", "nic", "-net", "user",
        "-drive", "file=%s" % output_filename,
        "-cdrom", iso_filename,
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
    subprocess.run(command, check=True)

def iso_find_bootfiles(iso_filename: str) -> Tuple[str, str]:
    """Find the Debian installer kernel and initrd in an ISO image. Return filenames."""
    kernel_regexp = r"^/install([^/]*)/vmlinuz$"
    initrd_regexp = r"^/install([^/]*)/initrd\.gz$"
    command = ["isoinfo", "-f", "-R", "-i", iso_filename]
    process = subprocess.run(command, capture_output=True, check=True, text=True)
    kernel_lines_found = []
    initrd_lines_found = []
    arch_suffixes_found = set()
    for line in process.stdout.split("\n"):
        match = re.search(kernel_regexp, line)
        if match:
            kernel_lines_found.append(line)
            arch_suffixes_found.add(match.group(1))
            continue
        match = re.search(initrd_regexp, line)
        if match:
            initrd_lines_found.append(line)
            arch_suffixes_found.add(match.group(1))
            continue
    if not kernel_lines_found:
        raise ValueError("kernel not found: %s, %s" % (iso_filename, kernel_regexp))
    if not initrd_lines_found:
        raise ValueError("initrd not found: %s, %s" % (iso_filename, initrd_regexp))
    if len(kernel_lines_found) > 1:
        raise ValueError("multiple kernels found: %s, %s" % (iso_filename, kernel_lines_found))
    if len(initrd_lines_found) > 1:
        raise ValueError("multiple initrds found: %s, %s" % (iso_filename, initrd_lines_found))
    if len(arch_suffixes_found) != 1:
        raise ValueError("mixed architectures: %s, %s" % (iso_filename, arch_suffixes_found))
    return kernel_lines_found[0], initrd_lines_found[0]

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

if __name__ == "__main__":
    main()
