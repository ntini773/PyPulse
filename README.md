# 🫀 PyPulse — A Distributed Log Orchestrator

> *A casual Python learning project turned into a mini distributed system.*

---

## 📖 About

I was casually going through Python's essential standard and third-party libraries — `os`, `json`, `pathlib`, `argparse`, `shutil`, `threading`, `multiprocessing`, `requests`, and even the `google-genai` SDK — just trying to understand what each one actually *does* in a real scenario rather than reading dry docs.

Instead of writing disconnected toy scripts, I decided to stitch everything together into one cohesive project: **PyPulse**. The result is a CLI-driven log orchestrator that simulates a real-world distributed backend pipeline, where each Python library plays a clearly defined role.

---

## 🧩 The Problem — A Story

> *Imagine you're a lone sysadmin at 2 AM.*

Hundreds of servers are silently spitting out heartbeat logs every second. Your job? Make sure nothing is on fire.

But there's a catch — **your disk is filling up fast**. If you don't watch it, the machine running your monitoring scripts will run out of space and crash *while* trying to save you from a crash. Classic.

On top of that, you need to **read thousands of log files simultaneously** — reading them one by one would take forever. You need parallelism.

Once you've crunched the data, you need to **ship a report to a remote server**. But networks fail. What happens if it doesn't go through?

And finally, once everything is synced, you need to **clean up** — zip the old logs, archive them, and wipe the workspace so tomorrow's logs have room to breathe.

That's PyPulse. A five-phase pipeline that solves a real problem using nothing but Python's standard toolkit (plus a sprinkle of AI at the end).

---

## ⚙️ System Architecture & Components

### Phase 1 — `FakeServer` *(Log Generator)*
> **Libraries:** `os`, `json`, `pathlib`, `time`, `threading`

This component simulates a live server environment. It creates a directory of `.log` files, each containing a JSON heartbeat from a fictional node — with a timestamp, node ID, CPU/memory metrics, and a status (`OK` or `ERROR`).

It acts as the **data source** for the rest of the pipeline. It respects a shared `threading.Event` flag so it can be halted mid-generation if the watchdog says "enough."

---

### Phase 2 — `watchdog()` *(Disk Space Monitor)*
> **Libraries:** `threading`, `pathlib`, `time`

This is a **background thread** — a guardian that runs silently alongside the log generator. Every second, it calculates the total size of the log folder. The moment it crosses a defined limit (`MAX_FOLDER_SIZE`), it fires the shared `stop_event` flag, which signals `FakeServer` to stop writing new files.

Think of it as a circuit breaker. It prevents runaway log generation from eating your disk alive.

---

### Phase 3 — `LogProcessor` *(Parallel Log Cruncher)*
> **Libraries:** `multiprocessing`, `json`, `pathlib`, `os`

Once log generation is halted, `LogProcessor` kicks in. It uses a **multiprocessing Pool** to read and parse every `.log` file in parallel — bypassing Python's GIL by farming work out to multiple CPU cores.

Each worker reads a file, extracts the node ID, status, and CPU load, and returns a clean dictionary. A callback collects all results back on the main thread. This phase turns raw JSON files into a structured, in-memory dataset.

---

### Phase 4a — `NetworkManager` *(Report Dispatcher)*
> **Libraries:** `requests`, `json`, `time`

`NetworkManager` consolidates the processed results into a final report payload and **POSTs it to a remote API** (using `httpbin.org` as a mock server). It handles network failures gracefully — if the request times out or returns an error, it saves the report locally to `emergency_backup.json` instead of losing the data.

---

### Phase 4b — `ControlPlane` *(AI-Powered Analysis + Remote Sync)*
> **Libraries:** `requests`, `os`, `json`, `google-genai`

`ControlPlane` is the smart layer. It first pulls a remote configuration via a GET request, then attempts to send the log summary to **Google's Gemini AI** for an executive health analysis — asking it to summarize system health percentage, flag critical nodes, and interpret the data.

If no API key is configured (or the AI call fails), it automatically falls back to a standard `requests.post` sync to the mock server. No silent failures.

---

### Phase 5 — `Archiver` *(Lifecycle Manager)*
> **Libraries:** `shutil`, `os`, `pathlib`, `time`

Once the sync is confirmed successful, `Archiver` closes the loop. It **zips the entire log directory** into a timestamped archive, then purges the original `.log` files, and removes the now-empty directory. The workspace is left clean and ready for the next run.

---

## 🗺️ Data Flow

```
START
  │
  ▼
os / pathlib ──────► Create /data/logs directory
  │
  ▼
threading ─────────► Start Watchdog (background disk monitor)
  │
  ▼
FakeServer ────────► Generate heartbeat .log files (JSON)
  │
  ▼  [stop_event fires when disk limit hit]
  │
  ▼
multiprocessing ───► Parse all .log files in parallel
  │
  ▼
json ───────────────► Aggregate into structured results list
  │
  ▼
google-genai SDK ──► AI health analysis (or fallback POST via requests)
  │
  ▼
shutil / os ────────► Zip logs → Archive → Purge raw files
  │
  ▼
END
```

---

## 🛠️ Tech Stack

| Library | Role |
|---|---|
| `os` | Directory creation, file removal, env vars |
| `json` | Serializing/deserializing log data and reports |
| `pathlib` | Clean, object-oriented file path handling |
| `argparse` | CLI argument parsing (`server_path`) |
| `time` | Timestamps, sleep intervals |
| `shutil` | Disk usage checks, ZIP archiving, recursive delete |
| `threading` | Background watchdog thread, shared `Event` flag |
| `multiprocessing` | Parallel file processing via `Pool.apply_async` |
| `requests` | HTTP GET/POST to remote APIs with error handling |
| `python-dotenv` | Loading `GEMINI_API_KEY` from a `.env` file |
| `google-genai` | AI-powered log analysis via Gemini SDK |

---

## 🚀 Getting Started

### Prerequisites

```bash
pip install requests python-dotenv google-genai
```

### (Optional) Configure AI Analysis

Create a `.env` file in the project root:

```env
GEMINI_API_KEY=your_gemini_api_key_here
```

Without this, the system will fall back to a standard HTTP sync.

### Run

```bash
python main.py
# or specify a custom log path:
python main.py data/my_logs
```

---

## 📁 Project Structure

```
PyPulse/
├── main.py               # Full pipeline: all phases in one script
├── emergency_backup.json # Auto-generated if network sync fails
├── archives/             # Auto-generated ZIP archives of processed logs
├── TASK.md               # Original design document
└── .env                  # (Optional) Your API keys — never commit this!
```

---

## 💡 What I Learned

Every library in this project earned its place by solving a **specific, concrete problem**:

- `threading` taught me *when* to go parallel (I/O-bound tasks like monitoring).
- `multiprocessing` showed me *why* the GIL matters and how to route around it for CPU-bound work.
- `requests` gave me respect for all the things that can go wrong on a network.
- `shutil` made file system operations feel civilised.
- `pathlib` made me never want to use string concatenation for paths again.
- `google-genai` made me realise AI can be just another API call away.

PyPulse started as a learning exercise — it ended up as something I'd actually trust to handle real log data.
