"""Tests del value object RomMeasurement."""
from domain.value_objects.rom_measurement import RomMeasurement

def test_rom_percentage():
    rom = RomMeasurement(achieved_degrees=85.0, expected_degrees=100.0)
    assert rom.percentage == 85.0

def test_rom_percentage_zero_expected():
    rom = RomMeasurement(achieved_degrees=50.0, expected_degrees=0.0)
    assert rom.percentage == 0.0
