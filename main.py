import os 
import json 
from pathlib import Path
import argparse
import time
import shutil
import threading
import multiprocessing
import requests

from dotenv import load_dotenv

MAX_FOLDER_SIZE =  10 * 1024 # 10 KB in bytes
MODEL_ID = "gemini-1.5-flash"
MOCK_API_URL = "https://httpbin.org/post"
class FakeServer:
    def __init__(self,server_path,stop_event):
        self.server_path = server_path
        if not os.path.exists(server_path):
            print(f"[*] Server path {self.server_path} not found. Creating...")
            os.makedirs(server_path,mode=0o700)
            print("[*] Generating dummy logs (Watchdog is active)...")
            for i in range(10000):
                if stop_event.is_set(): # <--- CHECK THE FLAG
                    print("\n[!] Log generation halted by Watchdog: Storage limit exceeded.")
                    break
                # file_name = Path(server_path)/f"file_{i}.log"
                log_file = self.server_path / f"node_{i}.log"
                data_dict = {
                    "timestamp": time.time(),
                    "node_id": f"Srv-Alpha-{i % 5}",
                    "status": "ERROR" if i % 10 == 0 else "OK",
                    "metrics": {"cpu": i * 1.5, "mem": i * 0.8},
                    "message": "Heartbeat pulse detected"
                }
                # content = json.dumps(data_dict,indent=4)
                with open(log_file,"w") as f:
                    # f.write(content)
                    json.dump(data_dict,f,indent=4)
                time.sleep(0.2)
        else:
            print("[*] Server environment exists. Proceeding to processing.")

def watchdog(server_path,stop_event):
    while not stop_event.is_set():
        # Get total size of all files in the server folder
        current_size = sum(f.stat().st_size for f in Path(server_path).rglob('*') if f.is_file())
        size_in_kb = (current_size/1024)
        print(f"current_size={size_in_kb:.2f} KB")
        # If folder exceeds your custom 'quota'
        if current_size >= MAX_FOLDER_SIZE:
            print("!!! FOLDER LIMIT REACHED - Emergency Stop !!!")
            stop_event.set()
            break
        time.sleep(1) # Don't stress the CPU

class LogProcessor:
    def __init__(self):
        self.results=[] # A simple list to hold the parsed jsons
        # Use a Pool to bypass GIL for CPU-intensive JSON parsing
        self.pool = multiprocessing.Pool(processes=min(3,os.cpu_count()))
    
    @staticmethod
    def process_file(file_path):
        """Worker: Reads one file and returns a dict."""
        try:
            with open(file_path, "r") as f:
                data = json.load(f)
                return {
                    "node": data.get("node_id"),
                    "status": data.get("status"),
                    "load": data.get("metrics", {}).get("cpu", 0)
                }
        except Exception as e:
            return {"error":str(e),"file":str(file_path)}
    
    def collect_result(self,result):
        """Callback: Runs in the Main Thread to collect data.""" 
        self.results.append(result)
    
    def run(self, server_path):
        """Execution: Sends all files to the pool."""
        files = list(Path(server_path).glob("*.log"))
        print(f"Found {len(files)} logs. Starting Parallel Engine...")

        for f in files:
            # Syntax: apply_async(func, args, callback)
            self.pool.apply_async(
                self.process_file, 
                args=(f,), 
                callback=self.collect_result
            )

        # Essential: Stop accepting jobs and wait for workers to finish
        self.pool.close()
        self.pool.join()
        print(f"[+] Processing Complete. Aggregated {len(self.results)} data points.")

        return self.results


class NetworkManager:
    def __init__(self, api_url="https://httpbin.org"):
        self.api_url = api_url
    
    def send_report(self, data_list):
        """Consolidates data and sends it to the remote server."""

        # Creating the final report
        report ={ 
            "timestamp":time.time(),
            "status":"COMPLETED",
            "total_logs_successfully_processed":len(data_list),
            "payload": data_list[:10]  # Sending first 10 for brevity in this demo
        }
        print(f"\n--- Sending Report to {self.api_url} ---")

        # 2. Try-Except for Network Safety
        try:
            # Use 'json=' parameter to auto-serialize and set headers
            response =  requests.post(self.api_url,json=report,timeout=5)

            # 3. Check for HTTP errors (like 404 or 500)
            response.raise_for_status()
            print(f"Success! Server Response Code: {response.status_code}")
            # Show a snippet of what the server received
            server_data = response.json()
            print(f"Server verified receipt of {len(server_data.get('json', {}).get('payload', []))} samples.")
        except requests.exceptions.RequestException as e:
            print(f"!!! Network Error: {e} !!!")
            print("Action: Report saved to local 'emergency_backup.json' instead.")
            with open("emergency_backup.json", "w") as f:
                json.dump(report, f, indent=4)

