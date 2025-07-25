#
# Created on Sun May 18 2025
#
# Created by Roland Axel Richter -- roland.richter@empa.ch
#
# Copyright (c) 2025 EMPA
#

"""Automated Data Acquisitor

This module contains helper functions for the Automated Data Acquisitor.

The helper functions include:

- detect_dissimilar_channels: Detects dissimilar channels in the acquired data.
- pretty_print_serde_json: Pretty prints a JSON string and saves it to a file.
- save_to_file: Saves the acquired data to a file in the specified format (CSV or Parquet).
- crop_data: Crops the acquired data based on trigger crossings and acquisition parameters.
- setup_logger: Sets up a logger that logs to both the console and a file.
- parse_args: Parses command line arguments for the data acquisition script.
"""
from __future__ import annotations

import argparse
import json
import logging
import pathlib
import re
import sys
from datetime import datetime
from typing import Any

import matplotlib

matplotlib.use("Agg")  # Use a non-interactive backend for matplotlib to avoid GUI
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import serde.json as sjson
from scipy.spatial.distance import pdist, squareform
from scipy.stats import zscore
from serde.json import from_dict

from automated_data_acquisitor.data_classes.acquisition_parameters import (
    AcqParams,
    SensorParams,
)
from automated_data_acquisitor.data_classes.file_format import FileFormat


def detect_dissimilar_channels(
    data: np.ndarray, data_acq_params: AcqParams
) -> np.ndarray:
    """
    Detects dissimilar channels in the given data using z-score normalization and
    cosine distance.

    Args:
        data (np.ndarray): 2D array of shape (num_channels, num_samples) containing
        the data to analyze.
        threshold (float): Z-score threshold for detecting dissimilar channels.
        Default is 2.0.
    Returns:
        np.ndarray: 1D array of shape (num_channels,) containing binary values (0 or 1)
        indicating whether each channel is dissimilar (1) or not (0).
    """
    data = data.T
    data_norm: np.ndarray = zscore(data, axis=1)
    dists: np.ndarray = squareform(pdist(data_norm, metric="cosine"))
    avg_dists: np.ndarray = np.mean(dists, axis=1)
    zscores: np.ndarray = zscore(avg_dists)
    outliers: np.ndarray = np.abs(zscores) > data_acq_params.sensitivity_threshold
    outliers = outliers.astype(int)
    outliers[data_acq_params.trigger_channel_no] = -1
    outliers[data_acq_params.emission_on_channel_no] = -1
    return outliers


def pretty_print_serde_json(json_string: str, target_file_name: pathlib.Path) -> None:
    """
    Pretty prints a JSON string and saves it to a file.

    Args:
        json_string (str): The JSON string to be pretty printed.
        target_file_name (pathlib.Path): The file path where the pretty-printed JSON
        will be saved.
    """
    with open(
        target_file_name,
        "w",
        encoding="utf-8",
    ) as json_out:
        json_out.write(json_string)

    tmp_json_dict: dict[str, Any] = {}
    with open(
        target_file_name,
        "r",
        encoding="utf-8",
    ) as json_in:
        tmp_json_dict = json.load(json_in)

    with open(
        target_file_name,
        "w",
        encoding="utf-8",
    ) as pretty_json_out:
        pretty_json_out.write(json.dumps(tmp_json_dict, indent=4, sort_keys=True))


def plot_data(data: np.ndarray, data_acq_params: AcqParams) -> None:
    """
    Plots the acquired data for each channel.

    Args:
        data (np.ndarray): The acquired data to be plotted.
        data_acq_params (AcqParams): The acquisition parameters containing the sample
        rate and target file name.
    Returns:
        None
    """
    if not data_acq_params.with_plot:
        return
    fig, ax = plt.subplots(ncols=1, nrows=data.T.shape[0], figsize=(32, 20))
    time_vec: np.ndarray = np.arange(0, data.T.shape[1]) * (
        1 / (data_acq_params.sample_rate * 1e6)  # Convert to seconds
    )
    for i in range(data.T.shape[0]):
        sensor_card: list[SensorParams] = (
            data_acq_params.sensors_card_0
            if i < len(data_acq_params.sensors_card_0)
            else data_acq_params.sensors_card_1
        )
        card_entry_no: int = (
            i
            if i < len(data_acq_params.sensors_card_0)
            else i - len(data_acq_params.sensors_card_0)
        )
        axis_title: str = (
            f"Channel {i} - {sensor_card[card_entry_no].sensor_type} - "
            f"{sensor_card[card_entry_no].sensor_placement}"
        )
        ax[i].plot(time_vec[::5], data.T[i][::5])
        ax[i].set_title(axis_title)
        ax[i].set_xlabel("Time (s)")
        ax[i].set_ylabel("Amplitude [V]")
        ax[i].grid()
        ax[i].set_xlim(
            0,
            time_vec[::5][-1],
        )
    fig.tight_layout()
    fig.savefig(
        f"graphs_{datetime.now().strftime('%d%m%Y_%H%M%S')}.png",
        bbox_inches="tight",
        dpi=150,
    )
    fig.clear()
    plt.close(fig)


