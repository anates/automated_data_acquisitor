#
# Created on Sun May 18 2025
#
# Created by Roland Axel Richter -- roland.richter@empa.ch
#
# Copyright (c) 2025 EMPA
#

"""Automated Data Acquisitor

This module contains the FileFormat enum, which defines the available data formats for the
Automated Data Acquisitor.

The FileFormat enum includes the following formats:

- CSV: Comma-separated values format
- PQT: Parquet format
"""
from __future__ import annotations

from enum import Enum


class FileFormat(Enum):
    """
    Enum for data format options.
    """

    CSV = "CSV"
    PQT = "PQT"

    @classmethod
    def from_str(cls, value: str) -> "FileFormat":
        """
        Create a FileFormat enum member from a string value.

        Args:
            value (str): The string representation of the enum value.
        Returns:
            FileFormat: The corresponding FileFormat enum member.
        Raises:
            ValueError: If the value does not correspond to any enum member.
        """
        for member in cls:
            if member.value == value:
                return member
        raise ValueError(f"{value} is not a valid FileFormat")
