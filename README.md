# Simple-FTP over UDP (Go-Back-N)

This project implements reliable file transfer over UDP using Go-Back-N ARQ.

## Core Source Files

- `Simple_ftp_server.py`: receiver/server
- `Simple_ftp_client.py`: sender/client
- `simple_ftp_common.py`: packet format and checksum helpers
- `client_task_runner.py`: Task 1/2/3 experiment runner that writes CSV output
- `plot_results.py`: generates PNG plots from the CSV files
- `compare_files.py`: byte-level transfer validation tool

## Extra Credit Source Files

- `selective_repeat_server.py`: Selective Repeat receiver/server
- `selective_repeat_client.py`: Selective Repeat sender/client

## Optional or Generated Files

These are not part of the core source code and can be deleted if you want a clean repo:

- `client_demo.log`, `server_demo.log`, `client_highloss.log`, `server_highloss.log`
- `trial_logs/`
- `results/`
- `received_output.bin`, `demo_output.bin`, `demo_output_highloss.bin`
- `__pycache__/`
- `Project 2 Report.docx`
- `run_experiments.py` if you are only using `client_task_runner.py`
- `Simple_ftp_client`, `Simple_ftp_server`, `Simple_ftp_client.bat`, `Simple_ftp_server.bat` if you run the `.py` scripts directly

## Packet Formats

Data packet (header + payload):

- 32-bit sequence number
- 16-bit checksum over payload using UDP-style one's complement checksum
- 16-bit type = `0x5555`

ACK packet (header only, no payload):

- 32-bit ACKed sequence number
- 16-bit field = `0x0000`
- 16-bit type = `0xAAAA`

## Setup

Use the Python interpreter in the project virtual environment.

Windows:

```powershell
cd D:\Atharva_Projects\IP\Project2\udp-reliable-file-transfer
.\.venv\Scripts\Activate.ps1
```

Mac or Linux:

```bash
cd udp-reliable-file-transfer
source .venv/bin/activate
```

If you need plotting support:

```powershell
python -m pip install matplotlib
```

## Server Command

The server listens on port `7735`.

Windows:

```powershell
python Simple_ftp_server.py 7735 demo_output.bin 0.05 --verbose
```

Mac/Linux:

```bash
python3 Simple_ftp_server.py 7735 demo_output.bin 0.05 --verbose
```

Arguments:

- `port`: always `7735` for this project
- `file-name`: output file to write on the server side
- `p`: packet loss probability in `(0, 1)`

Server output on probabilistic drop:

```text
Packet loss, sequence number = X
```

## Client Command

Windows:

```powershell
python Simple_ftp_client.py 10.153.27.102 7735 demo_input.bin 64 500 --verbose
```

Mac/Linux:

```bash
python3 Simple_ftp_client.py 10.153.27.102 7735 demo_input.bin 64 500 --verbose
```

Arguments:

- `server-host-name`: server machine IP or hostname
- `server-port`: always `7735`
- `file-name`: input file to transfer
- `N`: Go-Back-N window size
- `MSS`: maximum segment size in bytes

Optional argument:

- `--timeout`: client protocol timeout in seconds, default `0.5`

Client output on timeout:

```text
Timeout, sequence number = Y
```

## Manual Demo Commands

Use these commands when you want to run the protocol by hand during the demo. Replace `10.153.27.102` with your server machine IP.

### Task 1 Manual Run

Server:

```powershell
python Simple_ftp_server.py 7735 demo_output.bin 0.05 --verbose
```

Client, one run for a specific window size:

```powershell
python Simple_ftp_client.py 10.153.27.102 7735 demo_input.bin 1 500 --verbose
```

For Task 1, repeat the client command 5 times for each window size in this list:

```text
1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024
```

### Task 2 Manual Run

Server:

```powershell
python Simple_ftp_server.py 7735 demo_output.bin 0.05 --verbose
```

Client, one run for a specific MSS value:

```powershell
python Simple_ftp_client.py 10.153.27.102 7735 demo_input.bin 64 100 --verbose
```

For Task 2, repeat the client command 5 times for each MSS value in this list:

```text
100, 200, 300, 400, 500, 600, 700, 800, 900, 1000
```

### Task 3 Manual Run

Server, restart it for each probability value:

```powershell
python Simple_ftp_server.py 7735 demo_output.bin 0.01 --verbose
```

Client, one run for a specific loss probability setting:

```powershell
python Simple_ftp_client.py 10.153.27.102 7735 demo_input.bin 64 500 --verbose
```

For Task 3, repeat the client command 5 times for each loss probability in this list, restarting the server each time you move to a new value:

```text
0.01, 0.02, 0.03, 0.04, 0.05, 0.06, 0.07, 0.08, 0.09, 0.10
```

## Task Runner Commands

This is the easiest way to run Tasks 1, 2, and 3 and collect CSV results.

Task 1:

```powershell
python client_task_runner.py --server-host 10.153.27.102 --server-port 7735 --input-file demo_input.bin --task 1 --trials 5 --timeout 0.5 --client-run-timeout 300 --max-retries 2 --verbose
```

Task 2:

```powershell
python client_task_runner.py --server-host 10.153.27.102 --server-port 7735 --input-file demo_input.bin --task 2 --trials 5 --timeout 0.5 --client-run-timeout 1200 --max-retries 2 --verbose
```

Task 3:

```powershell
python client_task_runner.py --server-host 10.153.27.102 --server-port 7735 --input-file demo_input.bin --task 3 --trials 5 --timeout 0.5 --client-run-timeout 1200 --max-retries 2 --verbose
```

All tasks:

```powershell
python client_task_runner.py --server-host 10.153.27.102 --server-port 7735 --input-file demo_input.bin --task all --trials 5 --timeout 0.5 --client-run-timeout 300 --max-retries 2 --verbose
```

The task runner writes:

- `results/task1_window_size.csv`
- `results/task2_mss.csv`
- `results/task3_loss_probability.csv`
- per-trial logs in `trial_logs/`

## Plotting

After the CSV files are created, generate plots with:

```powershell
python plot_results.py
```

This creates PNG files in `results/`:

- `task1.png`
- `task2.png`
- `task3.png`

## Verify Output File

```powershell
python compare_files.py demo_input.bin demo_output.bin
```

Prints `MATCH` if transfer is correct.

## Selective Repeat ARQ (Extra Credit)

These files are separate from the Go-Back-N implementation, so the normal project code is unchanged.

Server:

```powershell
python selective_repeat_server.py 7735 demo_output.bin 0.05 64 --verbose
```

Client:

```powershell
python selective_repeat_client.py 10.153.27.102 7735 demo_input.bin 64 500 --verbose
```

For the Selective Repeat Tasks 1, 2, and 3, use the same sweeps as the Go-Back-N tasks, but run them with the Selective Repeat client and server files above:

- Task 1: vary `N` with `MSS=500` and `p=0.05`
- Task 2: vary `MSS` with `N=64` and `p=0.05`
- Task 3: vary `p` with `N=64` and `MSS=500`

## Notes

- All key parameters are runtime-tunable, so there is no hardcoded `N`, `MSS`, or `p` in the protocol implementation.
- The client appends a zero-length data segment as an EOF marker so the server can terminate cleanly after one transfer.
