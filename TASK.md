Design Document: PyPulse Orchestrator

1. Project Overview

PyPulse Orchestrator is a high-performance, CLI-based distributed system monitor and log processor. It is designed to demonstrate efficient resource management by combining multi-threaded hardware monitoring with multi-processed data crunching.

1.1 Objectives

Observability: Continuous background monitoring of system health (disk space).

Concurrency: Parallel processing of high-volume log data to maximize CPU utilization.

Reliability: Robust error handling for network requests and file I/O.

Persistence: Archiving and purging data post-processing to maintain system hygiene.

2. Technical Requirements

2.1 Functional Requirements

Environment Setup: Automatic creation of directory structures and generation of simulated log data.

Health Watchdog: A background service that can halt processing if system resources are critically low.

Parallel Processing: Parsing multiple files simultaneously without blocking the main execution thread.

Data Serialization: Transforming raw logs into structured JSON reports.

Remote Sync: Transmitting results to a central API with retry/timeout logic.

Lifecycle Management: Compressing processed logs and clearing the workspace.

2.2 Technology Stack & Methods

Library

Key Methods to Use

os

listdir(), path.join(), makedirs(), remove()

shutil

disk_usage(), make_archive()

json

dumps(), loads(), dump()

requests

post(), exceptions.RequestException

threading

Thread(), Event(), daemon=True

multiprocessing

Pool(), apply_async(), cpu_count()

3. System Architecture

3.1 Module Breakdown

Module A: The System Watchdog

Type: Threaded (I/O Bound)

Logic: Uses a threading.Event as a global circuit breaker. If shutil.disk_usage detects < 10% free space, the event is set, and the Parallel Engine must pause or exit gracefully.

Module B: The Parallel Engine

Type: Multi-processed (CPU Bound)

Worker: process_log_worker(file_path) reads and validates JSON content within logs.

Callback: on_file_processed(result) gathers results from various processes into a shared memory structure.

Module C: Data Transformation

Logic: Aggregates Worker results and Watchdog status. Outputs a "Pretty Printed" JSON string to the console and saves a final_report.json to the /reports directory.

Module D: The Cloud Syncer

Logic: Uses requests.post. It must handle connection errors and status codes. Logic only proceeds to "Archive" if the status code is 200 OK.

Module E: The Archiver

Logic: Uses shutil.make_archive to create a timestamped ZIP of the data/logs folder, followed by os.remove to purge the original text files.

4. Data Flow Diagram

START -> os creates /data, /reports, /archives.

INIT -> threading starts the Watchdog.

PROCESS -> multiprocessing.Pool maps workers to files in /data/logs.

COLLECT -> Callback updates the global results list.

REPORT -> json creates the final payload.

SYNC -> requests pushes payload to API.

CLEANUP -> shutil zips logs; os deletes files.

END -> Script exits; daemon threads terminate.

5. Success Criteria Checklist

[ ] Watchdog thread runs without blocking log processing.

[ ] Multi-core utilization is confirmed during the "Parallel" phase.

[ ] API failures do not cause data loss (logs are only deleted on 200 OK).

[ ] final_report.json contains valid, parsed data from all 10 dummy logs.

[ ] All processes and threads are closed using try...finally.