def save_to_file(data: np.ndarray, data_acq_params: AcqParams) -> None:
    """
    Saves the acquired data to a file in the specified format (CSV or Parquet).

    Args:
        data (np.ndarray): The acquired data to be saved.
        data_acq_params (AcqParams): The acquisition parameters containing the file
        format and target file name.
    Returns:
        None
    Raises:
        ValueError: If the specified file format is not supported.
    """
    timestamp: str = datetime.now().strftime("%d%m%Y_%H%M%S")
    pretty_print_serde_json(
        json_string=sjson.to_json(data_acq_params),
        target_file_name=pathlib.Path(f"params_{timestamp}.json"),
    )
    if data_acq_params.data_format == FileFormat.CSV:
        np.savetxt(
            pathlib.Path(data_acq_params.target_file_name).stem + f"_{timestamp}.csv",
            data,
            delimiter=",",
        )
    elif data_acq_params.data_format == FileFormat.PQT:
        time_vec: np.ndarray = np.arange(0, data.T.shape[1]) * (
            1 / (data_acq_params.sample_rate * 1e6)  # Convert to seconds
        )
        column_names: list[str] = [f"data_channel_{i}" for i in range(data.T.shape[0])]
        df = pd.DataFrame(data, columns=column_names)
        for i in range(data.T.shape[0]):
            df[f"time_channel_{i}"] = time_vec
        df.to_parquet(
            pathlib.Path(data_acq_params.target_file_name).stem + f"_{timestamp}.pqt"
        )
    else:
        raise ValueError(f"Unsupported file format: {data_acq_params.data_format}")


def crop_data(
    data: np.ndarray,
    data_acq_params: AcqParams,
) -> np.ndarray:
    """
    Crops the data based on the trigger channel and acquisition parameters.

    Args:
        data (np.ndarray): The data to be cropped.
        data_acq_params (AcqParams): The acquisition parameters.
    Returns:
        np.ndarray: The cropped data.
    Raises:
        ValueError: If no trigger crossings are found in the data.
    """
    if not data_acq_params.with_crop:
        return data
    channel_data: np.ndarray = data[:, data_acq_params.trigger_channel_no]
    crossings = np.where(
        np.diff((channel_data > data_acq_params.trigger_level).astype(int)) != 0
    )[0]
    # plt.plot(channel_data)
    # plt.show()
    if crossings.size == 0:
        first_cross = last_cross = None
    else:
        first_cross: None | int = crossings[0]
        last_cross: None | int = crossings[-1]
    if first_cross is None or last_cross is None:
        raise ValueError(
            "No trigger crossings found in the data. Please check the trigger level."
        )
    pre_trigger_samples: int = int(
        data_acq_params.pre_acquisition_duration * data_acq_params.sample_rate
    )
    post_trigger_samples: int = int(
        data_acq_params.post_acquisition_duration * data_acq_params.sample_rate
    )
    # Crop the data based on the acquisition parameters
    start_index: int = (
        first_cross - pre_trigger_samples if first_cross > pre_trigger_samples else 0
    )
    end_index: int = (
        last_cross + post_trigger_samples
        if last_cross + post_trigger_samples < data.shape[1]
        else data.shape[1]
    )
    return data[start_index:end_index, :]


def setup_logger(
    log_file: pathlib.Path = pathlib.Path("daq_log.log"),
) -> logging.Logger:
    """
    Sets up a logger that logs to both the console and a file.

    Args:
        log_file (str): Path to the log file.

    Returns:
        logging.Logger: Configured logger instance.
    """
    logger: logging.Logger = logging.getLogger("my_logger")
    logger.setLevel(logging.DEBUG)

    if not logger.handlers:  # Avoid duplicate handlers
        # File handler
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        file_handler.setFormatter(file_formatter)

        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter("%(levelname)s - %(message)s")
        console_handler.setFormatter(console_formatter)

        # Add handlers
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

    return logger


