#
# Created on Sun May 18 2025
#
# Created by Roland Axel Richter -- roland.richter@empa.ch
#
# Copyright (c) 2025 EMPA
#
"""Automated Data Acquisitor

This module contains the CardThread class, which is responsible for handling data retrieval
and saving for a single card.
The CardThread class is a subclass of threading.Thread and is designed to run in a separate
thread. It uses the already-opened Spectrum card object passed in and retrieves data from the card.

The class includes the following methods:

- __init__: Initializes the CardThread with the card index, card object, and gated transfer.
- run: The main method of the thread. It retrieves data from the card and waits for the data
to be available in the buffer.
"""
import queue
import threading

import spcm


class CardThread(threading.Thread):
    """
    Thread that handles data retrieval and saving for a single card.
    It uses the already-opened Spectrum card object passed in.
    """

    def __init__(
        self,
        card_index: int,
        card_obj: spcm.Card,
        gated_transfer: spcm.DataTransfer,
        ex_queue: queue.Queue | None = None,
    ) -> None:
        """
        Initializes the CardThread with the card index, card object, and gated transfer.

        Args:
            card_index (int): The index of the card in the stack.
            card_obj (spcm.Card): The Spectrum card object.
            gated_transfer (spcm.DataTransfer): The gated transfer object for the card.
            ex_queue (queue.Queue | None): Optional queue for exceptions.
        """
        super().__init__()
        self.card_index: int = card_index  # For logging
        self.card_obj: spcm.Card = card_obj  # This is stack.cards[i]
        self.gated_transfer: spcm.DataTransfer = gated_transfer
        self.ex_queue: queue.Queue | None = ex_queue
        self.name = f"CardThread-{self.card_index}"

    def run(self) -> None:
        """
        The main method of the thread. It retrieves data from the card and waits for
        the data to be available in the buffer.

        Args:
            None
        Returns:
            None
        Raises:
            None
        Notes:
            - This method is executed when the thread is started.
            - The thread will block until data is available in the buffer.
        """
        # pylint: disable=broad-exception-caught
        try:
            self.card_obj.cmd(spcm.M2CMD_DATA_WAITDMA)  # Wait for data in buffer
            _ = self.gated_transfer.buffer  # shape: (num_channels, total_samples)
        except Exception as e:
            if self.ex_queue is not None:
                self.ex_queue.put(e)
                return
            else:
                raise e
        # self.card_obj.cmd(spcm.M2CMD_DATA_WAITDMA)  # Wait for data in buffer
        # _ = self.gated_transfer.buffer  # shape: (num_channels, total_samples)
