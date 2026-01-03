import tkinter as tk
from tkinter import messagebox
import os
import json
import zipfile
import urllib.request
import shutil
import threading
import sys
import platform

# --- CONFIGURATION ---
BASE_MODS_URL = "https://github.com/KevinAwesomeCoding/mods-folder/releases/download/v1.0/mods.zip"
TARGET_FORGE_VERSION = "1.20.1-forge-47.4.10"
PROFILE_NAME = "Wonderland"

# Optional Mods Dictionary
OPTIONAL_MODS = {
    # "Optifine": "https://link-to-optifine.jar",
    # "Just Enough Items": "https://link-to-jei.jar"
}

class InstallerApp:
    def __init__(self, root):
        self.root = root
        self.root.title(f"{PROFILE_NAME} Installer")
        self.root.geometry("400x450")
        
        # UI Setup
        tk.Label(root, text=f"{PROFILE_NAME} Installer", font=("Segoe UI", 16, "bold")).pack(pady=10)
        
        tk.Label(root, text="Select Optional Mods:", font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=20, pady=(10,0))
        
        self.vars = {}
        if not OPTIONAL_MODS:
            tk.Label(root, text="(No optional mods available)", fg="gray").pack(anchor="w", padx=30)
        else:
            for mod_name in OPTIONAL_MODS:
                var = tk.BooleanVar()
                chk = tk.Checkbutton(root, text=mod_name, variable=var, font=("Segoe UI", 10))
                chk.pack(anchor="w", padx=30)
                self.vars[mod_name] = var
            
        self.btn_install = tk.Button(root, text="Install Profile", command=self.start_thread, 
                                     bg="#4CAF50", fg="white", font=("Segoe UI", 12, "bold"), height=2, width=20)
        self.btn_install.pack(pady=30)
        
        self.status = tk.Label(root, text="Ready", fg="gray")
        self.status.pack(side="bottom", pady=10)

    def start_thread(self):
        self.btn_install.config(state="disabled", text="Installing...")
        threading.Thread(target=self.run_install, daemon=True).start()

    def run_install(self):
        try:
            self.install_logic()
            self.root.after(0, lambda: messagebox.showinfo("Success", f"Installation Complete!\nOpen Minecraft and select '{PROFILE_NAME}'."))
            self.root.after(0, self.root.quit)
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Error", str(e)))
            self.root.after(0, lambda: self.reset_ui())

    def reset_ui(self):
        self.btn_install.config(state="normal", text="Install Profile")
        self.status.config(text="Error occurred.")

    def update_status(self, text):
        self.root.after(0, lambda: self.status.config(text=text))

    def download_file(self, url, path):
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response, open(path, 'wb') as out_file:
            shutil.copyfileobj(response, out_file)

    def install_logic(self):
        # 1. Setup Paths (Cross-Platform)
        system = platform.system()
        if system == 'Windows':
            appdata = os.getenv('APPDATA')
            mc_dir = os.path.join(appdata, '.minecraft')
        elif system == 'Darwin': # MacOS
            home = os.path.expanduser("~")
            mc_dir = os.path.join(home, "Library", "Application Support", "minecraft")
        else: # Linux
            home = os.path.expanduser("~")
            mc_dir = os.path.join(home, ".minecraft")

        if not os.path.exists(mc_dir):
            raise Exception(f"Minecraft folder not found at:\n{mc_dir}\nPlease launch Minecraft once.")

        profile_dir = os.path.join(mc_dir, 'profiles', PROFILE_NAME)
        if not os.path.exists(profile_dir):
            os.makedirs(profile_dir)

        # 2. Download Base Mods
        self.update_status("Downloading Base Mods...")
        base_zip = os.path.join(profile_dir, "base_mods.zip")
        self.download_file(BASE_MODS_URL, base_zip)
        
        self.update_status("Extracting Mods...")
        with zipfile.ZipFile(base_zip, 'r') as z:
            z.extractall(profile_dir)
        os.remove(base_zip)

        # 3. Download Optional Mods
        mods_folder = os.path.join(profile_dir, "mods")
        if not os.path.exists(mods_folder):
            os.makedirs(mods_folder)
            
        for mod_name, var in self.vars.items():
            if var.get():
                self.update_status(f"Downloading {mod_name}...")
                url = OPTIONAL_MODS[mod_name]
                filename = url.split("/")[-1].split("?")[0]
                self.download_file(url, os.path.join(mods_folder, filename))

        # 4. Update Profile JSON
        self.update_status("Configuring Launcher...")
        versions_dir = os.path.join(mc_dir, 'versions')
        forge_dir = os.path.join(versions_dir, TARGET_FORGE_VERSION)
        
        # Smart Search for Forge Version
        final_version = TARGET_FORGE_VERSION
        if not os.path.exists(forge_dir):
            found = False
            if os.path.exists(versions_dir):
                for f in os.listdir(versions_dir):
                    if f.startswith("1.20.1-forge"):
                        final_version = f
                        found = True
                        break
            if not found:
                # Warning only - proceed so they can install Forge later
                self.root.after(0, lambda: messagebox.showwarning("Warning", "Forge 1.20.1 not found!\nPlease install Forge manually."))

        profiles_file = os.path.join(mc_dir, 'launcher_profiles.json')
        if os.path.exists(profiles_file):
            try:
                with open(profiles_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                data['profiles'][PROFILE_NAME] = {
                    "name": PROFILE_NAME,
                    "type": "custom",
                    "created": "2025-01-01T00:00:00.000Z",
                    "lastVersionId": final_version,
                    "icon": "Furnace",
                    "gameDir": profile_dir
                }
                
                shutil.copy(profiles_file, profiles_file + ".bak")
                with open(profiles_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2)
            except Exception as e:
                raise Exception(f"Failed to update profile: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = InstallerApp(root)
    root.mainloop()
