#!/usr/bin/env python3
"""Simple-FTP server implementing Selective Repeat ARQ over UDP.

Usage:
    selective_repeat_server.py port file-name p N
"""

from __future__ import annotations

import argparse
import random
import socket
from pathlib import Path
from typing import Dict

from simple_ftp_common import (
    DATA_TYPE,
    compute_udp_style_checksum,
    make_ack_packet,
    parse_packet,
)


def _log_key_sequence(sequence_number: int) -> bool:
    return sequence_number < 5 or sequence_number % 100 == 0


def run_server(
    port: int,
    output_path: Path,
    loss_probability: float,
    window_size: int,
    verbose: bool,
) -> None:
    recv_base = 0
    received_packets = 0
    accepted_packets = 0
    buffered_packets = 0
    duplicate_packets = 0
    ignored_bad_checksum = 0
    buffered_payloads: Dict[int, bytes] = {}

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.bind(("0.0.0.0", port))
        if verbose:
            print(
                f"[SR SERVER] Listening on UDP port {port}; output={output_path}; "
                f"loss_probability={loss_probability}; window_size={window_size}",
                flush=True,
            )

        with output_path.open("wb") as output_file:
            while True:
                packet, client_address = sock.recvfrom(65535)
                received_packets += 1

                try:
                    sequence_number, recv_checksum, packet_type, payload = parse_packet(packet)
                except ValueError:
                    continue

                if packet_type != DATA_TYPE:
                    continue

                if random.random() <= loss_probability:
                    print(f"Packet loss, sequence number = {sequence_number}")
                    continue

                expected_checksum = compute_udp_style_checksum(payload)
                if recv_checksum != expected_checksum:
                    ignored_bad_checksum += 1
                    if verbose and _log_key_sequence(sequence_number):
                        print(
                            f"[SR SERVER] Ignored bad-checksum packet seq={sequence_number}",
                            flush=True,
                        )
                    continue

                if sequence_number < recv_base:
                    duplicate_packets += 1
                    sock.sendto(make_ack_packet(sequence_number), client_address)
                    if verbose and _log_key_sequence(sequence_number):
                        print(
                            f"[SR SERVER] Re-ACKed duplicate seq={sequence_number}; recv_base={recv_base}",
                            flush=True,
                        )
                    continue

                if sequence_number >= recv_base + window_size:
                    if verbose and _log_key_sequence(sequence_number):
                        print(
                            f"[SR SERVER] Ignored out-of-window packet seq={sequence_number}; recv_base={recv_base}",
                            flush=True,
                        )
                    continue

                if sequence_number not in buffered_payloads:
                    buffered_payloads[sequence_number] = payload
                    buffered_packets += 1
                    accepted_packets += 1
                    if verbose and _log_key_sequence(sequence_number):
                        print(
                            f"[SR SERVER] Buffered data seq={sequence_number}, bytes={len(payload)}",
                            flush=True,
                        )
                else:
                    duplicate_packets += 1
                    if verbose and _log_key_sequence(sequence_number):
                        print(
                            f"[SR SERVER] Duplicate in-window packet seq={sequence_number}",
                            flush=True,
                        )

                sock.sendto(make_ack_packet(sequence_number), client_address)

                while recv_base in buffered_payloads:
                    current_payload = buffered_payloads.pop(recv_base)
                    if len(current_payload) == 0:
                        if verbose:
                            print(
                                "[SR SERVER] EOF marker delivered; "
                                f"seq={recv_base}, transfer complete",
                                flush=True,
                            )
                            print(
                                "[SR SERVER] Summary: "
                                f"received_packets={received_packets}, "
                                f"accepted_packets={accepted_packets}, "
                                f"buffered_packets={buffered_packets}, "
                                f"duplicate_packets={duplicate_packets}, "
                                f"ignored_bad_checksum={ignored_bad_checksum}",
                                flush=True,
                            )
                        return

                    output_file.write(current_payload)
                    output_file.flush()
                    recv_base += 1

                    if verbose and _log_key_sequence(recv_base - 1):
                        print(
                            f"[SR SERVER] Delivered seq={recv_base - 1}, bytes={len(current_payload)}",
                            flush=True,
                        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Simple-FTP server using Selective Repeat")
    parser.add_argument("port", type=int, help="UDP listening port (e.g., 7735)")
    parser.add_argument("file_name", help="Output file name")
    parser.add_argument("p", type=float, help="Packet loss probability in (0, 1)")
    parser.add_argument("window_size", type=int, help="Selective Repeat window size N")
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable extra logs for debugging/demo screenshots",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.port <= 0 or args.port > 65535:
        raise ValueError("port must be in [1, 65535]")
    if not (0.0 < args.p < 1.0):
        raise ValueError("p must be in (0, 1)")
    if args.window_size <= 0:
        raise ValueError("window_size must be positive")

    output_path = Path(args.file_name)
    run_server(args.port, output_path, args.p, args.window_size, args.verbose)


if __name__ == "__main__":
    main()