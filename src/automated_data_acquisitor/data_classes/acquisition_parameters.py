#
# Created on Sun May 18 2025
#
# Created by Roland Axel Richter -- roland.richter@empa.ch
#
# Copyright (c) 2025 EMPA
#
"""Automated Data Acquisitor

This module contains the AcqParams class, which defines the acquisition parameters for the
Automated Data Acquisitor.

The AcqParams class includes the following attributes:

- card_identifiers: List of device names for the cards.
- sync_identifier: Identifier for the Star-Hub synchronization.
- channels_card_0: Channels to enable on card 0.
- channels_card_1: Channels to enable on card 1.
- channel_amp_level: Amplification level for the channels in volts.
- card_timeout: Timeout for card operations in seconds.
- trigger_level: Trigger threshold level in volts.
- trigger_channel_no: Trigger channel number.
- target_file_name: Name of the target file for saving data.
- sample_rate: Sampling rate in MHz.
- data_format: Data format for saving data (CSV or PQT).
- acquisition_duration: Duration of data acquisition in seconds.
- post_acquisition_duration: Duration after acquisition in seconds.
- pre_acquisition_duration: Duration before acquisition in seconds.
"""
from enum import Enum

import serde
from serde.json import to_json

from automated_data_acquisitor.data_classes.file_format import FileFormat


class InputImpedance(Enum):
    """Enum representing the input impedance of the acquisition system.

    Attributes:
        LOW_IMPEDANCE: Low impedance setting (50 Ohm).
        HIGH_IMPEDANCE: High impedance setting (1 MOhm).
    """

    LOW_IMPEDANCE = "50_ohm"
    HIGH_IMPEDANCE = "1_Mohm"


class SensorType(Enum):
    """Enum representing the type of sensor used in data acquisition.

    Attributes:
        AIRBORNE: Sensor mounted on an airborne platform.
        STRUCTURE: Sensor mounted on the plate.
        SIGNAL_CHANNEL: Channel used for machine communication.
    """

    AIRBORNE = "airborne"
    STRUCTURE = "structure"
    SIGNAL_CHANNEL = "signal_channel"


class SensorCoupling(Enum):
    """Enum representing the coupling type of the sensor.

    Attributes:
        AC: Alternating current coupling.
        DC: Direct current coupling.
    """

    AC = "ac"
    DC = "dc"


@serde.serde
class SensorParams:
    """Class representing parameters for a sensor used in data acquisition.

    Attributes:
        sensor_type (SensorType): Type of the sensor (airborne or structure).
        sensor_placement (str): Placement of the sensor (e.g., "top", "bottom").
        sensor_card (int): Card number where the sensor is connected.
        sensor_channel (int): Channel number on the card for the sensor.
        sensor_input_impedance (InputImpedance): Input impedance of the sensor.
            Default is HIGH_IMPEDANCE (1 MOhm).
        sensor_amp_level (float): Amplification level for the sensor in volts.
        sensor_coupling (SensorCoupling): Coupling type of the sensor (AC or DC).
    """

    sensor_type: SensorType = SensorType.AIRBORNE
    sensor_placement: str = "top"
    sensor_card: int = 0
    sensor_channel: int = 0
    sensor_input_impedance: InputImpedance = InputImpedance.HIGH_IMPEDANCE
    sensor_amp_level: float = 10.0
    sensor_coupling: SensorCoupling = SensorCoupling.DC

    def __str__(self) -> str:
        # Pretty-print using JSON serialization
        return to_json(self, indent=2)


@serde.serde
class AcqParams:
    """Class representing acquisition parameters for the Automated Data Acquisitor.

    Attributes:
        card_identifiers (list[str]): List of device names for the cards.
        sync_identifier (str): Identifier for the Star-Hub synchronization.
        sensors_card_0 (list[SensorParams]): List of sensor parameters for card 0.
        sensors_card_1 (list[SensorParams]): List of sensor parameters for card 1.
        card_timeout (float): Timeout for card operations in seconds.
        trigger_level (float): Trigger threshold level in volts.
        trigger_channel_no (int): Trigger channel number.
        emission_on_channel_no (int): Channel number for emission.
        target_file_name (str): Name of the target file for saving data.
        sample_rate (float): Sampling rate in MHz.
        data_format (FileFormat): Data format for saving data (CSV or PQT).
        acquisition_duration (float): Duration of data acquisition in seconds.
        post_acquisition_duration (float): Duration after acquisition in seconds.
        pre_acquisition_duration (float): Duration before acquisition in seconds.
        sensitivity_threshold (float): Sensitivity threshold for data processing.
        cur_version (int): Current version of the acquisition parameters.
        with_crop (bool): Whether to apply cropping to the data.
        with_plot (bool): Whether to generate plots from the data.
        with_channel_check (bool): Whether to perform a channel check after acquisition.
    """

    card_identifiers: list[str] = serde.field(
        default_factory=["/dev/spcm0", "/dev/spcm1"]
    )
    sync_identifier: str = "sync0"
    sensors_card_0: list[SensorParams] = serde.field(
        default_factory=[SensorParams(sensor_card=0, sensor_channel=0)]
    )
    sensors_card_1: list[SensorParams] = serde.field(
        default_factory=[SensorParams(sensor_card=1, sensor_channel=0)]
    )
    card_timeout: float = 5.0
    trigger_level: float = 0.5
    trigger_channel_no: int = 0
    emission_on_channel_no: int = 1
    target_file_name: str = "data.pqt"
    sample_rate: float = 2.0
    data_format: FileFormat = FileFormat.PQT
    acquisition_duration: float = 10.0
    post_acquisition_duration: float = 2.0
    pre_acquisition_duration: float = 2.0
    sensitivity_threshold: float = 2.0
    cur_version: int = 2
    with_crop: bool = True
    with_plot: bool = True
    with_channel_check: bool = False
