#
# Created on Fri Feb 28 2025
#
# Created by Roland Axel Richter -- roland.richter@empa.ch
#
# Copyright (c) 2025 EMPA
#

from typing import Any

from pint.facets.plain.quantity import PlainQuantity
from spcm import units

MAX_SAMPLE_NUMBER: PlainQuantity[Any] = (
    64 * units.MS
)  # Maximum sample number for the card
