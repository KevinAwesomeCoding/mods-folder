import tkinter as tk
from tkinter import messagebox
import os
import json
import zipfile
import urllib.request
import shutil
import threading
import ctypes

# --- CONFIGURATION ---
BASE_MODS_URL = "https://github.com/KevinAwesomeCoding/mods-folder/releases/download/v1.0/mods.zip"
TARGET_FORGE_VERSION = "1.20.1-forge-47.4.10"
PROFILE_NAME = "Wonderland"

# ADD YOUR OPTIONAL MODS HERE
# Format: "Name shown to user": "Direct Download Link to .jar file"
OPTIONAL_MODS = {
    "NONE OF THESE OPTIOS WORK FOR NOW": "https://example.com/optifine.jar",
    "JourneyMap (Minimap)": "https://example.com/journeymap.jar",
    "Just Enough Items": "https://example.com/jei.jar"
}

class InstallerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Wonderland Installer")
        self.root.geometry("400x400")
        
        # Header
        tk.Label(root, text="Wonderland Installer", font=("Segoe UI", 16, "bold")).pack(pady=10)
        tk.Label(root, text="Select Optional Mods:", font=("Segoe UI", 10)).pack(anchor="w", padx=20)
        
        # Checkboxes for Optional Mods
        self.vars = {}
        for mod_name in OPTIONAL_MODS:
            var = tk.BooleanVar()
            chk = tk.Checkbutton(root, text=mod_name, variable=var, font=("Segoe UI", 10))
            chk.pack(anchor="w", padx=30)
            self.vars[mod_name] = var
            
        # Install Button
        self.btn_install = tk.Button(root, text="Install Profile", command=self.start_thread, 
                                     bg="#4CAF50", fg="white", font=("Segoe UI", 12, "bold"), height=2, width=20)
        self.btn_install.pack(pady=30)
        
        # Status Label
        self.status = tk.Label(root, text="Ready", fg="gray")
        self.status.pack(side="bottom", pady=10)

    def start_thread(self):
        self.btn_install.config(state="disabled", text="Installing...")
        threading.Thread(target=self.run_install, daemon=True).start()

    def run_install(self):
        try:
            self.install_logic()
            self.root.after(0, lambda: messagebox.showinfo("Success", "Installation Complete!\nOpen Minecraft and select 'Wonderland'."))
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
        opener = urllib.request.build_opener()
        opener.addheaders = [('User-Agent', 'Mozilla/5.0')]
        urllib.request.install_opener(opener)
        urllib.request.urlretrieve(url, path)

    def install_logic(self):
        # 1. Setup Paths
        appdata = os.getenv('APPDATA')
        if not appdata: raise Exception("APPDATA not found")
        
        mc_dir = os.path.join(appdata, '.minecraft')
        profile_dir = os.path.join(mc_dir, 'profiles', PROFILE_NAME)
        
        if not os.path.exists(profile_dir):
            os.makedirs(profile_dir)

        # 2. Download Base Mods
        self.update_status("Downloading Base Mods...")
        base_zip = os.path.join(profile_dir, "base_mods.zip")
        self.download_file(BASE_MODS_URL, base_zip)
        
        self.update_status("Extracting Base Mods...")
        with zipfile.ZipFile(base_zip, 'r') as z:
            z.extractall(profile_dir)
        os.remove(base_zip)

        # 3. Download Optional Mods
        mods_folder = os.path.join(profile_dir, "mods")
        if not os.path.exists(mods_folder):
            os.makedirs(mods_folder) # Ensure mods folder exists for optionals
            
        for mod_name, var in self.vars.items():
            if var.get():
                self.update_status(f"Downloading {mod_name}...")
                url = OPTIONAL_MODS[mod_name]
                # Extract filename from URL (e.g., "optifine.jar")
                filename = url.split("/")[-1]
                if "?" in filename: filename = filename.split("?")[0] # Clean URL params
                
                self.download_file(url, os.path.join(mods_folder, filename))

        # 4. Update Profile JSON (Smart Forge Check)
        self.update_status("Configuring Launcher...")
        versions_dir = os.path.join(mc_dir, 'versions')
        forge_dir = os.path.join(versions_dir, TARGET_FORGE_VERSION)
        
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
                raise Exception("Forge 1.20.1 not found! Install Forge first.")

        profiles_file = os.path.join(mc_dir, 'launcher_profiles.json')
        if os.path.exists(profiles_file):
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

if __name__ == "__main__":
    root = tk.Tk()
    app = InstallerApp(root)
    root.mainloop()
