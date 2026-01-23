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
import base64
import ssl
from io import BytesIO
import traceback
import argparse

# Pillow (icons + resizing)
try:
    from PIL import Image, ImageTk
    HAS_PILLOW = True
except Exception:
    HAS_PILLOW = False

# certifi (reliable CA bundle for frozen apps on macOS)
try:
    import certifi
    HAS_CERTIFI = True
except Exception:
    HAS_CERTIFI = False

# CONFIG
MODPACKS_URL = "https://raw.githubusercontent.com/KevinAwesomeCoding/mods-folder/main/modpacks.json"
LOG_PATH = os.path.join(os.getcwd(), "installer_debug.log")

def log(msg: str):
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n")
    except Exception:
        pass

def get_ssl_context():
    try:
        if HAS_CERTIFI:
            ca = certifi.where()
            os.environ["SSL_CERT_FILE"] = ca
            return ssl.create_default_context(cafile=ca)
    except Exception:
        pass
    return ssl.create_default_context()

SSL_CTX = get_ssl_context()

def http_get_bytes(url: str, timeout=15) -> bytes:
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
    })
    with urllib.request.urlopen(req, context=SSL_CTX, timeout=timeout) as r:
        return r.read()

def http_download_file(url: str, path: str, progress_cb=None, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, context=SSL_CTX, timeout=timeout) as response:
        total_size = int(response.info().get("Content-Length", 0))
        block_size = 8192
        downloaded = 0
        with open(path, "wb") as out_file:
            while True:
                chunk = response.read(block_size)
                if not chunk:
                    break
                out_file.write(chunk)
                downloaded += len(chunk)
                if progress_cb and total_size > 0:
                    progress_cb(downloaded, total_size)

class InstallerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Modpack Installer")

        self.icon_cache = {}
        self.current_icon_base64 = None

        # Center window
        window_width = 500
        window_height = 700  # Increased height slightly for the rating box
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        x = (screen_width // 2) - (window_width // 2)
        y = (screen_height // 2) - (window_height // 2)
        self.root.geometry(f"{window_width}x{window_height}+{int(x)}+{int(y)}")

        self.modpacks = self.load_data()

        # Header
        tk.Label(root, text="Select a Modpack", font=("Segoe UI", 16, "bold")).pack(pady=(15, 5))

        self.btn_refresh = tk.Button(root, text="Refresh List", command=self.refresh_data, font=("Segoe UI", 9))
        self.btn_refresh.pack(pady=5)

        # Category Dropdown
        tk.Label(root, text="Select Category:", font=("Segoe UI", 10, "bold")).pack(pady=(5, 0))
        self.selected_category = tk.StringVar()
        self.cat_dropdown = ttk.Combobox(root, textvariable=self.selected_category, state="readonly", font=("Segoe UI", 10))
        if self.modpacks:
            self.cat_dropdown["values"] = list(self.modpacks.keys())
            self.cat_dropdown.current(0)
        else:
            self.cat_dropdown["values"] = ["Error loading data"]
        self.cat_dropdown.bind("<<ComboboxSelected>>", self.update_pack_dropdown)
        self.cat_dropdown.pack(pady=5, ipadx=20)

        # Pack Dropdown
        tk.Label(root, text="Select Modpack:", font=("Segoe UI", 10)).pack(pady=(10, 0))
        self.selected_pack = tk.StringVar()
        self.pack_dropdown = ttk.Combobox(root, textvariable=self.selected_pack, state="readonly", font=("Segoe UI", 10))
        self.pack_dropdown.bind("<<ComboboxSelected>>", self.on_pack_selected)
        self.pack_dropdown.pack(pady=5, ipadx=20)

        # Icon Area
        self.icon_label = tk.Label(root, text="")
        self.icon_label.pack(pady=(10, 5))

        # Description Label
        self.desc_label = tk.Label(
            root, 
            text="Description will appear here.", 
            font=("Segoe UI", 9), 
            fg="#555555",
            wraplength=400,
            justify="center"
        )
        self.desc_label.pack(pady=(0, 5))

        # --- NEW: Rating Label ---
        # We create a Frame to hold the rating so we can add a border or background if we want later
        self.rating_frame = tk.Frame(root)
        self.rating_frame.pack(pady=(5, 10))

        self.rating_title = tk.Label(self.rating_frame, text="RATING:", font=("Segoe UI", 9, "bold"), fg="#333333")
        self.rating_title.pack(anchor="center")
        
        self.rating_text = tk.Label(
            self.rating_frame, 
            text="", 
            font=("Segoe UI", 9, "italic"), 
            fg="#E65100", # A nice burnt orange color for the rating
            wraplength=400,
            justify="center"
        )
        self.rating_text.pack(anchor="center")

        # Install Button
        self.btn_install = tk.Button(
            root, text="Install Selected Pack", command=self.start_thread,
            bg="#4CAF50", fg="white", font=("Segoe UI", 12, "bold"), height=2, width=20
        )
        self.btn_install.pack(pady=15)

        # Progress Bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(root, variable=self.progress_var, maximum=100)

        # Status Label
        self.status = tk.Label(root, text="Ready", fg="gray")
        self.status.pack(side="bottom", pady=10)

        if self.modpacks:
            self.update_pack_dropdown(None)

    def update_status(self, text):
        self.root.after(0, lambda: self.status.config(text=text))
        log(f"STATUS: {text}")

    def update_progress(self, current, total):
        percent = (current / total) * 100
        self.root.after(0, lambda: self.progress_var.set(percent))

    def load_data(self):
        try:
            fresh_url = f"{MODPACKS_URL}?t={int(time.time())}-{random.randint(1, 999999)}"
            log(f"Loading modpacks from: {fresh_url}")
            raw = http_get_bytes(fresh_url, timeout=15).decode("utf-8")
            data = json.loads(raw)
            log(f"Loaded modpacks OK. Categories: {len(data)}")
            return data
        except Exception as e:
            log("ERROR load_data: " + repr(e))
            log(traceback.format_exc())
            return {}

    def refresh_data(self):
        self.btn_refresh.config(state="disabled", text="Refreshing...")
        self.root.update_idletasks()

        def do_refresh():
            new_data = self.load_data()
            if new_data:
                self.modpacks = new_data
                self.cat_dropdown.set("")
                self.cat_dropdown["values"] = list(self.modpacks.keys())
                self.cat_dropdown.current(0)
                self.update_pack_dropdown(None)
                messagebox.showinfo("Refreshed", "Modpack list updated successfully!")
            else:
                messagebox.showwarning("Refresh Failed", f"Could not load modpacks.\nLog: {LOG_PATH}")
            
            self.btn_refresh.config(state="normal", text="Refresh List")
            self.root.update_idletasks()

        self.root.after(100, do_refresh)

    def update_pack_dropdown(self, _event):
        if not self.modpacks:
            return
        category = self.selected_category.get()
        if category in self.modpacks:
            packs = list(self.modpacks[category].keys())
            self.pack_dropdown["values"] = packs
            if packs:
                self.pack_dropdown.current(0)
                self.on_pack_selected(None)

    def on_pack_selected(self, _event):
        category = self.selected_category.get()
        pack_name = self.selected_pack.get()
        self.current_icon_base64 = None

        if category in self.modpacks and pack_name in self.modpacks[category]:
            config = self.modpacks[category][pack_name]
            
            # Update Icon
            if HAS_PILLOW and "icon_url" in config:
                self.display_icon_preview(config["icon_url"])
            else:
                self.icon_label.config(image="", text="")
            
            # Update Description
            desc_text = config.get("description", "No description available.")
            self.desc_label.config(text=desc_text)

            # --- NEW: Update Rating ---
            rating_text = config.get("rating", "").strip()
            
            if rating_text:
                # If there is a rating, show the frame and text
                self.rating_text.config(text=rating_text)
                self.rating_frame.pack(pady=(5, 10)) 
            else:
                # If no rating, hide the frame completely so there's no empty gap
                self.rating_frame.pack_forget()


    def display_icon_preview(self, url):
        if not HAS_PILLOW:
            return

        if url in self.icon_cache:
            photo = self.icon_cache[url]
            self.icon_label.config(image=photo, text="")
            return

        def fetch():
            try:
                img_data = http_get_bytes(url, timeout=15)
                image = Image.open(BytesIO(img_data))
                if getattr(image, "is_animated", False):
                    image.seek(0)
                image = image.resize((64, 64), Image.Resampling.LANCZOS)
                
                self.root.after(0, lambda: self._finish_icon_load(url, image))
            except Exception as e:
                log("ERROR preview icon: " + repr(e))
                log(traceback.format_exc())

        threading.Thread(target=fetch, daemon=True).start()

    def _finish_icon_load(self, url, image):
        try:
            photo = ImageTk.PhotoImage(image)
            self._set_preview(url, photo)
        except Exception as e:
            log(f"Error converting icon on main thread: {e}")

    def _set_preview(self, url, photo):
        self.icon_cache[url] = photo
        self.icon_label.config(image=photo, text="")

    def start_thread(self):
        if not self.modpacks:
            return
        self.btn_install.config(state="disabled", text="Installing...")
        self.progress_bar.pack(fill="x", padx=40, pady=10)
        threading.Thread(target=self.run_install, daemon=True).start()

    def reset_ui(self):
        self.btn_install.config(state="normal", text="Install Selected Pack")
        self.progress_bar.pack_forget()

    def run_install(self):
        try:
            category = self.selected_category.get()
            pack_name = self.selected_pack.get()
            config = self.modpacks[category][pack_name]
            mc_dir = self.get_mc_dir()

            download_url = config["url"]
            current_os = platform.system()
            
            if current_os == "Darwin" and "mac_url" in config:
                log(f"Detected Mac: Using mac_url for {pack_name}")
                download_url = config["mac_url"]
            elif current_os == "Windows" and "windows_url" in config:
                log(f"Detected Windows: Using windows_url for {pack_name}")
                download_url = config["windows_url"]
            
            self.update_status(f"Checking loader for {pack_name}...")
            self.install_loader(mc_dir, config["loader_url"])

            self.install_modpack_logic(mc_dir, config, download_url)

            self.root.after(0, self.reset_ui)
            self.root.after(0, lambda: self.status.config(text="Installation Complete"))
            self.root.after(0, lambda: messagebox.showinfo("Success", f"Installed '{pack_name}' successfully!"))
        except Exception as e:
            log("INSTALL ERROR: " + repr(e))
            log(traceback.format_exc())
            self.root.after(0, lambda: messagebox.showerror("Error", f"{e}\n\nLog: {LOG_PATH}"))
            self.root.after(0, self.reset_ui)

    def get_mc_dir(self):
        system = platform.system()
        if system == "Windows":
            return os.path.join(os.getenv("APPDATA"), ".minecraft")
        if system == "Darwin":
            return os.path.join(os.path.expanduser("~"), "Library", "Application Support", "minecraft")
        return os.path.join(os.path.expanduser("~"), ".minecraft")

    def install_loader(self, mc_dir, loader_url):
        version_id = loader_url.split("/")[-1].replace(".zip", "")
        versions_dir = os.path.join(mc_dir, "versions")
        version_folder = os.path.join(versions_dir, version_id)

        if os.path.exists(version_folder):
            self.update_status(f"Loader {version_id} already installed, skipping...")
            return

        libraries_dir = os.path.join(mc_dir, "libraries")
        os.makedirs(versions_dir, exist_ok=True)
        os.makedirs(libraries_dir, exist_ok=True)

        temp_loader_zip = os.path.join(mc_dir, "temp_loader.zip")
        self.progress_var.set(0)

        self.update_status("Downloading Loader...")
        http_download_file(loader_url, temp_loader_zip, progress_cb=self.update_progress, timeout=60)

        self.update_status("Installing Loader...")
        temp_extract_path = os.path.join(mc_dir, "temp_loader_extract")
        if os.path.exists(temp_extract_path):
            shutil.rmtree(temp_extract_path)
        os.makedirs(temp_extract_path, exist_ok=True)

        with zipfile.ZipFile(temp_loader_zip, "r") as z:
            z.extractall(temp_extract_path)
        os.remove(temp_loader_zip)

        found_versions = None
        found_libraries = None
        for root_path, dirs, _files in os.walk(temp_extract_path):
            if "versions" in dirs:
                found_versions = os.path.join(root_path, "versions")
            if "libraries" in dirs:
                found_libraries = os.path.join(root_path, "libraries")
            if found_versions and found_libraries:
                break

        if found_versions:
            self.merge_folders(found_versions, versions_dir)
        if found_libraries:
            self.merge_folders(found_libraries, libraries_dir)

        shutil.rmtree(temp_extract_path, ignore_errors=True)

    def merge_folders(self, src, dst):
        if sys.version_info >= (3, 8):
            shutil.copytree(src, dst, dirs_exist_ok=True)
        else:
            os.makedirs(dst, exist_ok=True)
            for item in os.listdir(src):
                s = os.path.join(src, item)
                d = os.path.join(dst, item)
                if os.path.isdir(s):
                    self.merge_folders(s, d)
                else:
                    shutil.copy2(s, d)

    def download_icon_as_base64(self, icon_url, profile_dir):
        if not HAS_PILLOW:
            return None

        icon_path = os.path.join(profile_dir, "icon.png")
        img_data = http_get_bytes(icon_url, timeout=20)

        image = Image.open(BytesIO(img_data))
        if getattr(image, "is_animated", False):
            image.seek(0)
        if image.mode != "RGBA":
            image = image.convert("RGBA")
        image = image.resize((128, 128), Image.Resampling.LANCZOS)
        image.save(icon_path, format="PNG")

        with open(icon_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("utf-8")
        return "data:image/png;base64," + b64

    def install_modpack_logic(self, mc_dir, config, download_url):
        if not os.path.exists(mc_dir):
            raise Exception("Minecraft folder not found.")

        profile_dir = os.path.join(mc_dir, "profiles", config["folder_name"])
        if os.path.exists(profile_dir):
            shutil.rmtree(profile_dir)
        os.makedirs(profile_dir, exist_ok=True)

        self.update_status(f"Downloading {config['profile_name']}...")
        self.progress_var.set(0)
        temp_zip = os.path.join(profile_dir, "temp.zip")
        
        http_download_file(download_url, temp_zip, progress_cb=self.update_progress, timeout=120)

        temp_extract = os.path.join(profile_dir, "temp_extract")
        if os.path.exists(temp_extract):
            shutil.rmtree(temp_extract)
        os.makedirs(temp_extract, exist_ok=True)

        self.update_status("Extracting mods...")
        with zipfile.ZipFile(temp_zip, "r") as z:
            z.extractall(temp_extract)
        os.remove(temp_zip)

        is_complex = config.get("is_complex", False)
        if is_complex:
            self.merge_folders(temp_extract, profile_dir)
        else:
            target_mods = os.path.join(profile_dir, "mods")
            os.makedirs(target_mods, exist_ok=True)

            found_mods_nested = None
            for root_path, dirs, _files in os.walk(temp_extract):
                if "mods" in dirs:
                    found_mods_nested = os.path.join(root_path, "mods")
                    break

            if found_mods_nested:
                self.merge_folders(found_mods_nested, target_mods)
            else:
                self.merge_folders(temp_extract, target_mods)

        shutil.rmtree(temp_extract, ignore_errors=True)

        final_icon = config.get("icon", "Furnace")
        if "icon_url" in config and HAS_PILLOW:
            self.update_status("Downloading icon...")
            try:
                b64_icon = self.download_icon_as_base64(config["icon_url"], profile_dir)
                if b64_icon:
                    final_icon = b64_icon
            except Exception as e:
                log("ERROR icon base64: " + repr(e))
                log(traceback.format_exc())

        self.update_json_profile(
            mc_dir=mc_dir,
            name=config["profile_name"],
            game_dir=profile_dir,
            version_id=config["version_id"],
            icon=final_icon
        )

    def update_json_profile(self, mc_dir, name, game_dir, version_id, icon):
        profiles_file = os.path.join(mc_dir, "launcher_profiles.json")
        if not os.path.exists(profiles_file):
            raise Exception("launcher_profiles.json not found (open Minecraft Launcher once first).")

        with open(profiles_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        if "profiles" not in data:
            data["profiles"] = {}

        profile_id = name.replace(" ", "_")
        current_time = time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime())

        data["profiles"][profile_id] = {
            "created": current_time,
            "gameDir": game_dir,
            "icon": icon,
            "lastUsed": current_time,
            "lastVersionId": version_id,
            "name": name,
            "type": "custom"
        }

        shutil.copy(profiles_file, profiles_file + ".bak")
        with open(profiles_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

def selftest():
    log("=== SELFTEST START ===")
    log(f"OS={platform.system()} {platform.release()}  PY={sys.version}")
    log(f"HAS_CERTIFI={HAS_CERTIFI}  HAS_PILLOW={HAS_PILLOW}")
    log(f"MODPACKS_URL={MODPACKS_URL}")
    try:
        raw = http_get_bytes(MODPACKS_URL, timeout=15).decode("utf-8")
        data = json.loads(raw)
        log(f"SELFTEST OK: categories={len(data)}")
        return 0
    except Exception as e:
        log("SELFTEST FAIL: " + repr(e))
        log(traceback.format_exc())
        return 1

if __name__ == "__main__":
    try:
        with open(LOG_PATH, "w", encoding="utf-8") as f:
            f.write("")
    except Exception:
        pass

    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--selftest", action="store_true")
    args, _unknown = parser.parse_known_args()

    if args.selftest:
        raise SystemExit(selftest())

    root = tk.Tk()
    app = InstallerApp(root)
    root.mainloop()
