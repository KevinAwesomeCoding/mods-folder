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

def load_modpacks():
    try:
        # Try to load from the same directory as the script
        script_dir = os.path.dirname(os.path.abspath(__file__))
        modpacks_file = os.path.join(script_dir, 'modpacks.json')
        
        with open(modpacks_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        messagebox.showerror("Error", "modpacks.json file not found!\nPlease place it in the same folder as the installer.")
        sys.exit(1)
    except json.JSONDecodeError as e:
        messagebox.showerror("Error", f"Invalid JSON in modpacks.json:\n{e}")
        sys.exit(1)

MODPACKS = load_modpacks()


class InstallerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Modpack Installer")
        self.root.geometry("400x480")
        
        # Header
        tk.Label(root, text="Select a Modpack", font =("Segoe UI", 16, "bold")).pack(pady=15)
        
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

        # Initialize Dropdown Logic
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
            
            # --- STEP 1: INSTALL LOADER (Versions/Libraries) ---
            self.update_status(f"Checking loader for {pack_name}...")
            self.install_loader(mc_dir, config['loader_url'])
            
            # --- STEP 2: INSTALL MODPACK ---
            self.install_modpack_logic(mc_dir, config)
            
            # Success UI Updates
            self.root.after(0, self.reset_ui)
            self.root.after(0, lambda: self.status.config(text="Installation Complete"))
            self.root.after(0, lambda: messagebox.showinfo("Success", f"Installed '{pack_name}' successfully!"))
            
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Error", str(e)))
            self.root.after(0, self.reset_ui)
            self.root.after(0, lambda: self.status.config(text="Error occurred."))

    def install_loader(self, mc_dir, loader_url):
        versions_dir = os.path.join(mc_dir, 'versions')
        libraries_dir = os.path.join(mc_dir, 'libraries')
        
        if not os.path.exists(versions_dir): os.makedirs(versions_dir)
        if not os.path.exists(libraries_dir): os.makedirs(libraries_dir)
        
        temp_loader_zip = os.path.join(mc_dir, "temp_loader.zip")
        self.progress_var.set(0)
        
        self.update_status("Downloading Loader...")
        self.download_file(loader_url, temp_loader_zip)
        
        self.update_status("Installing Loader...")
        
        # Extract to a temp folder
        temp_extract_path = os.path.join(mc_dir, "temp_loader_extract")
        if os.path.exists(temp_extract_path): shutil.rmtree(temp_extract_path)
        os.makedirs(temp_extract_path)

        with zipfile.ZipFile(temp_loader_zip, 'r') as z:
            z.extractall(temp_extract_path)
            
        os.remove(temp_loader_zip)

        # --- FIND FOLDERS RECURSIVELY (The "Search and Destroy" Fix) ---
        found_versions = None
        found_libraries = None

        for root_path, dirs, files in os.walk(temp_extract_path):
            if "versions" in dirs:
                found_versions = os.path.join(root_path, "versions")
            if "libraries" in dirs:
                found_libraries = os.path.join(root_path, "libraries")
            
            # Stop if we found both to save time
            if found_versions and found_libraries:
                break

        # --- MERGE WITH OVERWRITE LOGIC ---
        if found_versions:
            self.update_status("Copying version files...")
            self.merge_folders_robust(found_versions, versions_dir)
        else:
            print("Warning: 'versions' folder not found in loader zip.")

        if found_libraries:
            self.update_status("Copying library files...")
            self.merge_folders_robust(found_libraries, libraries_dir)
        else:
            # Fallback: Maybe the zip IS the version folder? 
            # (Unlikely based on your description, but good safety)
            pass

        # Cleanup
        shutil.rmtree(temp_extract_path)

    def merge_folders_robust(self, src, dst):
        """
        Robustly merges src into dst.
        If dst exists, it merges contents.
        If files exist, it overwrites them (ensuring updates).
        """
        # Try using modern Python shutil.copytree if available
        if sys.version_info >= (3, 8):
            shutil.copytree(src, dst, dirs_exist_ok=True)
        else:
            # Manual fallback for older Python
            if not os.path.exists(dst):
                os.makedirs(dst)
            for item in os.listdir(src):
                s = os.path.join(src, item)
                d = os.path.join(dst, item)
                if os.path.isdir(s):
                    self.merge_folders_robust(s, d)
                else:
                    # Always copy, replacing existing files to ensure updates
                    try:
                        shutil.copy2(s, d)
                    except Exception as e:
                        print(f"Could not copy {s}: {e}")

    def install_modpack_logic(self, mc_dir, config):
        if not os.path.exists(mc_dir): raise Exception("Minecraft not found.")
        
        # 1. Prepare Main Profile Folder
        profile_dir = os.path.join(mc_dir, 'profiles', config['folder_name'])
        if not os.path.exists(profile_dir): os.makedirs(profile_dir)
        
        is_complex = config.get('is_complex', False)
        
        # 2. Download Modpack
        self.update_status(f"Downloading {config['profile_name']}...")
        self.progress_var.set(0)
        temp_zip = os.path.join(profile_dir, "temp.zip")
        self.download_file(config['url'], temp_zip)
        
        # 3. Extract to temp location first
        temp_extract = os.path.join(profile_dir, "temp_extract_mods")
        if os.path.exists(temp_extract): shutil.rmtree(temp_extract)
        os.makedirs(temp_extract)
        
        self.update_status("Extracting mods...")
        self.progress_var.set(100)
        with zipfile.ZipFile(temp_zip, 'r') as z:
            z.extractall(temp_extract)
        os.remove(temp_zip)

        # 4. Smart Install Logic (Mods)
        if is_complex:
            self.merge_folders_robust(temp_extract, profile_dir)
        else:
            target_mods = os.path.join(profile_dir, "mods")
            if not os.path.exists(target_mods): os.makedirs(target_mods)
            
            # Check for nested 'mods' folder
            found_mods_nested = None
            for root_path, dirs, files in os.walk(temp_extract):
                if "mods" in dirs:
                    found_mods_nested = os.path.join(root_path, "mods")
                    break
            
            if found_mods_nested:
                # Found a nested 'mods' folder, move its CONTENTS
                self.merge_folders_robust(found_mods_nested, target_mods)
            else:
                # No nested 'mods' folder, assume all jars in temp are mods
                self.merge_folders_robust(temp_extract, target_mods)

        # Cleanup
        if os.path.exists(temp_extract): shutil.rmtree(temp_extract)
        
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
