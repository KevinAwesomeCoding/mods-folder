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
from io import BytesIO

# Try to import Pillow for image handling
try:
    from PIL import Image, ImageTk
    HAS_PILLOW = True
except ImportError:
    HAS_PILLOW = False
    print("Warning: Pillow not installed. Icons will not display in the app.")
    print("Run: pip install pillow")

# CONFIG
MODPACKS_URL = "https://raw.githubusercontent.com/KevinAwesomeCoding/mods-folder/refs/heads/main/modpacks.json" 

class InstallerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Modpack Installer")
        
        # Cache for loaded icons (for UI preview only)
        self.icon_cache = {}
        self.current_icon_path = None

        # --- CENTER THE WINDOW ---
        window_width = 450 
        window_height = 600
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        
        x = (screen_width // 2) - (window_width // 2)
        y = (screen_height // 2) - (window_height // 2)
        
        self.root.geometry(f"{window_width}x{window_height}+{int(x)}+{int(y)}")

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
        self.pack_dropdown.bind("<<ComboboxSelected>>", self.on_pack_selected)
        self.pack_dropdown.pack(pady=5, ipadx=20)
        
        # --- ICON PREVIEW ---
        self.icon_label = tk.Label(root, text="")
        self.icon_label.pack(pady=10)

        # Install Button
        self.btn_install = tk.Button(root, text="Install Selected Pack", command=self.start_thread, 
                                     bg="#4CAF50", fg="white", font=("Segoe UI", 12, "bold"), height=2, width=20)
        self.btn_install.pack(pady=15)
        
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
            print(f"Error loading data: {e}")
            return {}

    def refresh_data(self):
        self.btn_refresh.config(state="disabled", text="Refreshing...")
        self.root.update_idletasks()
        
        new_data = self.load_data()
        
        if new_data:
            self.modpacks = new_data
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
                self.on_pack_selected(None) 
            else:
                self.pack_dropdown.set("No packs")
                self.btn_install.config(state="disabled")
                self.icon_label.config(image='', text="No Icon")

    def on_pack_selected(self, event):
        category = self.selected_category.get()
        pack_name = self.selected_pack.get()
        
        if category in self.modpacks and pack_name in self.modpacks[category]:
            self.btn_install.config(state="normal")
            config = self.modpacks[category][pack_name]
            
            # Reset icon path
            self.current_icon_path = None
            
            # Display preview in UI
            if 'icon_url' in config and HAS_PILLOW:
                self.display_icon_preview(config['icon_url'])
            else:
                self.icon_label.config(image='', text="")

    def display_icon_preview(self, url):
        """Downloads icon for UI preview only (non-blocking)."""
        if url in self.icon_cache:
            photo = self.icon_cache[url]
            self.icon_label.config(image=photo, text="")
            return

        def fetch():
            try:
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req) as response:
                    img_data = response.read()
                
                image = Image.open(BytesIO(img_data))
                if getattr(image, "is_animated", False):
                    image.seek(0)
                
                image = image.resize((64, 64), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(image)
                
                self.root.after(0, lambda: self._update_icon_preview(url, photo))
            except Exception as e:
                print(f"Icon preview error: {e}")

        threading.Thread(target=fetch, daemon=True).start()

    def _update_icon_preview(self, url, photo):
        self.icon_cache[url] = photo
        self.icon_label.config(image=photo, text="")

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
            print(f"Full error: {e}")

    def install_loader(self, mc_dir, loader_url):
        version_id = loader_url.split('/')[-1].replace('.zip', '')
        versions_dir = os.path.join(mc_dir, 'versions')
        version_folder = os.path.join(versions_dir, version_id)
        
        if os.path.exists(version_folder):
            self.update_status(f"Loader {version_id} already installed, skipping...")
            return
        
        libraries_dir = os.path.join(mc_dir, 'libraries')
        if not os.path.exists(versions_dir): os.makedirs(versions_dir)
        if not os.path.exists(libraries_dir): os.makedirs(libraries_dir)
        
        temp_loader_zip = os.path.join(mc_dir, "temp_loader.zip")
        self.progress_var.set(0)
        
        self.update_status("Downloading Loader...")
        self.download_file(loader_url, temp_loader_zip)
        
        self.update_status("Installing Loader...")
        temp_extract_path = os.path.join(mc_dir, "temp_loader_extract")
        if os.path.exists(temp_extract_path): shutil.rmtree(temp_extract_path)
        os.makedirs(temp_extract_path)

        with zipfile.ZipFile(temp_loader_zip, 'r') as z:
            z.extractall(temp_extract_path)
        os.remove(temp_loader_zip)

        found_versions = None
        found_libraries = None

        for root_path, dirs, files in os.walk(temp_extract_path):
            if "versions" in dirs: found_versions = os.path.join(root_path, "versions")
            if "libraries" in dirs: found_libraries = os.path.join(root_path, "libraries")
            if found_versions and found_libraries: break

        if found_versions:
            self.merge_folders_robust(found_versions, versions_dir)
        
        if found_libraries:
            self.merge_folders_robust(found_libraries, libraries_dir)

        shutil.rmtree(temp_extract_path)

    def merge_folders_robust(self, src, dst):
        if sys.version_info >= (3, 8):
            shutil.copytree(src, dst, dirs_exist_ok=True)
        else:
            if not os.path.exists(dst): os.makedirs(dst)
            for item in os.listdir(src):
                s = os.path.join(src, item)
                d = os.path.join(dst, item)
                if os.path.isdir(s):
                    self.merge_folders_robust(s, d)
                else:
                    try: shutil.copy2(s, d)
                    except: pass

    def download_icon_file(self, icon_url, profile_dir):
        """Downloads the icon, resizes it to 128x128, and saves it to profile_dir/icon.png. Returns the file path."""
        if not HAS_PILLOW:
            print("Pillow not installed, skipping icon download")
            return None
            
        try:
            print(f"Attempting to download icon from: {icon_url}")
            
            icon_path = os.path.join(profile_dir, "icon.png")
            
            req = urllib.request.Request(icon_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=10) as response:
                img_data = response.read()
            
            print(f"Downloaded {len(img_data)} bytes")
            
            # Open the image with Pillow
            image = Image.open(BytesIO(img_data))
            
            # If it's an animated GIF, grab the first frame
            if getattr(image, "is_animated", False):
                image.seek(0)
            
            # Convert to RGBA if needed (handles transparency)
            if image.mode != 'RGBA':
                image = image.convert('RGBA')
            
            # Resize to EXACTLY 128x128 (required by Minecraft Launcher)
            image = image.resize((128, 128), Image.Resampling.LANCZOS)
            
            # Save as PNG
            image.save(icon_path, format="PNG")
            
            print(f"✓ Icon saved to: {icon_path} (128x128)")
            
            # Verify the file exists
            if os.path.exists(icon_path):
                print(f"✓ Verified: Icon file exists at {icon_path}")
                return icon_path
            else:
                print("ERROR: Icon file was not created!")
                return None
                
        except Exception as e:
            print(f"Icon download/resize failed: {e}")
            import traceback
            traceback.print_exc()
            return None

    def install_modpack_logic(self, mc_dir, config):
        if not os.path.exists(mc_dir): raise Exception("Minecraft not found.")
        profile_dir = os.path.join(mc_dir, 'profiles', config['folder_name'])
        
        if os.path.exists(profile_dir):
            shutil.rmtree(profile_dir)
        os.makedirs(profile_dir)
        
        is_complex = config.get('is_complex', False)
        
        self.update_status(f"Downloading {config['profile_name']}...")
        self.progress_var.set(0)
        temp_zip = os.path.join(profile_dir, "temp.zip")
        self.download_file(config['url'], temp_zip)
        
        temp_extract = os.path.join(profile_dir, "temp_extract_mods")
        if os.path.exists(temp_extract): shutil.rmtree(temp_extract)
        os.makedirs(temp_extract)
        
        self.update_status("Extracting mods...")
        self.progress_var.set(100)
        with zipfile.ZipFile(temp_zip, 'r') as z:
            z.extractall(temp_extract)
        os.remove(temp_zip)

        if is_complex:
            self.merge_folders_robust(temp_extract, profile_dir)
        else:
            target_mods = os.path.join(profile_dir, "mods")
            if not os.path.exists(target_mods): os.makedirs(target_mods)
            
            found_mods_nested = None
            for root_path, dirs, files in os.walk(temp_extract):
                if "mods" in dirs:
                    found_mods_nested = os.path.join(root_path, "mods")
                    break
            
            if found_mods_nested:
                self.merge_folders_robust(found_mods_nested, target_mods)
            else:
                self.merge_folders_robust(temp_extract, target_mods)

        if os.path.exists(temp_extract): shutil.rmtree(temp_extract)
        
        # --- DOWNLOAD ICON TO PROFILE FOLDER (128x128) ---
        print(f"Profile folder is: {profile_dir}")
        print(f"Profile folder exists: {os.path.exists(profile_dir)}")
        
        final_icon = config.get('icon', "Furnace")
        if 'icon_url' in config:
            self.update_status("Downloading icon...")
            downloaded_icon_path = self.download_icon_file(config['icon_url'], profile_dir)
            if downloaded_icon_path:
                print(f"Using custom icon: {downloaded_icon_path}")
                final_icon = downloaded_icon_path
            else:
                print("Icon download failed, using fallback")
        
        self.update_json_profile(mc_dir, config['profile_name'], profile_dir, config['version_id'], final_icon)

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
        current_time = time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime())
        
        print(f"Writing profile with icon: {icon}")
        
        data['profiles'][profile_id] = {
            "created": current_time,
            "gameDir": game_dir,
            "icon": icon,
            "lastUsed": current_time,
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
