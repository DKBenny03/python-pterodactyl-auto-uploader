import tkinter as tk
import json
from tkinter import Frame, messagebox, scrolledtext
from tkinter.ttk import Notebook
import psutil
import os
import signal
import subprocess
from datetime import datetime
import requests
from typing import Optional, Dict, Any, Union, BinaryIO
import json



class MessageLoggerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Message Logger")
        self.root.geometry("600x600")
        
        # Load settings from the config file
        self.settings = self.load_settings()

        # ScrolledText widget for displaying messages
        self.text_area = tk.scrolledtext.ScrolledText(root, wrap=tk.WORD, state='disabled', height=20)
        self.text_area.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

        
        
        # Frame for buttons (start/stop)
        input_frame = tk.Frame(root)
        input_frame.pack(padx=10, pady=10, fill=tk.X)
        
        self.isWatchdogRunning = self.is_script_running(self.settings["watchdog_script_path"])

        self.watchdog_button_text = tk.StringVar()
        self.watchdog_button = tk.Button(input_frame, textvariable=self.watchdog_button_text, command=self.update_watchdog)
        self.watchdog_button.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        if not self.isWatchdogRunning:
            self.watchdog_button_text.set("Start Watchdog")
        if self.isWatchdogRunning:
            self.watchdog_button_text.set("Stop Watchdog")
            
        self.settings_button = tk.Button(input_frame, text="Settings", command=self.open_settings_window)
        self.settings_button.pack(side=tk.LEFT, fill=tk.X, expand=False, padx=(0, 5))

        self.clear_log_button = tk.Button(input_frame, text="Clear Log", command=self.clear_log)
        self.clear_log_button.pack(side=tk.LEFT, fill=tk.X, expand=False, padx=(0, 5))

        self.restart_server_button = tk.Button(input_frame, text="Restart server", command=self.restart_server)
        self.restart_server_button.pack(side=tk.LEFT, fill=tk.X, expand=False, padx=(0, 5))

        self.custom_command_button = tk.Button(input_frame, text="Send custom command", command=self.custom_command)
        self.custom_command_button.pack(side=tk.LEFT, fill=tk.X, expand=False, padx=(0, 5))
        
        self.watchdog_process = None
        #Stops watchdog if somehow runs on start
        if self.is_script_running(self.settings["watchdog_script_path"]):
            try:
                    self.watchdog_process.terminate()
                    self.watchdog_process.wait()
                    self.log_message("Stopped watchdog.py")
                    self.reload_buttons(self.root)
            except Exception as e:
                self.log_message(f"Error stopping watchdog.py: {str(e)}")

        if not os.path.exists(self.settings["log_file_path"]):
            # If the config file doesn't exist, create it with default settings
            file = open(self.settings["log_file_path"], 'w+')
        # Reload the buttons to update the state

        # Add a settings button to open the settings window
        self.settings_button = None
        self.update_log()

    def custom_command(self):
        api_url = f"{self.settings['pteredoctyl_url']}api/client/servers/{self.settings['pteredoctyl_server_id']}/command"
        token = self.settings['pteredoctyl_token']
        command = self.settings['custom_executeable']
        try:
            data = {
                "command": command  # Action to send to Pteredoctyl
            }

            headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json"
            }
            
            headers["Content-Type"] = "application/json"
            
            try:
                request_kwargs = {
                    "method": "POST",
                    "url": api_url,
                    "headers": headers,
                    "params": data,
                }
                
                
                request_kwargs["data"] = json.dumps(data) if data else None
                
                response = requests.request(**request_kwargs)
                response.raise_for_status()
                self.log_message(f"Command '{command}' sent!")
            except requests.exceptions.RequestException as e:
                self.log_message(f"Watchdog: Error making request: {str(e)}")
                raise
        except requests.exceptions.RequestException as e:
            self.log_message(f"Failed to restart: {str(e)}")


    def restart_server(self):
        api_url = f"{self.settings['pteredoctyl_url']}api/client/servers/{self.settings['pteredoctyl_server_id']}/power"
        token = self.settings['pteredoctyl_token']
        try:
            data = {
                "signal": "restart"  # Action to send to Pteredoctyl
            }

            headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json"
            }
            
            headers["Content-Type"] = "application/json"
            
            try:
                request_kwargs = {
                    "method": "POST",
                    "url": api_url,
                    "headers": headers,
                    "params": data,
                }
                
                
                request_kwargs["data"] = json.dumps(data) if data else None
                
                response = requests.request(**request_kwargs)
                response.raise_for_status()
                self.log_message(f"Server has been restarted")
            except requests.exceptions.RequestException as e:
                self.log_message(f"Watchdog: Error making request: {str(e)}")
                raise
        except requests.exceptions.RequestException as e:
            self.log_message(f"Failed to restart: {str(e)}")
        
    def clear_log(self):
        open("log.txt", "w").close()

    def update_log(self):
            """Reads the log file and updates the GUI."""
            try:
                with open("log.txt", "r") as log_file:
                    log_content = log_file.read()
                
                # Update the text area only if new content is added
                self.text_area.configure(state='normal')
                self.text_area.delete(1.0, tk.END)  # Clear existing content
                self.text_area.insert(tk.END, log_content)  # Insert the updated content
                self.text_area.configure(state='disabled')
                self.text_area.yview(tk.END)  # Scroll to the end
            except FileNotFoundError:
                pass  # If log.txt doesn't exist yet, no need to do anything

            # Schedule the next update in 1000 ms (1 second)
            self.root.after(1000, self.update_log)
    def load_settings(self):
        """Load settings from the config file."""
        config_path = "config.json"
        
        # Check if the config file exists
        if not os.path.exists(config_path):
            # If the config file doesn't exist, create it with default settings
            self.create_default_config(config_path)
            return self.load_settings()  # Retry loading after creating the default config
        
        # Try reading the config file
        try:
            with open(config_path, "r") as config_file:
                data = config_file.read().strip()
                if not data:  # If the file is empty, create default settings
                    self.create_default_config(config_path)
                    return self.load_settings()  # Retry loading after creating the default config
                return json.loads(data)
        except json.JSONDecodeError:
            # If the file is corrupted or not valid JSON, create default settings
            self.create_default_config(config_path)
            return self.load_settings()  # Retry loading after creating the default config

    def create_default_config(self, config_path):
        """Create a default config file with default settings."""
        default_settings = {
            "watchdog_script_path": "watchdog_.py",
            "log_file_path": "log.txt",
            "default_directory_to_watch": "D:/YourDirectory",
            "pteredoctyl_url": "https://panel.host.xyz/",
            "pteredoctyl_server_id": "SERVERID",
            "pteredoctyl_token": "TOKEN",
            "pteredoctyl_defult_upload_folder": "/plugins",
            "python_executable": "python",
            "custom_executeable": "plugman reload Link"
        }
        with open(config_path, "w") as config_file:
            json.dump(default_settings, config_file, indent=4)

    def save_settings(self):
        """Save the current settings to the config file."""
        with open("config.json", "w") as config_file:
            json.dump(self.settings, config_file, indent=4)

    def open_settings_window(self):
        """Opens a new window for settings."""
        settings_window = tk.Toplevel(self.root)  # Ensure the settings window is initialized properly
        settings_window.title("Settings")
        settings_window.geometry("400x300")
        
        tk.Label(settings_window, text="Pteredoctyl Host").pack(pady=5)
        pteredoctyl_url = tk.Entry(settings_window)
        pteredoctyl_url.insert(0, self.settings["pteredoctyl_url"])
        pteredoctyl_url.pack(pady=5)
        
        tk.Label(settings_window, text="Pteredoctyl Server ID").pack(pady=5)
        pteredoctyl_server_id = tk.Entry(settings_window)
        pteredoctyl_server_id.insert(0, self.settings["pteredoctyl_server_id"])
        pteredoctyl_server_id.pack(pady=5)
        
        tk.Label(settings_window, text="Pteredoctyl API Key").pack(pady=5)
        pteredoctyl_token = tk.Entry(settings_window)
        pteredoctyl_token.insert(0, self.settings["pteredoctyl_token"])
        pteredoctyl_token.pack(pady=5)
        
        tk.Label(settings_window, text="Pteredoctyl Upload Folder").pack(pady=5)
        pteredoctyl_defult_upload_folder = tk.Entry(settings_window)
        pteredoctyl_defult_upload_folder.insert(0, self.settings["pteredoctyl_defult_upload_folder"])
        pteredoctyl_defult_upload_folder.pack(pady=5)
        
        tk.Label(settings_window, text="Custom command to send").pack(pady=5)
        custom_executeable = tk.Entry(settings_window)
        custom_executeable.insert(0, self.settings["custom_executeable"])
        custom_executeable.pack(pady=5)

        tk.Label(settings_window, text="Directory to Watch:").pack(pady=5)
        dir_to_watch_entry = tk.Entry(settings_window)
        dir_to_watch_entry.insert(0, self.settings["default_directory_to_watch"])
        dir_to_watch_entry.pack(pady=5)

        tk.Label(settings_window, text="Python Executable:").pack(pady=5)
        python_executable_entry = tk.Entry(settings_window)
        python_executable_entry.insert(0, self.settings["python_executable"])
        python_executable_entry.pack(pady=5)

        # Save button to save the settings
        def save_and_close():
            self.settings["pteredoctyl_url"] = pteredoctyl_url.get()
            self.settings["pteredoctyl_server_id"] = pteredoctyl_server_id.get()
            self.settings["pteredoctyl_defult_upload_folder"] = pteredoctyl_defult_upload_folder.get()
            self.settings["pteredoctyl_token"] = pteredoctyl_token.get()
            self.settings["default_directory_to_watch"] = dir_to_watch_entry.get()
            self.settings["python_executable"] = python_executable_entry.get()
            self.settings["custom_executeable"] = custom_executeable.get()
            self.save_settings()
            settings_window.destroy()

        save_button = tk.Button(settings_window, text="Save", command=save_and_close)
        save_button.pack(pady=20)

    def is_script_running(self, script_name):
        """Checks if a script is running."""
        for proc in psutil.process_iter(attrs=['pid', 'name', 'cmdline']):
            try:
                if proc.info['cmdline'] and any(script_name in part for part in proc.info['cmdline']):
                    self.watchdog_process = proc
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        return False

    def startWatchdog(self):
        """Starts the watchdog script."""
       

    def update_watchdog(self):
        if self.watchdog_process:
            try:
                self.watchdog_process.terminate()
                self.watchdog_process.wait()
                self.log_message("Stopped watchdog.py")
                self.watchdog_button_text.set("Start Watchdog")
            except Exception as e:
                self.log_message(f"Error stopping watchdog.py: {str(e)}")
        else:
            try:
                self.watchdog_process = subprocess.Popen(
                    [self.settings["python_executable"], self.settings["watchdog_script_path"]],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                self.log_message("Started watchdog.py")
                self.watchdog_button_text.set("Stop Watchdog")
            except Exception as e:
                self.log_message(f"Error starting watchdog.py: {str(e)}")

    def log_message(self, message):
        timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open("log.txt", "a") as log_file:
            log_file.write(timestamp_str+" | "+message + "\n")

# Create the main application window
root = tk.Tk()

# Create the application with the message queue
app = MessageLoggerApp(root)

# Run the application
root.mainloop()
