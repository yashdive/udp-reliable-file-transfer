#!/usr/bin/env python3
"""Client-side Task 1/2/3 runner for Simple-FTP.

This script is meant to be run on the client machine in a two-host setup.
The server must already be running on the other machine for each transfer.

For each trial, the script launches only the client, reads the delay from the
client output, and writes averaged results to CSV files.
"""

from __future__ import annotations

import argparse
import csv
import subprocess
from pathlib import Path
from statistics import mean
from typing import Iterable, List


TASK1_WINDOW_SIZES = [1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024]
TASK2_MSS_VALUES = list(range(100, 1001, 100))
TASK3_LOSS_VALUES = [round(value / 100.0, 2) for value in range(1, 11)]


def run_client_once(
    python_cmd: str,
    server_host: str,
    server_port: int,
    input_file: str,
    window_size: int,
    mss: int,
    timeout: float,
    verbose: bool,
) -> float:
    command = [
        python_cmd,
        "Simple_ftp_client.py",
        server_host,
        str(server_port),
        input_file,
        str(window_size),
        str(mss),
        "--timeout",
        str(timeout),
    ]
    if verbose:
        command.append("--verbose")

    completed = subprocess.run(command, check=True, capture_output=True, text=True)
    for line in completed.stdout.splitlines():
        if line.startswith("Transfer complete. Delay ="):
            try:
                return float(line.split("=")[1].split()[0])
            except (ValueError, IndexError) as exc:
                raise RuntimeError(f"Could not parse delay from line: {line}") from exc

    raise RuntimeError("Transfer complete line was not found in client output")


def write_csv(path: Path, rows: Iterable[dict], fieldnames: List[str]) -> None:
    with path.open("w", newline="", encoding="ascii") as file_handle:
        writer = csv.DictWriter(file_handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Tasks 1-3 from the client machine")
    parser.add_argument("--python", default="python", help="Python command to use")
    parser.add_argument("--server-host", required=True, help="Server machine IP or hostname")
    parser.add_argument("--server-port", type=int, default=7735, help="Server UDP port")
    parser.add_argument("--input-file", required=True, help="File to transfer")
    parser.add_argument("--trials", type=int, default=5, help="Number of trials per setting")
    parser.add_argument("--timeout", type=float, default=0.5, help="Client timeout in seconds")
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Pass through verbose mode to the client for extra logs",
    )
    parser.add_argument(
        "--task",
        choices=["1", "2", "3", "all"],
        default="all",
        help="Which task sweep to run",
    )
    parser.add_argument(
        "--output-dir",
        default="results",
        help="Directory where CSV files will be written",
    )
    return parser.parse_args()


def run_task_1(args: argparse.Namespace, output_dir: Path) -> None:
    rows = []
    for window_size in TASK1_WINDOW_SIZES:
        delays = []
        print(f"Task 1: window size N={window_size}")
        for trial in range(1, args.trials + 1):
            input("Start the server, then press Enter to begin trial " f"{trial}/{args.trials}... ")
            delay = run_client_once(
                python_cmd=args.python,
                server_host=args.server_host,
                server_port=args.server_port,
                input_file=args.input_file,
                window_size=window_size,
                mss=500,
                timeout=args.timeout,
                verbose=args.verbose,
            )
            delays.append(delay)
            print(f"  Trial {trial}: {delay:.6f} sec")
        average_delay = mean(delays)
        rows.append({"N": window_size, "average_delay_seconds": f"{average_delay:.6f}"})
        print(f"  Average delay: {average_delay:.6f} sec")

    write_csv(output_dir / "task1_window_size.csv", rows, ["N", "average_delay_seconds"])


def run_task_2(args: argparse.Namespace, output_dir: Path) -> None:
    rows = []
    for mss in TASK2_MSS_VALUES:
        delays = []
        print(f"Task 2: MSS={mss}")
        for trial in range(1, args.trials + 1):
            input("Start the server, then press Enter to begin trial " f"{trial}/{args.trials}... ")
            delay = run_client_once(
                python_cmd=args.python,
                server_host=args.server_host,
                server_port=args.server_port,
                input_file=args.input_file,
                window_size=64,
                mss=mss,
                timeout=args.timeout,
                verbose=args.verbose,
            )
            delays.append(delay)
            print(f"  Trial {trial}: {delay:.6f} sec")
        average_delay = mean(delays)
        rows.append({"MSS": mss, "average_delay_seconds": f"{average_delay:.6f}"})
        print(f"  Average delay: {average_delay:.6f} sec")

    write_csv(output_dir / "task2_mss.csv", rows, ["MSS", "average_delay_seconds"])


def run_task_3(args: argparse.Namespace, output_dir: Path) -> None:
    rows = []
    for loss_probability in TASK3_LOSS_VALUES:
        delays = []
        print(f"Task 3: loss probability p={loss_probability:.2f}")
        for trial in range(1, args.trials + 1):
            input("Start the server with the matching p value, then press Enter to begin trial " f"{trial}/{args.trials}... ")
            delay = run_client_once(
                python_cmd=args.python,
                server_host=args.server_host,
                server_port=args.server_port,
                input_file=args.input_file,
                window_size=64,
                mss=500,
                timeout=args.timeout,
                verbose=args.verbose,
            )
            delays.append(delay)
            print(f"  Trial {trial}: {delay:.6f} sec")
        average_delay = mean(delays)
        rows.append({"p": f"{loss_probability:.2f}", "average_delay_seconds": f"{average_delay:.6f}"})
        print(f"  Average delay: {average_delay:.6f} sec")

    write_csv(output_dir / "task3_loss_probability.csv", rows, ["p", "average_delay_seconds"])


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)

    if args.task in ("1", "all"):
        run_task_1(args, output_dir)

    if args.task in ("2", "all"):
        run_task_2(args, output_dir)

    if args.task in ("3", "all"):
        run_task_3(args, output_dir)


if __name__ == "__main__":
    main()