class Archiver:
    """Phase 5: Cleanup & Storage Lifecycle"""
    @staticmethod
    def cleanup(server_path,archive_dir="archives"):
        print(f"[*] Finalizing Lifecycle: Archiving logs...")
        archive_path = Path(archive_dir)
        archive_path.mkdir(exist_ok=True)
        timestamp=int(time.time())
        zip_name= f"pypulse_backup_{timestamp}"
        shutil.make_archive(str(archive_path/zip_name),'zip',server_path)
        print(f"[+] Archive created: {zip_name}.zip")
        # Purge original logs
        for file in Path(server_path).glob("*.log"):
            os.remove(file)
        print("[+] Raw log storage purged. System Clean.")

class ControlPlane:
    """Phase 4: Remote Sync & AI Analysis (Real API)"""
    def __init__(self):
        API_KEY = os.getenv("GEMINI_API_KEY")
        self.api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_ID}:generateContent?key={API_KEY}"


    def analyze_with_ai(self, log_summary):
        """Sends logs to Gemini API for a real high-level summary."""
        print("[*] Syncing with Cloud AI Control Plane...")
        
        summary_payload = log_summary[:20] # Send a sample for context
        prompt = (
            f"Analyze these system log snippets: {json.dumps(summary_payload)}. "
            "Provide a brief 2-line executive summary. "
            "Line 1: Overall system health percentage. Line 2: Which node ID needs attention."
        )
        
        payload = {
            "contents": [{ "parts": [{ "text": prompt }] }]
        }

        # Exponential Backoff Implementation
        for delay in [1, 2, 4, 8]:
            try:
                response = requests.post(self.api_url, json=payload, timeout=10)
                if response.status_code == 404:
                    print(f"[!] 404 Error: Model {MODEL_ID} not found. Check your API access.")
                    return False
                response.raise_for_status()
                
                result = response.json()
                summary = result['candidates'][0]['content']['parts'][0]['text']
                print(f"\n--- AI ORCHESTRATOR SUMMARY ---\n{summary.strip()}\n")
                return True
            except Exception as e:
                print(f"[!] Connection Issue: {e}")
                time.sleep(delay)
        
        print("[!] Cloud Sync Failed after retries.")
        return False


def main():
    parser = argparse.ArgumentParser(description="Initialize a fake server.")
    parser.add_argument(
        "server_path",
        nargs="?",
        default="data/logs",
        help="Path to the server directory"
    )
    args = parser.parse_args()
    server_path = Path(args.server_path)
    stop_event = threading.Event()
    t = threading.Thread(target=watchdog,args=(server_path,stop_event),daemon=True)
    t.start()
    server = FakeServer(server_path,stop_event)
        # NEW: Keep the main thread alive so we can see the watchdog prints
    print("Main: Monitoring disk... (Press Ctrl+C to stop manually)")
    try:
        while not stop_event.is_set():
            time.sleep(1)
    except KeyboardInterrupt:
        print("Manual exit.")
    
    # 1. Run Processor
    processor = LogProcessor()
    results = processor.run(server_path)
    
    # 2. NEW: Reporting Phase
    # if processor.results:
    #     reporter = NetworkManager()
    #     reporter.send_report(processor.results)
    # else:
    #     print("No results to report.")

    if results:
        # 4. Sync & AI Analysis (The "Real" API)
        control = ControlPlane()
        success = control.analyze_with_ai(results)

        # 5. Archive only on successful sync
        if success:
            Archiver.cleanup(server_path)
    else:
        print("[!] No data processed.")
    




if __name__ == "__main__":
    load_dotenv()
    main()