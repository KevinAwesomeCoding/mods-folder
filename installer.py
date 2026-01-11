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
    "Horror": {
        "Wonderland": {
            "url": "https://github.com/KevinAwesomeCoding/mods-folder/releases/download/wonderland/mods.zip",
            "profile_name": "Wonderland",
            "folder_name": "Wonderland",
            "version_id": "1.20.1-forge-47.4.10",
            "icon": "Furnace",
            "loader_url": "https://github.com/KevinAwesomeCoding/mods-folder/releases/download/versions/1.20.1-forge-47.4.10.zip"
        },
        "The Backrooms": {
            "url": "https://github.com/KevinAwesomeCoding/mods-folder/releases/download/backrooms/mods.zip",
            "profile_name": "Backrooms",
            "folder_name": "Backrooms",
            "version_id": "fabric-loader-0.18.4-1.20.1",
            "icon": "Bookshelf",
            "loader_url": "https://github.com/KevinAwesomeCoding/mods-folder/releases/download/versions/fabric-loader-0.18.4-1.20.1.zip"
        },
        "The Anomaly": {
            "url": "https://github.com/KevinAwesomeCoding/mods-folder/releases/download/anomaly/mods.zip",
            "profile_name": "The Anomaly",
            "folder_name": "The Anomaly",
            "version_id": "1.20.1-forge-47.4.10",
            "icon": "Obsidian",
            "loader_url": "https://github.com/KevinAwesomeCoding/mods-folder/releases/download/versions/1.20.1-forge-47.4.10.zip"
        },
        "The One Who Watches": {
            "url": "https://github.com/KevinAwesomeCoding/mods-folder/releases/download/onewhowatches/mods.zip",
            "profile_name": "The One Who Watches",
            "folder_name": "The One Who Watches",
            "version_id": "1.20.1-forge-47.4.10",
            "icon": "Carved_Pumpkin",
            "loader_url": "https://github.com/KevinAwesomeCoding/mods-folder/releases/download/versions/1.20.1-forge-47.4.10.zip"
        },
        "The Obsessed": {
            "url": "https://github.com/KevinAwesomeCoding/mods-folder/releases/download/obsessed/mods.zip",
            "profile_name": "The Obsessed",
            "folder_name": "The Obsessed",
            "version_id": "1.20.1-forge-47.4.10",
            "icon": "Netherrack",
            "loader_url": "https://github.com/KevinAwesomeCoding/mods-folder/releases/download/versions/1.20.1-forge-47.4.10.zip"
        },
        "From The Fog": {
            "url": "https://github.com/KevinAwesomeCoding/mods-folder/releases/download/fromthefog/mods.zip",
            "profile_name": "From The Fog",
            "folder_name": "From The Fog",
            "version_id": "fabric-loader-0.18.4-1.21.11",
            "icon": "Glass",
            "loader_url": "https://github.com/KevinAwesomeCoding/mods-folder/releases/download/versions/fabric-loader-0.18.4-1.21.11.zip"
        },
        "The Broken Script": {
            "url": "https://github.com/KevinAwesomeCoding/mods-folder/releases/download/brokenscript/mods.zip",
            "profile_name": "The Broken Script",
            "folder_name": "The Broken Script",
            "version_id": "1.20.1-forge-47.4.10",
            "icon": "Redstone_Block",
            "loader_url": "https://github.com/KevinAwesomeCoding/mods-folder/releases/download/versions/1.20.1-forge-47.4.10.zip"
        },
        "000.jar": {
            "url": "https://github.com/KevinAwesomeCoding/mods-folder/releases/download/000/mods.zip",
            "profile_name": "000.jar",
            "folder_name": "000.jar",
            "version_id": "1.19.2-forge-43.5.2",
            "icon": "Barrier",
            "loader_url": "https://github.com/KevinAwesomeCoding/mods-folder/releases/download/versions/1.19.2-forge-43.5.2.zip"
        },
        "The Newest Goatman": {
            "url": "https://github.com/KevinAwesomeCoding/mods-folder/releases/download/goatman/mods.zip",
            "profile_name": "The Newest Goatman",
            "folder_name": "The Newest Goatman",
            "version_id": "1.19.2-forge-43.5.2",
            "icon": "Bone_Block",
            "loader_url": "https://github.com/KevinAwesomeCoding/mods-folder/releases/download/versions/1.19.2-forge-43.5.2.zip"
        },
        "Sanity": {
            "url": "https://github.com/KevinAwesomeCoding/mods-folder/releases/download/sanity/mods.zip",
            "profile_name": "Sanity",
            "folder_name": "Sanity",
            "version_id": "1.20.1-forge-47.4.10",
            "icon": "Soul_Sand",
            "loader_url": "https://github.com/KevinAwesomeCoding/mods-folder/releases/download/versions/1.20.1-forge-47.4.10.zip"
        },
        "The God": {
            "url": "https://github.com/KevinAwesomeCoding/mods-folder/releases/download/thegod/mods.zip",
            "profile_name": "The God",
            "folder_name": "The God",
            "version_id": "1.20.1-forge-47.4.10",
            "icon": "Beacon",
            "loader_url": "https://github.com/KevinAwesomeCoding/mods-folder/releases/download/versions/1.20.1-forge-47.4.10.zip"
        },
        "From The Caves": {
            "url": "https://github.com/KevinAwesomeCoding/mods-folder/releases/download/fromthecaves/mods.zip",
            "profile_name": "From The Caves",
            "folder_name": "From The Caves",
            "version_id": "1.20.1-forge-47.4.10",
            "icon": "Bedrock",
            "loader_url": "https://github.com/KevinAwesomeCoding/mods-folder/releases/download/versions/1.20.1-forge-47.4.10.zip"
        }
    },
    "Challenge": {
        # Placeholders
    }
}

class InstallerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Modpack Installer")
        self.root.geometry("400x450")
        
        # Header
        tk.Label(root, text="Select a Modpack", font=("Segoe UI", 16, "bold")).pack(pady=15)
        
        # --- CATEGORY DROPDOWN ---
        tk.Label(root, text="Select Category:", font=("Segoe UI", 10, "bold")).pack(pady=(5, 0))
        self.selected_category = tk.StringVar()
        self.cat_dropdown = ttk.Combobox(root, textvariable=self.selected_category, state="readonly", font=("Segoe UI", 10))
        self.cat_dropdown['values'] = list(MODPACKS.keys())
        self.cat_dropdown.bind("<<ComboboxSelected>>", self.update_pack_dropdown)
        self.cat_dropdown.current(0)
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

        # --- CORRECT PLACEMENT ---
        self.update_pack_dropdown(None)


    def update_pack_dropdown(self, event):
        category = self.selected_category.get()
        packs = list(MODPACKS[category].keys())
        
        self.pack_dropdown['values'] = packs
        if packs:
            self.pack_dropdown.current(0)
            self.btn_install.config(state="normal")
        else:
            self.pack_dropdown.set("No packs in this category")
            self.btn_install.config(state="disabled")

    def start_thread(self):
        self.btn_install.config(state="disabled", text="Installing...")
        self.progress_bar.pack(fill="x", padx=40, pady=10)
        threading.Thread(target=self.run_install, daemon=True).start()

    def run_install(self):
        try:
            category = self.selected_category.get()
            pack_name = self.selected_pack.get()
            
            if pack_name not in MODPACKS[category]:
                raise Exception("Invalid selection.")

            config = MODPACKS[category][pack_name]
            mc_dir = self.get_mc_dir()
            
            # --- STEP 1: AUTO-INSTALL LOADER ---
            version_id = config['version_id']
            if not self.check_loader_installed(version_id):
                self.update_status(f"Missing {version_id}. Downloading it now...")
                self.install_loader(mc_dir, config['loader_url'])
            
            # --- STEP 2: INSTALL MODPACK ---
            self.install_modpack_logic(mc_dir, config)
            
            self.root.after(0, self.reset_ui)
            self.root.after(0, lambda: self.status.config(text="Installation Complete"))
            self.root.after(0, lambda: messagebox.showinfo("Success", f"Installed '{pack_name}' successfully!"))
            
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Error", str(e)))
            self.root.after(0, self.reset_ui)
            self.root.after(0, lambda: self.status.config(text="Error occurred."))

    def check_loader_installed(self, version_id):
        mc_dir = self.get_mc_dir()
        version_path = os.path.join(mc_dir, 'versions', version_id)
        return os.path.exists(version_path)

    def install_loader(self, mc_dir, loader_url):
        versions_dir = os.path.join(mc_dir, 'versions')
        if not os.path.exists(versions_dir): os.makedirs(versions_dir)
        
        temp_loader_zip = os.path.join(versions_dir, "temp_loader.zip")
        self.progress_var.set(0)
        self.download_file(loader_url, temp_loader_zip)
        
        self.update_status("Installing Loader files...")
        with zipfile.ZipFile(temp_loader_zip, 'r') as z:
            z.extractall(versions_dir)
        os.remove(temp_loader_zip)

    def install_modpack_logic(self, mc_dir, config):
        if not os.path.exists(mc_dir): raise Exception("Minecraft not found.")
        
        profile_dir = os.path.join(mc_dir, 'profiles', config['folder_name'])
        if not os.path.exists(profile_dir): os.makedirs(profile_dir)
        
        self.update_status(f"Downloading {config['profile_name']} Mods...")
        self.progress_var.set(0)
        
        temp_zip = os.path.join(profile_dir, "temp.zip")
        self.download_file(config['url'], temp_zip)
        
        self.update_status("Extracting Mods...")
        self.progress_var.set(100)
        with zipfile.ZipFile(temp_zip, 'r') as z: z.extractall(profile_dir)
        os.remove(temp_zip)
        
        extracted_version_source = os.path.join(profile_dir, "version_data")
        if os.path.exists(extracted_version_source):
            self.update_status("Installing Loader Version...")
            main_versions_dir = os.path.join(mc_dir, "versions")
            for item in os.listdir(extracted_version_source):
                s = os.path.join(extracted_version_source, item)
                d = os.path.join(main_versions_dir, item)
                if not os.path.exists(d):
                    shutil.move(s, d)
            shutil.rmtree(extracted_version_source)

        self.update_json_profile(mc_dir, config['profile_name'], profile_dir, config['version_id'], config['icon'])

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

if __name__ == "__main__":
    root = tk.Tk()
    app = InstallerApp(root)
    root.mainloop()
