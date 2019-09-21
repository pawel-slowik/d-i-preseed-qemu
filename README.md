A [QEMU][qemu] wrapper for performing automated Debian installations in QEMU
virtual machines.

Automation is based on [Debian installer preseeding][d-i-preseed].

Supports the i386, amd64 and arm64 architectures.

[qemu]: https://www.qemu.org/
[d-i-preseed]: https://wiki.debian.org/DebianInstaller/Preseed

## Installation

Clone this repository and run the script from there.

## Requirements

- Python 3.x
- QEMU
- `isoinfo`, `dd`, `fdisk`, `sfdisk`, `mkfs.ext2`, `debugfs`

Install all the requirements on Debian 10 / buster with:

	apt-get install python3 qemu-kvm qemu-system-arm qemu-utils genisoimage coreutils fdisk e2fsprogs

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

## ARM notes

The arm64 installer randomly fails at one of the first steps, e.g. at _Detect
and mount CD-ROM_ or at _Access software for blind person using a braille
display_. I haven't found a solution yet, for now you'll need to keep retrying.

I couldn't find any way to install a working bootloader for ARM from the Debian
installer. Therefore this script will attempt to extract the kernel and initrd
files after the installation is complete, so that you can use them to boot the
VM with QEMU `-kernel` and `-initrd` parameters. The extracted files are saved
with `.kernel` and `.initrd` extensions. E.g. for `-o debian-10-arm64.qcow2`
the extracted files are named `debian-10-arm64.kernel` and
`debian-10-arm64.initrd`.

Extracting the kernel and initrd files currently only works for a DOS partition
table and an ext2 / ext3 / ext4 filesystem.

## Acknowledgements

- [Installing Debian on QEMU’s 32-bit ARM “virt” board](https://translatedcode.wordpress.com/2016/11/03/installing-debian-on-qemus-32-bit-arm-virt-board/)
- [Installing Debian on QEMU’s 64-bit ARM “virt” board](https://translatedcode.wordpress.com/2017/07/24/installing-debian-on-qemus-64-bit-arm-virt-board/)
- [Run Debian iso on QEMU ARMv8](https://kennedy-han.github.io/2015/06/16/QEMU-debian-ARMv8.html)
