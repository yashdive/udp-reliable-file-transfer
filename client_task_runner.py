#!/usr/bin/env python3
"""Client-side Task 1/2/3 runner for Simple-FTP.

Run this script on the client machine in a two-host setup. The server must be
running on the other machine before each trial.
"""

from __future__ import annotations

import argparse
import csv
import subprocess
import time
from pathlib import Path
from statistics import mean
from typing import Iterable, List, Tuple


TASK1_WINDOW_SIZES = [1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024]
TASK2_MSS_VALUES = list(range(100, 1001, 100))
TASK3_LOSS_VALUES = [round(value / 100.0, 2) for value in range(1, 11)]


def normalize_server_target(server_host: str, server_port: int) -> Tuple[str, int]:
    """Accept either host or host:port and return normalized host/port."""
    if ":" in server_host:
        host_part, port_part = server_host.rsplit(":", 1)
        if host_part and port_part.isdigit():
            return host_part, int(port_part)
    return server_host, server_port


def ensure_text(value: object) -> str:
    """Return a text string for subprocess output regardless of type."""
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def run_client_once(
    python_cmd: str,
    server_host: str,
    server_port: int,
    input_file: str,
    window_size: int,
    mss: int,
    protocol_timeout: float,
    run_timeout: float,
    verbose: bool,
) -> Tuple[bool, float, str, str, str]:
    """Run one client transfer attempt.

    Returns (ok, delay_or_elapsed, status, stdout_text, stderr_text).
    """
    server_host, server_port = normalize_server_target(server_host, server_port)
    command = [
        python_cmd,
        "Simple_ftp_client.py",
        server_host,
        str(server_port),
        input_file,
        str(window_size),
        str(mss),
        "--timeout",
        str(protocol_timeout),
    ]
    if verbose:
        command.append("--verbose")

    start = time.perf_counter()
    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=run_timeout,
        )
    except subprocess.TimeoutExpired as exc:
        elapsed = time.perf_counter() - start
        stdout_text = ensure_text(exc.stdout)
        stderr_text = ensure_text(exc.stderr)
        return False, elapsed, "timed_out", stdout_text, stderr_text

    elapsed = time.perf_counter() - start
    if completed.returncode != 0:
        return False, elapsed, f"process_error_{completed.returncode}", ensure_text(completed.stdout), ensure_text(completed.stderr)

    for line in completed.stdout.splitlines():
        if line.startswith("Transfer complete. Delay ="):
            try:
                delay = float(line.split("=")[1].split()[0])
                return True, delay, "ok", completed.stdout, completed.stderr
            except (ValueError, IndexError):
                return False, elapsed, "parse_error", completed.stdout, completed.stderr

    return False, elapsed, "missing_delay_line", completed.stdout, completed.stderr


