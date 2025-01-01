import requests
from typing import Optional, Dict, Any, Union, BinaryIO
import json
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import os
import time
from datetime import datetime

def load_settings(config_path="config.json"):
    """Load settings from the shared config file."""
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found: {config_path}")
    
    with open(config_path, "r") as f:
        data = f.read().strip()
        if not data:
            raise ValueError("Config file is empty.")
        return json.loads(data)

class FileUpdateHandler(FileSystemEventHandler):
    def on_modified(self, event):
        if event.is_directory:
            return
        log_message(f"File updated: {event.src_path}")
        update_file(event.src_path, os.path.basename(event.src_path))

def update_file(path_to_file, file_name):
    settings = load_settings("config.json")
    api_url = f"{settings.get('pteredoctyl_url')}api/client/servers/{settings.get('pteredoctyl_server_id')}/files/upload"
    token = settings.get("pteredoctyl_token")
    
    try:
        # GET request example
        response = make_authenticated_request(
            url=api_url,
            bearer_token=token,
        )
        log_message(f"Fetched upload URL")
        data = response.json()
        try:
            # Example 1: Simple file upload
            with open(path_to_file, "rb") as f:
                files = {
                    "files": (file_name, f, "application/java-archive")  # Use appropriate content type
                }
                params = {
                    "directory": settings.get('pteredoctyl_defult_upload_folder')  # For example: "/plugins" or "/config"
                }
                
                response = make_authenticated_request(
                    url=data['attributes']['url'],
                    bearer_token=token,
                    method="POST",
                    files=files,
                    params=params
                )
                log_message(f"File {file_name} successfully uploaded!")
        except requests.exceptions.RequestException as e:
            log_message(f"Watchdog: Failed to make request: {str(e)}")
        
    except requests.exceptions.RequestException as e:
        log_message(f"Watchdog: Failed to make request: {str(e)}")

def log_message(message):
    """Log message to a shared file or other medium."""
    timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open("log.txt", "a") as log_file:
        log_file.write(timestamp_str+" | "+message + "\n")

def make_authenticated_request(
    url: str,
    bearer_token: str,
    method: str = "GET",
    data: Optional[Dict[str, Any]] = None,
    params: Optional[Dict[str, Any]] = None,
    files: Optional[Dict[str, Union[tuple, BinaryIO]]] = None
) -> requests.Response:
    headers = {
        "Authorization": f"Bearer {bearer_token}",
        "Accept": "application/json"
    }
    
    if not files:
        headers["Content-Type"] = "application/json"
    
    try:
        request_kwargs = {
            "method": method.upper(),
            "url": url,
            "headers": headers,
            "params": params,
        }
        
        if files:
            request_kwargs["files"] = files
            if data:
                request_kwargs["data"] = data
        else:
            request_kwargs["data"] = json.dumps(data) if data else None
        
        response = requests.request(**request_kwargs)
        response.raise_for_status()
        return response
        
    except requests.exceptions.RequestException as e:
        log_message(f"Watchdog: Error making request: {str(e)}")
        raise

def monitor_directory(path_to_watch):
    event_handler = FileUpdateHandler()
    observer = Observer()
    observer.schedule(event_handler, path=path_to_watch, recursive=False)
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()



if __name__ == "__main__":
    settings = load_settings("config.json")
    directory_to_watch = settings.get("default_directory_to_watch", "D:/YourDirectory")
    try:
        monitor_directory(directory_to_watch)
    except (FileNotFoundError, NotADirectoryError, PermissionError) as e:
        log_message(f"Watchdog: Error: {e}")
    monitor_directory(directory_to_watch)
    print(f"Started watchdog on  {directory_to_watch}")
