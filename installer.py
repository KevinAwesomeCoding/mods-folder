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

# --- MODPACKS CONFIGURATION ---
MODPACKS = {
    "Wonderland": {
        "url": "https://github.com/KevinAwesomeCoding/mods-folder/releases/download/wonderland/mods.zip",
        "profile_name": "Wonderland",
        "folder_name": "Wonderland",
        "version_id": "1.20.1-forge-47.4.10",
        "icon": "Furnace",
        "required_loader": "Forge 1.20.1 Version 47.4.10" 
    },
    "The Backrooms": {
        "url": "https://github.com/KevinAwesomeCoding/mods-folder/releases/download/backrooms/mods.zip",
        "profile_name": "Backrooms",
        "folder_name": "Backrooms",
        "version_id": "fabric-loader-0.18.4-1.20.1",
        "icon": "Bookshelf",
        "required_loader": "Fabric 1.20.1 Version 0.18.4"
    },
    "The Anomaly": {
        "url": "https://github.com/KevinAwesomeCoding/mods-folder/releases/download/anomaly/mods.zip",
        "profile_name": "The Anomaly",
        "folder_name": "The Anomaly",
        "version_id": "1.20.1-forge-47.4.10",
        "icon": "Obsidian",
        "required_loader": "Forge 1.20.1 Version 47.4.10" 
    },
    "The One Who Watches": {
        "url": "https://github.com/KevinAwesomeCoding/mods-folder/releases/download/onewhowatches/mods.zip",
        "profile_name": "The One Who Watches",
        "folder_name": "The One Who Watches",
        "version_id": "1.20.1-forge-47.4.10",
        "icon": "Carved_Pumpkin",
        "required_loader": "Forge 1.20.1 Version 47.4.10" 
    },
    "The Obsessed": {
        "url": "https://github.com/KevinAwesomeCoding/mods-folder/releases/download/obsessed/mods.zip",
        "profile_name": "The Obsessed",
        "folder_name": "The Obsessed",
        "version_id": "1.20.1-forge-47.4.10",
        "icon": "Netherrack",
        "required_loader": "Forge 1.20.1 Version 47.4.10" 
    },
    "From The Fog": {
        "url": "https://github.com/KevinAwesomeCoding/mods-folder/releases/download/fromthefog/mods.zip",
        "profile_name": "From The Fog",
        "folder_name": "From The Fog",
        "version_id": "fabric-loader-0.18.4-1.21.11",
        "icon": "Glass",
        "required_loader": "Fabric 1.21.11 Version 0.18.4" 
    },
    "The Broken Script": {
        "url": "https://github.com/KevinAwesomeCoding/mods-folder/releases/download/brokenscript/mods.zip",
        "profile_name": "The Broken Script",
        "folder_name": "The Broken Script",
        "version_id": "1.20.1-forge-47.4.10",
        "icon": "Redstone_Block",
        "required_loader": "Forge 1.20.1 Version 47.4.10" 
    },
}

class InstallerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Modpack Installer")
        self.root.geometry("400x400")
        
        # Header
        tk.Label(root, text="Select a Modpack", font=("Segoe UI", 16, "bold")).pack(pady=20)
        
        # Dropdown
        tk.Label(root, text="Choose which server to install:", font=("Segoe UI", 10)).pack(pady=(0, 5))
        self.selected_pack = tk.StringVar()
        self.dropdown = ttk.Combobox(root, textvariable=self.selected_pack, state="readonly", font=("Segoe UI", 10))
        self.dropdown['values'] = list(MODPACKS.keys())
        self.dropdown.current(0)
        self.dropdown.pack(pady=10, ipadx=20)
        
        # Install Button
        self.btn_install = tk.Button(root, text="Install Selected Pack", command=self.pre_install_check, 
                                     bg="#4CAF50", fg="white", font=("Segoe UI", 12, "bold"), height=2, width=20)
        self.btn_install.pack(pady=20)
        
        # Progress Bar (Hidden by default)
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(root, variable=self.progress_var, maximum=100)
        
        # Status Label
        self.status = tk.Label(root, text="Ready", fg="gray")
        self.status.pack(side="bottom", pady=10)

    def pre_install_check(self):
        pack_name = self.selected_pack.get()
        config = MODPACKS[pack_name]
        loader_ver = config['required_loader']
        
        # --- THE PROMPT ---
        message = (
            f"IF you haven't PLEASE DOWNLOAD {loader_ver} TO CONTINUE.\n\n"
            "If you have done so, click OK."
        )
        
        # Show prompt. If they click OK, it returns True. If Cancel, False.
        response = messagebox.askokcancel("Requirement Check", message, icon='warning')
        
        if response: # User clicked OK
            self.start_thread()
        else: # User clicked Cancel
            self.update_status("Installation cancelled.")

    def start_thread(self):
        self.btn_install.config(state="disabled", text="Installing...")
        self.progress_bar.pack(fill="x", padx=40, pady=10)
        threading.Thread(target=self.run_install, daemon=True).start()

    def run_install(self):
        try:
            pack_name = self.selected_pack.get()
            self.install_logic(pack_name)
            
            # Installation successful
            self.root.after(0, self.reset_ui)
            self.root.after(0, lambda: self.status.config(text="Installation Complete"))
            self.root.after(0, lambda: messagebox.showinfo("Success", f"Installed '{pack_name}' successfully!"))
            
        except Exception as e:
            # Installation failed
            self.root.after(0, lambda: messagebox.showerror("Error", str(e)))
            self.root.after(0, self.reset_ui)
            self.root.after(0, lambda: self.status.config(text="Error occurred."))

    def reset_ui(self):
        self.btn_install.config(state="normal", text="Install Selected Pack")
        self.progress_bar.pack_forget()

    def update_status(self, text):
        self.root.after(0, lambda: self.status.config(text=text))

    def update_progress(self, current, total):
        percent = (current / total) * 100
        self.root.after(0, lambda: self.progress_var.set(percent))

    def download_file(self, url, path):
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            total_size = int(response.info().get('Content-Length', 0))
            block_size = 8192
            downloaded = 0
            
            with open(path, 'wb') as out_file:
                while True:
                    chunk = response.read(block_size)
                    if not chunk: break
                    out_file.write(chunk)
                    downloaded += len(chunk)
                    if total_size > 0:
                        self.update_progress(downloaded, total_size)

    def get_mc_dir(self):
        system = platform.system()
        if system == 'Windows':
            return os.path.join(os.getenv('APPDATA'), '.minecraft')
        elif system == 'Darwin':
            return os.path.join(os.path.expanduser("~"), "Library", "Application Support", "minecraft")
        return os.path.join(os.path.expanduser("~"), ".minecraft")

    def update_json_profile(self, mc_dir, name, game_dir, version_id, icon):
        profiles_file = os.path.join(mc_dir, 'launcher_profiles.json')
        if not os.path.exists(profiles_file): return

        with open(profiles_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        profile_id = name.replace(" ", "_")
        
        data['profiles'][profile_id] = {
            "created": "2025-01-01T00:00:00.000Z",
            "gameDir": game_dir,
            "icon": icon,
            "lastUsed": "2025-01-01T00:00:00.000Z",
            "lastVersionId": version_id,
            "name": name,
            "type": "custom"
        }

        shutil.copy(profiles_file, profiles_file + ".bak")
        with open(profiles_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)

    def install_logic(self, pack_name):
        mc_dir = self.get_mc_dir()
        if not os.path.exists(mc_dir): raise Exception("Minecraft not found.")

        config = MODPACKS[pack_name]
        
        # 1. Create Folder
        profile_dir = os.path.join(mc_dir, 'profiles', config['folder_name'])
        if not os.path.exists(profile_dir): os.makedirs(profile_dir)
        
        # 2. Download
        self.update_status(f"Downloading {pack_name}...")
        self.progress_var.set(0)
        
        temp_zip = os.path.join(profile_dir, "temp.zip")
        self.download_file(config['url'], temp_zip)
        
        # 3. Extract
        self.update_status("Extracting files...")
        self.progress_var.set(100)
        with zipfile.ZipFile(temp_zip, 'r') as z: z.extractall(profile_dir)
        os.remove(temp_zip)
        
        # 4. Profile
        self.update_json_profile(mc_dir, config['profile_name'], profile_dir, config['version_id'], config['icon'])

if __name__ == "__main__":
    root = tk.Tk()
    app = InstallerApp(root)
    root.mainloop()