def write_csv(path: Path, rows: Iterable[dict], fieldnames: List[str]) -> None:
    with path.open("w", newline="", encoding="ascii") as file_handle:
        writer = csv.DictWriter(file_handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def write_trial_log(
    log_dir: Path,
    task_name: str,
    setting_label: str,
    trial_index: int,
    attempt_index: int,
    status: str,
    stdout_text: str,
    stderr_text: str,
) -> None:
    safe_setting = setting_label.replace("=", "-").replace(".", "_")
    path = log_dir / (
        f"{task_name}_{safe_setting}_trial{trial_index:02d}_attempt{attempt_index:02d}_{status}.log"
    )
    with path.open("w", encoding="utf-8") as handle:
        handle.write("=== STDOUT ===\n")
        handle.write(stdout_text or "")
        handle.write("\n=== STDERR ===\n")
        handle.write(stderr_text or "")


def run_trial_with_retries(
    args: argparse.Namespace,
    log_dir: Path,
    task_name: str,
    setting_label: str,
    trial: int,
    window_size: int,
    mss: int,
) -> Tuple[bool, float, str]:
    last_status = "unknown"
    last_value = 0.0

    for attempt in range(1, args.max_retries + 2):
        ok, value, status, stdout_text, stderr_text = run_client_once(
            python_cmd=args.python,
            server_host=args.server_host,
            server_port=args.server_port,
            input_file=args.input_file,
            window_size=window_size,
            mss=mss,
            protocol_timeout=args.timeout,
            run_timeout=args.client_run_timeout,
            verbose=args.verbose,
        )

        write_trial_log(
            log_dir=log_dir,
            task_name=task_name,
            setting_label=setting_label,
            trial_index=trial,
            attempt_index=attempt,
            status=status,
            stdout_text=stdout_text,
            stderr_text=stderr_text,
        )

        if ok:
            return True, value, "ok"

        last_status = status
        last_value = value
        print(
            f"  Trial {trial} attempt {attempt} failed: status={status}. "
            f"See logs in {log_dir}",
            flush=True,
        )
        if attempt <= args.max_retries:
            input("Restart server if needed, then press Enter to retry this trial... ")

    return False, last_value, last_status


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Tasks 1-3 from the client machine")
    parser.add_argument("--python", default="python", help="Python command to use")
    parser.add_argument(
        "--server-host",
        required=True,
        help="Server machine IP or hostname, optionally host:port",
    )
    parser.add_argument("--server-port", type=int, default=7735, help="Server UDP port")
    parser.add_argument("--input-file", required=True, help="File to transfer")
    parser.add_argument("--trials", type=int, default=5, help="Number of trials per setting")
    parser.add_argument("--timeout", type=float, default=0.5, help="Client protocol timeout in seconds")
    parser.add_argument(
        "--client-run-timeout",
        type=float,
        default=120.0,
        help="Maximum wall-clock seconds for one client trial",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=2,
        help="Additional retries per trial on timeout/failure",
    )
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
    parser.add_argument(
        "--log-dir",
        default="trial_logs",
        help="Directory for per-trial stdout/stderr logs",
    )
    return parser.parse_args()


def run_task_1(args: argparse.Namespace, output_dir: Path, log_dir: Path) -> None:
    rows = []
    for window_size in TASK1_WINDOW_SIZES:
        delays = []
        failed_trials = 0
        print(f"Task 1: window size N={window_size}")
        for trial in range(1, args.trials + 1):
            input(f"Start the server, then press Enter to begin trial {trial}/{args.trials}... ")
            ok, value, status = run_trial_with_retries(
                args=args,
                log_dir=log_dir,
                task_name="task1",
                setting_label=f"N={window_size}",
                trial=trial,
                window_size=window_size,
                mss=500,
            )
            if ok:
                delays.append(value)
                print(f"  Trial {trial}: {value:.6f} sec")
            else:
                failed_trials += 1
                print(f"  Trial {trial}: failed ({status})")

        average_delay = mean(delays) if delays else 0.0
        rows.append(
            {
                "N": window_size,
                "average_delay_seconds": f"{average_delay:.6f}",
                "successful_trials": len(delays),
                "failed_trials": failed_trials,
            }
        )
        print(
            f"  Average delay: {average_delay:.6f} sec; "
            f"successful={len(delays)} failed={failed_trials}",
            flush=True,
        )

    write_csv(
        output_dir / "task1_window_size.csv",
        rows,
        ["N", "average_delay_seconds", "successful_trials", "failed_trials"],
    )


def run_task_2(args: argparse.Namespace, output_dir: Path, log_dir: Path) -> None:
    rows = []
    for mss in TASK2_MSS_VALUES:
        delays = []
        failed_trials = 0
        print(f"Task 2: MSS={mss}")
        for trial in range(1, args.trials + 1):
            input(f"Start the server, then press Enter to begin trial {trial}/{args.trials}... ")
            ok, value, status = run_trial_with_retries(
                args=args,
                log_dir=log_dir,
                task_name="task2",
                setting_label=f"MSS={mss}",
                trial=trial,
                window_size=64,
                mss=mss,
            )
            if ok:
                delays.append(value)
                print(f"  Trial {trial}: {value:.6f} sec")
            else:
                failed_trials += 1
                print(f"  Trial {trial}: failed ({status})")

        average_delay = mean(delays) if delays else 0.0
        rows.append(
            {
                "MSS": mss,
                "average_delay_seconds": f"{average_delay:.6f}",
                "successful_trials": len(delays),
                "failed_trials": failed_trials,
            }
        )
        print(
            f"  Average delay: {average_delay:.6f} sec; "
            f"successful={len(delays)} failed={failed_trials}",
            flush=True,
        )

    write_csv(
        output_dir / "task2_mss.csv",
        rows,
        ["MSS", "average_delay_seconds", "successful_trials", "failed_trials"],
    )


def run_task_3(args: argparse.Namespace, output_dir: Path, log_dir: Path) -> None:
    rows = []
    for loss_probability in TASK3_LOSS_VALUES:
        delays = []
        failed_trials = 0
        print(f"Task 3: loss probability p={loss_probability:.2f}")
        for trial in range(1, args.trials + 1):
            input(
                "Start the server with the matching p value, "
                f"then press Enter to begin trial {trial}/{args.trials}... "
            )
            ok, value, status = run_trial_with_retries(
                args=args,
                log_dir=log_dir,
                task_name="task3",
                setting_label=f"p={loss_probability:.2f}",
                trial=trial,
                window_size=64,
                mss=500,
            )
            if ok:
                delays.append(value)
                print(f"  Trial {trial}: {value:.6f} sec")
            else:
                failed_trials += 1
                print(f"  Trial {trial}: failed ({status})")

        average_delay = mean(delays) if delays else 0.0
        rows.append(
            {
                "p": f"{loss_probability:.2f}",
                "average_delay_seconds": f"{average_delay:.6f}",
                "successful_trials": len(delays),
                "failed_trials": failed_trials,
            }
        )
        print(
            f"  Average delay: {average_delay:.6f} sec; "
            f"successful={len(delays)} failed={failed_trials}",
            flush=True,
        )

    write_csv(
        output_dir / "task3_loss_probability.csv",
        rows,
        ["p", "average_delay_seconds", "successful_trials", "failed_trials"],
    )


def main() -> None:
    args = parse_args()
    if args.timeout <= 0:
        raise ValueError("--timeout must be positive")
    if args.client_run_timeout <= 0:
        raise ValueError("--client-run-timeout must be positive")
    if args.max_retries < 0:
        raise ValueError("--max-retries cannot be negative")

    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)
    log_dir = Path(args.log_dir)
    log_dir.mkdir(exist_ok=True)

    if args.task in ("1", "all"):
        run_task_1(args, output_dir, log_dir)

    if args.task in ("2", "all"):
        run_task_2(args, output_dir, log_dir)

    if args.task in ("3", "all"):
        run_task_3(args, output_dir, log_dir)


if __name__ == "__main__":
    main()
