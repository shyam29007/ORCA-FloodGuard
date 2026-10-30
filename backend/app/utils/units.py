"""Unit conversion utilities for hydrological parameters."""


def cusecs_to_cumecs(cusecs: float) -> float:
    """Convert discharge from cubic feet per second (cusecs) to cubic meters per second (cumecs)."""
    return round(cusecs * 0.0283168, 2)


def cumecs_to_cusecs(cumecs: float) -> float:
    """Convert discharge from cubic meters per second to cubic feet per second."""
    return round(cumecs / 0.0283168, 2)


def feet_to_meters(feet: float) -> float:
    """Convert depth or elevation from feet to meters."""
    return round(feet * 0.3048, 2)


def meters_to_feet(meters: float) -> float:
    """Convert depth or elevation from meters to feet."""
    return round(meters / 0.3048, 2)


def inches_to_mm(inches: float) -> float:
    """Convert precipitation or water level from inches to millimeters."""
    return round(inches * 25.4, 2)


def mm_to_inches(mm: float) -> float:
    """Convert precipitation or water level from millimeters to inches."""
    return round(mm / 25.4, 2)

