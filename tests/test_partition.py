# pylint: disable=missing-docstring
import os.path
import pytest
from preseed_install import parse_fdisk_units, parse_fdisk_sector_size, parse_symlink_target


def test_fdisk_units() -> None:
    assert parse_fdisk_units(load_test_data("valid_fdisk_output.txt")) == 512


def test_fdisk_units_exception() -> None:
    with pytest.raises(ValueError):
        parse_fdisk_units("")


def test_fdisk_sector_size() -> None:
    assert parse_fdisk_sector_size(load_test_data("valid_fdisk_output.txt")) == 512


def test_fdisk_sector_size_exception() -> None:
    with pytest.raises(ValueError):
        parse_fdisk_sector_size("")


def test_fdisk_sector_size_mismatch_exception() -> None:
    with pytest.raises(
        ValueError,
        match="partition table logical and physical sector sizes differ: 512 != 1024"
    ):
        parse_fdisk_sector_size(load_test_data("invalid_sector_size_fdisk_output.txt"))


def test_symlink_target() -> None:
    target = parse_symlink_target(load_test_data("debugfs_symlink_output.txt"))
    assert target == "boot/vmlinuz-4.19.0-16-amd64"


def test_symlink_target_exception() -> None:
    with pytest.raises(ValueError):
        parse_symlink_target("")


def load_test_data(name: str) -> str:
    with open(os.path.join("tests", name), "r", encoding="ascii") as file:
        return file.read()
