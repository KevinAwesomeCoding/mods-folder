import tkinter as tk
from tkinter import ttk, messagebox
import os
import json
import zipfile
import urllib.request
import shutil
import threading
import sys
import platform
import time 
import random

# CONFIG
MODPACKS_URL = "https://raw.githubusercontent.com/KevinAwesomeCoding/mods-folder/refs/heads/main/modpacks.json" 

class InstallerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Modpack Installer")
        self.root.geometry("400x500") 
        
        # 1. LOAD DATA FIRST
        self.modpacks = self.load_data()

        # Header
        tk.Label(root, text="Select a Modpack", font=("Segoe UI", 16, "bold")).pack(pady=(15, 5))

        # Refresh Button
        self.btn_refresh = tk.Button(root, text="🔄 Refresh List", command=self.refresh_data, font=("Segoe UI", 8))
        self.btn_refresh.pack(pady=5)
        
        # --- CATEGORY DROPDOWN ---
        tk.Label(root, text="Select Category:", font=("Segoe UI", 10, "bold")).pack(pady=(5, 0))
        self.selected_category = tk.StringVar()
        self.cat_dropdown = ttk.Combobox(root, textvariable=self.selected_category, state="readonly", font=("Segoe UI", 10))
        
        if self.modpacks:
            self.cat_dropdown['values'] = list(self.modpacks.keys())
            self.cat_dropdown.current(0)
        else:
            self.cat_dropdown['values'] = ["Error loading data"]

        self.cat_dropdown.bind("<<ComboboxSelected>>", self.update_pack_dropdown)
        self.cat_dropdown.pack(pady=5, ipadx=20)

        # --- MODPACK DROPDOWN ---
        tk.Label(root, text="Select Modpack:", font=("Segoe UI", 10)).pack(pady=(10, 0))
        self.selected_pack = tk.StringVar()
        self.pack_dropdown = ttk.Combobox(root, textvariable=self.selected_pack, state="readonly", font=("Segoe UI", 10))
        self.pack_dropdown.pack(pady=5, ipadx=20)
        
        # Install Button
        self.btn_install = tk.Button(root, text="Install Selected Pack", command=self.start_thread, 
                                     bg="#4CAF50", fg="white", font=("Segoe UI", 12, "bold"), height=2, width=20)
        self.btn_install.pack(pady=25)
        
        # Progress Bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(root, variable=self.progress_var, maximum=100)
        
        # Status Label
        self.status = tk.Label(root, text="Ready", fg="gray")
        self.status.pack(side="bottom", pady=10)

        # Initialize Dropdown Logic
        if self.modpacks:
            self.update_pack_dropdown(None)

    def load_data(self):
        """Downloads the JSON and returns it. Returns {} on error."""
        try:
            fresh_url = f"{MODPACKS_URL}?t={int(time.time())}-{random.randint(1, 1000)}"
            print(f"Downloading from: {fresh_url}")
            
            req = urllib.request.Request(fresh_url, headers={
                'User-Agent': 'Mozilla/5.0',
                'Cache-Control': 'no-cache',
                'Pragma': 'no-cache'
            })
            
            with urllib.request.urlopen(req) as response:
                data = response.read().decode('utf-8')
                return json.loads(data)
                
        except Exception as e:
            messagebox.showerror("Connection Error", f"Could not load modpack list.\n{e}")
            return {}

    def refresh_data(self):
        self.btn_refresh.config(state="disabled", text="Refreshing...")
        self.root.update_idletasks()
        
        new_data = self.load_data()
        
        if new_data:
            self.modpacks = new_data
            
            # Clear and Reset Category Dropdown
            self.cat_dropdown.set('') 
            self.cat_dropdown['values'] = list(self.modpacks.keys())
            
            if self.modpacks:
                self.cat_dropdown.current(0) 
                self.update_pack_dropdown(None) 
            
            messagebox.showinfo("Refreshed", "Modpack list updated successfully!")
        else:
            messagebox.showwarning("Refresh Failed", "Could not load new data. Keeping old list.")

        self.btn_refresh.config(state="normal", text="🔄 Refresh List")

    def update_pack_dropdown(self, event):
        if not self.modpacks: return
        
        category = self.selected_category.get()
        if category in self.modpacks:
            packs = list(self.modpacks[category].keys())
            self.pack_dropdown['values'] = packs
            if packs:
                self.pack_dropdown.current(0)
                self.btn_install.config(state="normal")
            else:
                self.pack_dropdown.set("No packs")
                self.btn_install.config(state="disabled")

    def start_thread(self):
        if not self.modpacks: return
        self.btn_install.config(state="disabled", text="Installing...")
        self.progress_bar.pack(fill="x", padx=40, pady=10)
        threading.Thread(target=self.run_install, daemon=True).start()

    def run_install(self):
        try:
            category = self.selected_category.get()
            pack_name = self.selected_pack.get()
            
            if pack_name not in self.modpacks[category]:
                raise Exception("Invalid selection.")

            config = self.modpacks[category][pack_name]
            mc_dir = self.get_mc_dir()
            
            # 1. Loader
            self.update_status(f"Checking loader for {pack_name}...")
            self.install_loader(mc_dir, config['loader_url'])
            
            # 2. Modpack
            self.install_modpack_logic(mc_dir, config)
            
            self.root.after(0, self.reset_ui)
            self.root.after(0, lambda: self.status.config(text="Installation Complete"))
            self.root.after(0, lambda: messagebox.showinfo("Success", f"Installed '{pack_name}' successfully!"))
            
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Error", str(e)))
            self.root.after(0, self.reset_ui)
            self.root.after(0, lambda: self.status.config(text="Error occurred."))
  
    def install_loader(self, mc_dir, loader_url):
        versions_dir = os.path.join(mc
