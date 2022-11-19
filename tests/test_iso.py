# pylint: disable=missing-docstring
import pytest
from preseed_install import get_debian_version, get_debian_architecture, iso_is_arm
from preseed_install import iso_get_boot_filenames, iso_extract_file


def test_version() -> None:
    assert get_debian_version("debian-11.3.0-amd64-netinst.iso") == 11


def test_version_exception() -> None:
    with pytest.raises(
        ValueError,
        match="can't read Debian version: ubuntu-22.10-desktop-amd64.iso"
    ):
        get_debian_version("ubuntu-22.10-desktop-amd64.iso")


def test_architecture() -> None:
    assert get_debian_architecture("debian-10.1.0-armhf-netinst.iso") == "armhf"


def test_architecture_exception() -> None:
    with pytest.raises(
        ValueError,
        match="can't read Debian architecture: ubuntu-22.10-desktop-amd64.iso"
    ):
        get_debian_architecture("ubuntu-22.10-desktop-amd64.iso")


def test_is_arm() -> None:
    assert iso_is_arm("debian-10.1.0-armhf-netinst.iso")


def test_is_not_arm() -> None:
    assert not iso_is_arm("debian-10.10.0-amd64-netinst.iso")


@pytest.mark.parametrize(
    "iso_filename",
    [
        "debian-9.13.0-i386-netinst.iso",
        "debian-9.13.0-amd64-netinst.iso",
        "debian-9.13.0-arm64-netinst.iso",
        "debian-9.13.0-armhf-netinst.iso",
        "debian-10.13.0-i386-netinst.iso",
        "debian-10.13.0-arm64-netinst.iso",
        "debian-10.10.0-amd64-netinst.iso",
        "debian-10.1.0-armhf-netinst.iso",
        "debian-11.5.0-amd64-netinst.iso",
    ]
)
def test_boot_filenames(iso_filename: str) -> None:
    kernel, initrd = iso_get_boot_filenames(iso_filename)
    assert isinstance(kernel, str)
    assert isinstance(initrd, str)


def test_boot_filenames_unknown_image() -> None:
    with pytest.raises(
        ValueError,
        match="unsupported Debian version or architecture: 11, i386"
    ):
        iso_get_boot_filenames("debian-11.5.0-i386-netinst.iso")


def test_extract() -> None:
    assert iso_extract_file("tests/test.iso", "/foo.txt") == b"FOO\n"


def test_extract_exception() -> None:
    with pytest.raises(
        ValueError,
        match="failed to extract file: /baz.txt from ISO: tests/test.iso"
    ):
        iso_extract_file("tests/test.iso", "/baz.txt")
