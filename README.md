A [QEMU][qemu] wrapper for performing automated Debian installations in QEMU
virtual machines.

Automation is based on [Debian installer preseeding][d-i-preseed].

[qemu]: https://www.qemu.org/
[d-i-preseed]: https://wiki.debian.org/DebianInstaller/Preseed

## Installation

Clone this repository and run the script from there.

## Requirements

- Python 3.x
- QEMU (`qemu-system-x86` and `qemu-utils` Debian packages)
- `isoinfo` (`genisoimage` Debian package)

## Usage

	~/path/preseed_install.py -i debian-10.0.0-amd64-netinst.iso -u http://server/preseed.cfg -o debian-10.qcow2

	~/path/preseed_install.py --help

By default the installation runs without any keyboard / display IO (since it's
meant to be fully automated). If you want to see the installer working use the
`-d VNC_DISPLAY` option, e.g. `-d :1`. You can then connect to the VM with a
VNC client:

	vncviewer :1

You can use the Python built in HTTP server for serving preseed configuration
files:

	python3 -m http.server --bind 10.0.10.1 8080

and then refer to a file with `-u http://10.0.10.1:8080/preseed.cfg`.

## Limitations

Supports only the i386 and x86-64 architectures.
