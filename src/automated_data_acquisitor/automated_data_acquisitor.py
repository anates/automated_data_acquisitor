#
# Created on Fri Feb 28 2025
#
# Created by Roland Axel Richter -- roland.richter@empa.ch
#
# Copyright (c) 2025 EMPA
#
"""Automated Data Acquisitor

This module contains the main function for the Automated Data Acquisitor.
The main function initializes the acquisition parameters, sets up the cards,
and starts the acquisition process.

The acquisition parameters are defined in the AcqParams class, which includes
the following attributes:

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
import logging
import operator
import pathlib
import queue
import threading
from functools import reduce

import numpy as np
import spcm
from spcm import units

from automated_data_acquisitor import MAX_SAMPLE_NUMBER
from automated_data_acquisitor.card_classes.card_thread import CardThread
from automated_data_acquisitor.data_classes.acquisition_parameters import (
    AcqParams,
    InputImpedance,
    SensorCoupling,
)
from automated_data_acquisitor.helper_functions.helper_functions import (
    crop_data,
    detect_dissimilar_channels,
    parse_args,
    plot_data,
    save_to_file,
    setup_logger,
)


def run_acquisition(acq_params: AcqParams, process_logger: logging.Logger) -> None:
    """
    Main function to run the data acquisition process

    It initializes the Spectrum cards, configures them, and starts the acquisition process.
    The acquired data is saved to files determined by acq_params.

    Args:
        acq_params (AcqParams): The acquisition parameters.
    Returns:
        None
    Raises:
        None
    Notes:
        - This function is the entry point for the data acquisition process.
        - It handles card initialization, configuration, and data retrieval.
    """

    # List your card device names here
    card_identifiers: list[str] = acq_params.card_identifiers
    sync_identifier: str = acq_params.sync_identifier  # Star-Hub sync identifier

    exc_queue: queue.Queue = queue.Queue()

    # Open all cards in one stack so that Star-Hub synchronization can be configured
    # Keep the stack open for the entire run (hence 'with ... as stack:')
    with spcm.CardStack(
        card_identifiers=card_identifiers, sync_identifier=sync_identifier
    ) as stack:

        try:
            channels = spcm.Channels(
                stack=stack,
                stack_enable=[
                    reduce(
                        operator.or_,
                        (
                            getattr(spcm, f"CHANNEL{sensor_data.sensor_channel}")
                            for sensor_data in acq_params.sensors_card_0
                        ),
                        spcm.CHANNEL0,
                    ),
                    reduce(
                        operator.or_,
                        (
                            getattr(spcm, f"CHANNEL{sensor_data.sensor_channel}")
                            for sensor_data in acq_params.sensors_card_1
                        ),
                        spcm.CHANNEL0,
                    ),
                ],
            )
            for channel in channels:
                # Set the channel amplification level
                cur_channel_card: int = channel.card.sn()
                cur_channel_no: int = channel.index
                channel_found: bool = False
                for card_entry in [
                    acq_params.sensors_card_0,
                    acq_params.sensors_card_1,
                ]:
                    for entry in card_entry:
                        if (
                            entry.sensor_card == cur_channel_card
                            and entry.sensor_channel == cur_channel_no
                        ):
                            channel.amp(entry.sensor_amp_level * units.V)
                            channel.coupling(
                                spcm.COUPLING_DC
                                if entry.sensor_coupling == SensorCoupling.DC
                                else spcm.COUPLING_AC
                            )
                            channel.termination(
                                int(
                                    entry.sensor_input_impedance
                                    == InputImpedance.LOW_IMPEDANCE
                                )
                            )
                            process_logger.info(
                                f"Configuring channel {cur_channel_no} on card {cur_channel_card} with "
                                f"amp level {entry.sensor_amp_level} V, coupling "
                                f"{entry.sensor_coupling}, "
                                f"termination {entry.sensor_input_impedance}."
                            )
                            channel_found = True
                            break
                if not channel_found:
                    process_logger.error(
                        f"Channel {cur_channel_no} on card {cur_channel_card} not found in "
                        "acquisition parameters."
                    )
                    raise ValueError(
                        f"Channel {cur_channel_no} on card {cur_channel_card} not found in acquisition "
                        "parameters."
                    )
        except Exception as e:
            process_logger.error(f"Error configuring channels: {e}")
            raise e

        process_logger.info(
            f"Available channels: {[(channel, channel.card) for channel in channels]}"
        )
        process_logger.info(f"Cards: {[card for card in stack.cards]}")

        # Prepare a Gated object for each card
        # We'll store them along with the target file name and pass them to our threads
        gated_transfers: list[spcm.DataTransfer] = []

        try:
            for i, card in enumerate(stack.cards):
                # Make sure the card is an A/D digitizer
                if card.function_type() != spcm.SPCM_TYPE_AI:
                    process_logger.error(
                        f"This example is for A/D cards only. Card {i} is not supported."
                    )
                    raise spcm.SpcmException(
                        f"This example is for A/D cards only. Card {i} is not supported."
                    )

                process_logger.info(f"Configuring card {i}: {card}")
                # -----------------------------
                # Card/Trigger/Clock setup
                # -----------------------------
                card.card_mode(spcm.SPC_REC_STD_SINGLE)  # FIFO Gated mode
                if acq_params.card_timeout > 0:
                    acq_total_duration: float = (
                        acq_params.pre_acquisition_duration
                        + acq_params.acquisition_duration
                        + acq_params.post_acquisition_duration
                    )
                    if acq_total_duration >= acq_params.card_timeout:
                        warnings_str: str = (
                            f"Total acquisition time ({acq_total_duration}) exceeds"
                        )
                        warnings_str += (
                            f" timeout duration ({acq_params.card_timeout} s)."
                        )
                        warnings_str += " Adjusting timeout accordingly from "
                        warnings_str += f"{acq_params.card_timeout}"
                        warnings_str += f" to {acq_total_duration + 5} s."
                        # warnings.warn(warnings_str)
                        process_logger.warning(warnings_str)
                        card.timeout((acq_total_duration + 5) * units.s)
                    else:
                        card.timeout(
                            acq_params.card_timeout * units.s
                        )  # 5-second timeout

                process_logger.info(f"Card {i} features: {card.features()}")
                starhub_support: int = card.features() & (
                    spcm.SPCM_FEAT_STARHUB5 | spcm.SPCM_FEAT_STARHUB16
                )
                process_logger.info(f"Card {i} supports Star-Hub: {starhub_support}")

                # Trigger setup
                trigger = spcm.Trigger(card)
                trigger.or_mask(spcm.SPC_TMASK_EXT0)
                trigger.and_mask(spcm.SPC_TMASK_NONE)
                trigger.ext0_mode(spcm.SPC_TM_POS)
                trigger.ext0_level0(acq_params.trigger_level * units.V)

                # Clock setup
                clock = spcm.Clock(card)
                clock.mode(spcm.SPC_CM_INTPLL)
                sample_rate: int = clock.sample_rate(acq_params.sample_rate * units.MHz)
                process_logger.info(f"Card {i} sample rate: {sample_rate / 1e6} MHz")

                # -----------------------------
                # Memory / gating config
                # -----------------------------
                data_transfer: spcm.DataTransfer = spcm.DataTransfer(card)

                # Expected number of samples
                num_samples: int = int(
                    int(
                        acq_params.pre_acquisition_duration
                        + acq_params.acquisition_duration
                        + acq_params.post_acquisition_duration
                    )
                    * acq_params.sample_rate
                    * 1e6
                    * units.S
                )
                if num_samples > MAX_SAMPLE_NUMBER.to_base_units().magnitude:
                    warnings_str = "Requested number of samples "
                    warnings_str += f"({int(num_samples / 1e6) * units.MS})"
                    warnings_str += " exceeds maximum "
                    warnings_str += (
                        f"({int(MAX_SAMPLE_NUMBER.to_base_units() / 1e6) * units.MS})."
                    )
                    process_logger.warning(warnings_str)
                    num_samples = MAX_SAMPLE_NUMBER.to_base_units().magnitude
                    acq_duration: (
                        float
                    ) = MAX_SAMPLE_NUMBER.to_base_units().magnitude / (
                        acq_params.sample_rate * 1e6
                    )
                    post_acq_duration: float = (
                        acq_duration - acq_params.pre_acquisition_duration
                    )
                    warnings_str = f"Adjusted acquisition time to {acq_duration} s/"
                    warnings_str += f"{int(num_samples / 1e6) * units.MS}."
                    warnings_str += (
                        f" Adjusted post-trigger time to {post_acq_duration} s."
                    )
                    process_logger.warning(warnings_str)
                else:
                    acq_duration = (
                        acq_params.pre_acquisition_duration
                        + acq_params.acquisition_duration
                        + acq_params.post_acquisition_duration
                    )
                    post_acq_duration = (
                        acq_params.acquisition_duration
                        + acq_params.post_acquisition_duration
                    )
                process_logger.info(
                    f"Card {i} number of samples: {int(num_samples / 1e6)} MS, "
                    f"acquisition time: {acq_duration} s, "
                    f"post-trigger time: {post_acq_duration} s"
                )
                # Set the number of samples to be acquired

                data_transfer.duration(
                    duration=(acq_duration) * units.s,
                    post_trigger_duration=(post_acq_duration) * units.s,
                )

                data_transfer.start_buffer_transfer(
                    spcm.M2CMD_DATA_STARTDMA, direction=spcm.SPCM_DIR_CARDTOPC
                )
                # Store this for use in the thread
                gated_transfers.append(data_transfer)
        except Exception as e:
            process_logger.error(f"Error configuring card stack: {e}")
            raise e

        try:
            # Enable Star-Hub sync (if present)
            stack.sync_enable(True)

            # Start acquisition on all cards and wait for DMA
            # M2CMD_CARD_ENABLETRIGGER => arm trigger
            # M2CMD_DATA_WAITDMA       => block until data in buffer
            process_logger.info("Starting acquisition on all cards...")

            stack.start(spcm.M2CMD_CARD_ENABLETRIGGER)  # | spcm.M2CMD_DATA_WAITDMA)
            process_logger.info("All cards triggered and acquisition in progress...")
        except Exception as e:
            process_logger.error(f"Error starting acquisition: {e}")
            raise e

        # Create and start a thread for each card to handle saving data
        try:
            threads: list[threading.Thread] = []
            for i, card in enumerate(stack.cards):
                t = CardThread(
                    card_index=i,
                    card_obj=card,
                    gated_transfer=gated_transfers[i],
                    ex_queue=exc_queue,
                )
                threads.append(t)
                t.start()

            # Wait for all threads to finish
            for t in threads:
                t.join()
            process_logger.info("All threads finished.")

            if not exc_queue.empty():
                while not exc_queue.empty():
                    ex: Exception = exc_queue.get()
                    process_logger.error(f"Caught exception from thread: {ex}")
                raise RuntimeError("Caught exception from thread during acquisition.")

            process_logger.info(
                f"Len of gated transfers: {[len(entry.buffer) for entry in gated_transfers]}"
            )
            list_of_data: list[np.ndarray] = []
            for data in gated_transfers:
                for col_no in range(data.buffer.shape[0]):
                    process_logger.info(
                        f"Processing column number: {col_no} of card {data.card}"
                    )
                    list_of_data.append(
                        channels[0].convert_data(
                            data=data.buffer.T[:, col_no], return_unit=units.V
                        )
                    )
            # Concatenate all data into a single array
            data_arr = np.array(list_of_data).T
            # Crop data according to trigger channel
            data_arr: np.ndarray = crop_data(
                data=data_arr,
                data_acq_params=acq_params,
            )
            # Check if the data is dissimilar across channels
            if acq_params.with_channel_check:
                dissimilar_channels: np.ndarray = detect_dissimilar_channels(
                    data=data_arr, data_acq_params=acq_params
                )
                if np.any(dissimilar_channels > 0):
                    process_logger.warning(
                        f"Detected dissimilar channels: {dissimilar_channels}"
                    )
                    identified_channels: list = [
                        i for i, val in enumerate(dissimilar_channels) if val > 0
                    ]
                    process_logger.warning(
                        f"Identified dissimilar channels: {identified_channels}"
                    )
            # # Save the data to CSV files
            save_to_file(data=data_arr, data_acq_params=acq_params)
            # Plot data if requested
            plot_data(data=data_arr, data_acq_params=acq_params)
        except Exception as e:
            process_logger.error(f"Encountered exception {e}")
            raise e


def main() -> None:
    """
    Main function to run the Automated Data Acquisitor. It initializes the acquisition parameters
    and starts the acquisition process.

    Args:
        None
    Returns:
        None
    Raises:
        None
    Notes:
        - This function is the entry point for the Automated Data Acquisitor.
        - It handles command-line argument parsing and logger setup.
    """
    # Set up logging
    local_logger: logging.Logger = setup_logger(
        log_file=pathlib.Path("daq_log.log"),
    )
    parsed_acq_params: AcqParams = parse_args(process_logger=local_logger)

    # Run the acquisition process
    run_acquisition(acq_params=parsed_acq_params, process_logger=local_logger)


if __name__ == "__main__":
    main()
    # local_logger: logging.Logger = setup_logger(
    #     log_file=pathlib.Path("daq_log.log"),
    # )
    # parsed_acq_params: AcqParams = parse_args(process_logger=local_logger)

    # # Run the acquisition process
    # run_acquisition(acq_params=parsed_acq_params, process_logger=local_logger)