def parse_args(process_logger: logging.Logger) -> AcqParams:
    """
    Parse command line arguments for the data acquisition script.
    This function is a placeholder for future command line argument parsing.

    Returns:
        dict[str, Any]: A dictionary containing parsed command line arguments.
    """
    parser = argparse.ArgumentParser(
        prog="Automated_data_acquisition.py",
        description="Automated Data Acquisition Script",
    )
    parser.add_argument(
        "--config",
        type=str,
        help="Path to the JSON configuration file",
        default=None,
    )
    args: argparse.Namespace = parser.parse_args()

    # Default parameters
    default_params: dict[str, Any] = {
        "data_format": "PQT",
        "card_identifiers": ["/dev/spcm0", "/dev/spcm1"],
        "sync_identifier": "sync0",
        "channel_amp_level": 10.0,
        "card_timeout": 25.0,
        "trigger_level": 2.0,
        "trigger_channel_no": 0,  # Channel number for trigger
        "emission_on_channel_no": 1,  # Channel number for emission on
        "sample_rate": 2.0,
        "sensors_card_0": [
            SensorParams(sensor_card=0, sensor_channel=0),
            SensorParams(sensor_card=0, sensor_channel=1),
        ],
        "sensors_card_1": [
            SensorParams(sensor_card=1, sensor_channel=0),
            SensorParams(sensor_card=1, sensor_channel=1),
        ],
        "acquisition_duration": 20.0,
        "pre_acquisition_duration": 1.0,
        "post_acquisition_duration": 1.0,
        "target_file_name": "data.pqt",
        "sensitivity_threshold": 1.2,
        "with_crop": "True",
        "with_plot": "True",
        "with_channel_check": False,  # Disables channel check by default
        # Versioning for future compatibility
        "cur_version": 1,
    }
    json_dict: dict[str, Any] = {}
    # Load parameters from JSON file if provided
    if args.config and pathlib.Path(args.config).is_file():
        process_logger.info(f"Reading config from {args.config}")
        with open(args.config, "r", encoding="utf-8") as f:
            json_dict = json.load(f)
        for key, value in json_dict.items():
            if key in default_params:
                if re.fullmatch(r"sensors_card_(\d+)", key):
                    for entry in value:
                        if not isinstance(entry, dict):
                            process_logger.warning(
                                f"Invalid sensor entry in {key}: {entry}. Expected a dictionary."
                            )
                            continue
                        # Convert sensor parameters to SensorParams objects
                    sensors: list[SensorParams] = [
                        from_dict(SensorParams, sensor) for sensor in value
                    ]
                    default_params[key] = sensors
                else:
                    default_params[key] = value
            else:
                process_logger.warning(
                    f"Warning: {key} not found in default parameters. Ignoring."
                )
        process_logger.info(f"Loaded parameters from {args.config}: {json_dict}")
        for entry in default_params.items():
            if isinstance(entry[1], list):
                process_logger.info(f"Parameter: {entry[0]} = {entry[1][0]}")
                for entry in entry[1][1:]:
                    process_logger.info(f"\t\t\t\t{entry}")
            else:
                process_logger.info(f"Parameter: {entry[0]} = {entry[1]}")
    else:
        process_logger.warning(
            "No valid JSON configuration file provided. Using default parameters."
        )
        for entry in default_params.items():
            process_logger.info(f"Default parameter: {entry[0]} = {entry[1]}")
    if default_params["cur_version"] < 2:
        raise ValueError(
            "The current version of the acquisition parameters is outdated. "
            "Please update to the latest version."
        )
    local_acq_params: AcqParams = AcqParams(
        card_identifiers=default_params["card_identifiers"],
        sync_identifier=default_params["sync_identifier"],
        sensors_card_0=default_params["sensors_card_0"],
        sensors_card_1=default_params["sensors_card_1"],
        card_timeout=default_params["card_timeout"],
        trigger_level=default_params["trigger_level"],
        trigger_channel_no=default_params["trigger_channel_no"],
        emission_on_channel_no=default_params["emission_on_channel_no"],
        sample_rate=default_params["sample_rate"],
        data_format=(
            FileFormat.CSV if default_params["data_format"] == "CSV" else FileFormat.PQT
        ),
        acquisition_duration=default_params["acquisition_duration"],
        pre_acquisition_duration=default_params["pre_acquisition_duration"],
        sensitivity_threshold=default_params["sensitivity_threshold"],
        with_crop=(
            True
            if re.match("true", str(default_params["with_crop"]), re.IGNORECASE)
            else False
        ),
        with_plot=(
            True
            if re.match("true", str(default_params["with_plot"]), re.IGNORECASE)
            else False
        ),
        with_channel_check=(
            True
            if re.match(
                "true", str(default_params["with_channel_check"]), re.IGNORECASE
            )
            else False
        ),
    )
    return local_acq_params
