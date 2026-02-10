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

# --- DARK THEME COLORS ---
BG_COLOR = "#2E2E2E"
FG_COLOR = "#FFFFFF"
ACCENT_COLOR = "#007ACC"
BUTTON_BG = "#3E3E3E"
BUTTON_FG = "#FFFFFF"
BUTTON_ACTIVE = "#505050"
ENTRY_BG = "#404040"
ENTRY_FG = "#FFFFFF"
FRAME_BG = "#2E2E2E"


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
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        },
    )
    with urllib.request.urlopen(req, context=SSL_CTX, timeout=timeout) as r:
        return r.read()


def http_download_file(url: str, path: str, progress_cb=None, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, context=SSL_CTX, timeout=timeout) as response:
        total_size = int(response.info().get("Content-Length", 0))
        block_size = 8192
        downloaded = 0

        start_time = time.time()
        last_update_time = 0

        with open(path, "wb") as out_file:
            while True:
                chunk = response.read(block_size)
                if not chunk:
                    break
                out_file.write(chunk)
                downloaded += len(chunk)

                # Update UI only every 0.1s to prevent lag
                current_time = time.time()
                if (
                    progress_cb
                    and total_size > 0
                    and (current_time - last_update_time > 0.1)
                ):
                    elapsed_time = current_time - start_time
                    if elapsed_time > 0:
                        speed = downloaded / elapsed_time
                        remaining_bytes = total_size - downloaded
                        eta_seconds = remaining_bytes / speed if speed > 0 else 0
                    else:
                        eta_seconds = 0
                    progress_cb(downloaded, total_size, eta_seconds)
                    last_update_time = current_time

            # Ensure final update hits 100%
            if progress_cb and total_size > 0:
                progress_cb(total_size, total_size, 0)


class InstallerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Modpack Installer")
        self.root.configure(bg=BG_COLOR)

        self.icon_cache = {}
        self.current_icon_base64 = None
        self.current_action_name = "Processing"

        # Center window
        window_width = 500
        window_height = 750
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        x = (screen_width // 2) - (window_width // 2)
        y = (screen_height // 2) - (window_height // 2)
        self.root.geometry(f"{window_width}x{window_height}+{int(x)}+{int(y)}")

        # Configure Dark Theme Styles
        style = ttk.Style()
        style.theme_use("clam")  # 'clam' allows for better color customization

        style.configure(
            "TLabel",
            background=BG_COLOR,
            foreground=FG_COLOR,
            font=("Segoe UI", 10),
        )
        style.configure(
            "TButton",
            background=BUTTON_BG,
            foreground=BUTTON_FG,
            borderwidth=1,
            font=("Segoe UI", 10),
        )
        style.map("TButton", background=[("active", BUTTON_ACTIVE)])

        style.configure(
            "TCombobox",
            fieldbackground=ENTRY_BG,
            background=BUTTON_BG,
            foreground=FG_COLOR,
            arrowcolor=FG_COLOR,
        )
        style.map(
            "TCombobox",
            fieldbackground=[("readonly", ENTRY_BG)],
            selectbackground=[("readonly", ACCENT_COLOR)],
        )

        style.configure(
            "Horizontal.TProgressbar",
            background=ACCENT_COLOR,
            troughcolor=BUTTON_BG,
            bordercolor=BG_COLOR,
            lightcolor=ACCENT_COLOR,
            darkcolor=ACCENT_COLOR,
        )

        self.modpacks = self.load_data()

        # --- DEBUG ICON (Top Right) ---
        self.btn_debug = tk.Button(
            root,
            text="⚙",
            font=("Segoe UI", 12),
            command=self.open_debug_menu,
            bg=BG_COLOR,
            fg=FG_COLOR,
            activebackground=BUTTON_ACTIVE,
            activeforeground=FG_COLOR,
            bd=0,
            highlightthickness=0,
        )
        self.btn_debug.place(relx=0.92, rely=0.02)

        # Header
        tk.Label(
            root,
            text="Select a Modpack",
            font=("Segoe UI", 18, "bold"),
            bg=BG_COLOR,
            fg=FG_COLOR,
        ).pack(pady=(20, 10))

        self.btn_refresh = tk.Button(
            root,
            text="Refresh List",
            command=self.refresh_data,
            font=("Segoe UI", 9),
            bg=BUTTON_BG,
            fg=BUTTON_FG,
            activebackground=BUTTON_ACTIVE,
            activeforeground=BUTTON_FG,
            bd=1,
            relief="flat",
        )
        self.btn_refresh.pack(pady=5)

        # Main Content Frame
        content_frame = tk.Frame(root, bg=BG_COLOR)
        content_frame.pack(fill="both", expand=True, padx=20)

        # Category Dropdown
        tk.Label(
            content_frame,
            text="CATEGORY",
            font=("Segoe UI", 9, "bold"),
            bg=BG_COLOR,
            fg="#AAAAAA",
        ).pack(pady=(15, 2), anchor="w")
        self.selected_category = tk.StringVar()
        self.cat_dropdown = ttk.Combobox(
            content_frame,
            textvariable=self.selected_category,
            state="readonly",
            font=("Segoe UI", 11),
        )
        if self.modpacks:
            self.cat_dropdown["values"] = list(self.modpacks.keys())
            self.cat_dropdown.current(0)
        else:
            self.cat_dropdown["values"] = ["Error loading data"]
        self.cat_dropdown.bind("<<ComboboxSelected>>", self.update_pack_dropdown)
        self.cat_dropdown.pack(pady=5, fill="x")

        # Pack Dropdown
        tk.Label(
            content_frame,
            text="MODPACK",
            font=("Segoe UI", 9, "bold"),
            bg=BG_COLOR,
            fg="#AAAAAA",
        ).pack(pady=(15, 2), anchor="w")
        self.selected_pack = tk.StringVar()
        self.pack_dropdown = ttk.Combobox(
            content_frame,
            textvariable=self.selected_pack,
            state="readonly",
            font=("Segoe UI", 11),
        )
        self.pack_dropdown.bind("<<ComboboxSelected>>", self.on_pack_selected)
        self.pack_dropdown.pack(pady=5, fill="x")

        # Icon Area
        self.icon_frame = tk.Frame(content_frame, bg=BG_COLOR, height=80)
        self.icon_frame.pack(pady=(20, 10))
        self.icon_label = tk.Label(self.icon_frame, text="", bg=BG_COLOR)
        self.icon_label.pack()

        # Description Label
        self.desc_label = tk.Label(
            content_frame,
            text="Description will appear here.",
            font=("Segoe UI", 10),
            fg="#CCCCCC",
            bg=BG_COLOR,
            wraplength=400,
            justify="center",
        )
        self.desc_label.pack(pady=(0, 10))

        # Rating Frame
        self.rating_frame = tk.Frame(content_frame, bg=BG_COLOR)
        self.rating_frame.pack(pady=(5, 15))

        self.rating_title = tk.Label(
            self.rating_frame,
            text="RATING",
            font=("Segoe UI", 8, "bold"),
            fg="#888888",
            bg=BG_COLOR,
        )
        self.rating_title.pack(anchor="center")

        self.rating_text = tk.Label(
            self.rating_frame,
            text="",
            font=("Segoe UI", 10, "bold"),
            fg="#FFD700",
            bg=BG_COLOR,
            wraplength=400,
            justify="center",
        )
        self.rating_text.pack(anchor="center")

        # Install Button
        self.btn_install = tk.Button(
            root,
            text="INSTALL SELECTED PACK",
            command=self.start_thread,
            bg=ACCENT_COLOR,
            fg="white",
            font=("Segoe UI", 11, "bold"),
            activebackground="#005A9E",
            activeforeground="white",
            bd=0,
            relief="flat",
            height=2,
        )
        self.btn_install.pack(pady=20, fill="x", padx=40)

        # Progress Bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            root,
            variable=self.progress_var,
            maximum=100,
            style="Horizontal.TProgressbar",
        )

        # Status Label
        self.status = tk.Label(
            root,
            text="Ready",
            fg="#888888",
            bg=BG_COLOR,
            font=("Segoe UI", 9),
        )
        self.status.pack(side="bottom", pady=15)

        if self.modpacks:
            self.update_pack_dropdown(None)

    # --- DEBUG MENU LOGIC ---
    def open_debug_menu(self):
        debug_win = tk.Toplevel(self.root)
        debug_win.title("Debug / Tools")
        debug_win.geometry("350x300")
        debug_win.configure(bg=BG_COLOR)

        tk.Label(
            debug_win,
            text="Maintenance Tools",
            font=("Segoe UI", 12, "bold"),
            bg=BG_COLOR,
            fg=FG_COLOR,
        ).pack(pady=15)

        # Button 1: Update Launcher Profiles (JSON only)
        btn_update_json = tk.Button(
            debug_win,
            text="Update Launcher Profiles (JSON)",
            command=lambda: self.debug_update_profiles(debug_win),
            bg=BUTTON_BG,
            fg=BUTTON_FG,
            activebackground=BUTTON_ACTIVE,
            activeforeground=BUTTON_FG,
            relief="flat",
            font=("Segoe UI", 10),
        )
        btn_update_json.pack(pady=5, fill="x", padx=30, ipady=5)

        # Button 2: Update Mods
        tk.Label(
            debug_win,
            text="Update Installed Mods:",
            font=("Segoe UI", 10),
            bg=BG_COLOR,
            fg="#AAAAAA",
        ).pack(pady=(20, 5))

        # Get installed packs by looking at profiles folder
        mc_dir = self.get_mc_dir()
        profiles_dir = os.path.join(mc_dir, "profiles")
        installed_packs = ["All"]
        if os.path.exists(profiles_dir):
            for item in os.listdir(profiles_dir):
                if os.path.isdir(os.path.join(profiles_dir, item)):
                    installed_packs.append(item)

        pack_var = tk.StringVar()
        pack_dropdown = ttk.Combobox(
            debug_win,
            textvariable=pack_var,
            values=installed_packs,
            state="readonly",
            font=("Segoe UI", 10),
        )
        if installed_packs:
            pack_dropdown.current(0)
        pack_dropdown.pack(pady=5, padx=30, fill="x")

        btn_update_mods = tk.Button(
            debug_win,
            text="Update Selected Mods",
            command=lambda: self.debug_update_mods(pack_var.get(), debug_win),
            bg=ACCENT_COLOR,
            fg="white",
            activebackground="#005A9E",
            activeforeground="white",
            relief="flat",
            font=("Segoe UI", 10, "bold"),
        )
        btn_update_mods.pack(pady=10, fill="x", padx=30, ipady=5)

    def debug_update_profiles(self, window):
        threading.Thread(
            target=self._debug_update_profiles_thread, args=(window,), daemon=True
        ).start()

    def _debug_update_profiles_thread(self, window):
        mc_dir = self.get_mc_dir()
        log("DEBUG: Updating profiles JSON...")
        count = 0
        try:
            all_configs = {}
            for cat in self.modpacks:
                for pack_name, cfg in self.modpacks[cat].items():
                    all_configs[cfg["folder_name"]] = cfg

            profiles_dir = os.path.join(mc_dir, "profiles")
            if os.path.exists(profiles_dir):
                for folder in os.listdir(profiles_dir):
                    if folder in all_configs:
                        cfg = all_configs[folder]

                        final_icon = cfg.get("icon", "Furnace")
                        if "icon_url" in cfg and HAS_PILLOW:
                            try:
                                b64 = self.download_icon_as_base64(
                                    cfg["icon_url"],
                                    os.path.join(profiles_dir, folder),
                                )
                                if b64:
                                    final_icon = b64
                            except Exception:
                                pass

                        default_args = (
                            "-Xmx4096m -Xms256m "
                            "-Dfml.ignorePatchDiscrepancies=true "
                            "-Dfml.ignoreInvalidMinecraftCertificates=true "
                            "-Duser.language=en -Duser.country=US"
                        )
                        jvm_args = cfg.get("jvm_args", default_args)

                        self.update_json_profile(
                            mc_dir=mc_dir,
                            name=cfg["profile_name"],
                            game_dir=os.path.join(profiles_dir, folder),
                            version_id=cfg["version_id"],
                            icon=final_icon,
                            jvm_args=jvm_args,
                        )
                        count += 1

            messagebox.showinfo(
                "Debug", f"Updated {count} profiles in launcher_profiles.json"
            )
            window.destroy()
        except Exception as e:
            log(f"DEBUG ERROR: {e}")
            messagebox.showerror("Error", str(e))

    def debug_update_mods(self, selection, window):
        if not selection:
            return
        window.destroy()
        threading.Thread(
            target=self._debug_update_mods_thread, args=(selection,), daemon=True
        ).start()

    def _debug_update_mods_thread(self, selection):
        self.btn_install.config(state="disabled")
        self.progress_bar.pack(fill="x", padx=40, pady=10)

        mc_dir = self.get_mc_dir()

        all_configs = {}
        for cat in self.modpacks:
            for pname, cfg in self.modpacks[cat].items():
                all_configs[cfg["folder_name"]] = cfg

        targets = []
        if selection == "All":
            profiles_dir = os.path.join(mc_dir, "profiles")
            if os.path.exists(profiles_dir):
                for folder in os.listdir(profiles_dir):
                    if folder in all_configs:
                        targets.append(all_configs[folder])
        else:
            if selection in all_configs:
                targets.append(all_configs[selection])

        if not targets:
            messagebox.showinfo("Info", "No matching modpacks found to update.")
            self.reset_ui()
            return

        for i, config in enumerate(targets):
            self.update_status(
                f"Updating {config['profile_name']} ({i+1}/{len(targets)})..."
            )
            try:
                download_url = config["url"]
                if platform.system() == "Darwin" and "mac_url" in config:
                    download_url = config["mac_url"]
                elif platform.system() == "Windows" and "windows_url" in config:
                    download_url = config["windows_url"]

                # Use the same logic as normal: detect existing profile and update
                self.install_modpack_logic(mc_dir, config, download_url)
            except Exception as e:
                log(f"Failed to update {config['profile_name']}: {e}")

        self.update_status("Update Complete!")
        messagebox.showinfo("Success", "Selected modpacks have been updated.")
        self.reset_ui()

    def update_status(self, text):
        self.root.after(0, lambda: self.status.config(text=text))
        log(f"STATUS: {text}")

    def update_progress(self, current, total, eta_seconds=0):
        if total <= 0:
            return
        percent = (current / total) * 100
        self.root.after(0, lambda: self.progress_var.set(percent))

        if eta_seconds < 60:
            time_str = f"{int(eta_seconds)}s"
        else:
            time_str = f"{int(eta_seconds // 60)}m {int(eta_seconds % 60)}s"

        status_text = f"{self.current_action_name}... {int(percent)}% ({time_str} left)"
        self.root.after(0, lambda: self.status.config(text=status_text))

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
                messagebox.showwarning(
                    "Refresh Failed", f"Could not load modpacks.\nLog: {LOG_PATH}"
                )

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

            if HAS_PILLOW and "icon_url" in config:
                self.display_icon_preview(config["icon_url"])
            else:
                self.icon_label.config(image="", text="")

            desc_text = config.get("description", "No description available.")
            self.desc_label.config(text=desc_text)

            rating_text = config.get("rating", "").strip()
            if rating_text:
                self.rating_text.config(text=rating_text)
                self.rating_frame.pack(pady=(5, 10))
            else:
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
                self.root.after(
                    0,
                    lambda: self._finish_icon_load(url, image),
                )
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
        self.btn_install.config(state="disabled", text="INSTALLING...", bg="#555555")
        self.progress_bar.pack(fill="x", padx=40, pady=10)
        threading.Thread(target=self.run_install, daemon=True).start()

    def reset_ui(self):
        self.btn_install.config(
            state="normal", text="INSTALL SELECTED PACK", bg=ACCENT_COLOR
        )
        self.progress_bar.pack_forget()

    def copy_options_template(self, profile_dir):
        template_name = "base_options.txt"
        template_path = os.path.join(os.getcwd(), template_name)

        if not os.path.exists(template_path):
            if getattr(sys, "frozen", False):
                template_path = os.path.join(os.path.dirname(sys.executable), template_name)

        if os.path.exists(template_path):
            try:
                dest_path = os.path.join(profile_dir, "options.txt")
                shutil.copy2(template_path, dest_path)
                log(f"Copied {template_name} to {dest_path}")
                self.update_status("Applied custom options settings...")
            except Exception as e:
                log(f"Failed to copy options template: {e}")
        else:
            log(f"No {template_name} found. Skipping options copy.")

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

            self.current_action_name = "Downloading Loader"
            self.install_loader(mc_dir, config["loader_url"])

            self.install_modpack_logic(mc_dir, config, download_url)

            self.root.after(0, self.reset_ui)
            self.root.after(0, lambda: self.status.config(text="Installation Complete"))
            self.root.after(
                0,
                lambda: messagebox.showinfo(
                    "Success", f"Installed '{pack_name}' successfully!"
                ),
            )
        except Exception as e:
            log("INSTALL ERROR: " + repr(e))
            log(traceback.format_exc())
            self.root.after(
                0,
                lambda: messagebox.showerror(
                    "Error", f"{e}\n\nLog: {LOG_PATH}"
                ),
            )
            self.root.after(0, self.reset_ui)

    def get_mc_dir(self):
        system = platform.system()
        if system == "Windows":
            return os.path.join(os.getenv("APPDATA"), ".minecraft")
        if system == "Darwin":
            return os.path.join(
                os.path.expanduser("~"),
                "Library",
                "Application Support",
                "minecraft",
            )
        return os.path.join(os.path.expanduser("~"), ".minecraft")

    def install_loader(self, mc_dir, loader_url):
        version_id = loader_url.split("/")[-1].replace(".zip", "")
        versions_dir = os.path.join(mc_dir, "versions")
        version_folder = os.path.join(versions_dir, version_id)

        if os.path.exists(version_folder):
            self.update_status(
                f"Loader {version_id} already installed, skipping..."
            )
            return

        libraries_dir = os.path.join(mc_dir, "libraries")
        os.makedirs(versions_dir, exist_ok=True)
        os.makedirs(libraries_dir, exist_ok=True)

        temp_loader_zip = os.path.join(mc_dir, "temp_loader.zip")
        self.progress_var.set(0)

        self.current_action_name = "Downloading Loader"
        http_download_file(
            loader_url, temp_loader_zip, progress_cb=self.update_progress, timeout=60
        )

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

    # --- NEW: update-in-place logic ---
    def install_modpack_update_in_place(self, mc_dir, config, download_url, profile_dir):
        """
        Used when the profile already exists and the user chooses to update.
        It will NOT delete anything in the existing profile_dir.
        It only overwrites/merges content that is present in the downloaded zip.
        """
        self.copy_options_template(profile_dir)

        self.update_status(f"Downloading {config['profile_name']} (update)...")
        self.progress_var.set(0)
        temp_zip = os.path.join(profile_dir, "temp_update.zip")

        self.current_action_name = "Downloading Mods"
        http_download_file(
            download_url, temp_zip, progress_cb=self.update_progress, timeout=120
        )

        temp_extract = os.path.join(profile_dir, "temp_update_extract")
        if os.path.exists(temp_extract):
            shutil.rmtree(temp_extract)
        os.makedirs(temp_extract, exist_ok=True)

        self.update_status("Extracting mods (update)...")
        self.current_action_name = "Extracting"

        with zipfile.ZipFile(temp_zip, "r") as z:
            total_size = sum(f.file_size for f in z.infolist())
            extracted_size = 0
            start_time = time.time()
            last_update_time = 0

            for file_info in z.infolist():
                z.extract(file_info, temp_extract)
                extracted_size += file_info.file_size

                current_time = time.time()
                if current_time - last_update_time > 0.1:
                    elapsed_time = current_time - start_time
                    if elapsed_time > 0 and extracted_size > 0:
                        speed = extracted_size / elapsed_time
                        if speed > 0:
                            remaining = total_size - extracted_size
                            eta = remaining / speed
                        else:
                            eta = 0
                        self.update_progress(
                            extracted_size, total_size, eta
                        )
                    last_update_time = current_time

            self.update_progress(total_size, total_size, 0)

        os.remove(temp_zip)

        is_complex = config.get("is_complex", False)

        if is_complex:
            # Complex pack: merge everything from temp_extract into profile_dir,
            # but DO NOT delete anything that is not in the zip.
            self.merge_folders(temp_extract, profile_dir)
        else:
            # Simple pack: only replace the 'mods' folder
            target_mods = os.path.join(profile_dir, "mods")
            os.makedirs(target_mods, exist_ok=True)

            found_mods_nested = None
            for root_path, dirs, _files in os.walk(temp_extract):
                if "mods" in dirs:
                    found_mods_nested = os.path.join(root_path, "mods")
                    break

            if found_mods_nested:
                shutil.rmtree(target_mods, ignore_errors=True)
                os.makedirs(target_mods, exist_ok=True)
                self.merge_folders(found_mods_nested, target_mods)
            else:
                # If no mods folder in zip, just merge what exists
                self.merge_folders(temp_extract, profile_dir)

        shutil.rmtree(temp_extract, ignore_errors=True)

        final_icon = config.get("icon", "Furnace")
        if "icon_url" in config and HAS_PILLOW:
            self.update_status("Downloading icon...")
            try:
                b64_icon = self.download_icon_as_base64(
                    config["icon_url"], profile_dir
                )
                if b64_icon:
                    final_icon = b64_icon
            except Exception as e:
                log("ERROR icon base64 (update): " + repr(e))
                log(traceback.format_exc())

        default_args = (
            "-Xmx4096m -Xms256m "
            "-Dfml.ignorePatchDiscrepancies=true "
            "-Dfml.ignoreInvalidMinecraftCertificates=true "
            "-Duser.language=en -Duser.country=US"
        )
        custom_jvm_args = config.get("jvm_args", default_args)

        self.update_json_profile(
            mc_dir=mc_dir,
            name=config["profile_name"],
            game_dir=profile_dir,
            version_id=config["version_id"],
            icon=final_icon,
            jvm_args=custom_jvm_args,
        )

    # --- REWRITTEN install_modpack_logic with prompt ---
    def install_modpack_logic(self, mc_dir, config, download_url):
        if not os.path.exists(mc_dir):
            raise Exception("Minecraft folder not found.")

        profile_dir = os.path.join(mc_dir, "profiles", config["folder_name"])
        already_exists = os.path.exists(profile_dir)

        if already_exists:
            answer = messagebox.askyesno(
                "Modpack Already Installed",
                f"You already have '{config['profile_name']}' installed.\n\n"
                "Would you like to update it?\n\n"
                "This will overwrite files from the modpack itself, but your existing worlds and other data in this profile will stay.",
            )
            if not answer:
                self.update_status("Update cancelled by user.")
                return

            os.makedirs(profile_dir, exist_ok=True)
            self.install_modpack_update_in_place(
                mc_dir, config, download_url, profile_dir
            )
            return

        # Fresh install path
        os.makedirs(profile_dir, exist_ok=True)

        self.copy_options_template(profile_dir)

        self.update_status(f"Downloading {config['profile_name']}...")
        self.progress_var.set(0)
        temp_zip = os.path.join(profile_dir, "temp.zip")

        self.current_action_name = "Downloading Mods"
        http_download_file(
            download_url, temp_zip, progress_cb=self.update_progress, timeout=120
        )

        temp_extract = os.path.join(profile_dir, "temp_extract")
        if os.path.exists(temp_extract):
            shutil.rmtree(temp_extract)
        os.makedirs(temp_extract, exist_ok=True)

        self.update_status("Extracting mods...")
        self.current_action_name = "Extracting"

        with zipfile.ZipFile(temp_zip, "r") as z:
            total_size = sum(f.file_size for f in z.infolist())
            extracted_size = 0
            start_time = time.time()
            last_update_time = 0

            for file_info in z.infolist():
                z.extract(file_info, temp_extract)
                extracted_size += file_info.file_size

                current_time = time.time()
                if current_time - last_update_time > 0.1:
                    elapsed_time = current_time - start_time
                    if elapsed_time > 0 and extracted_size > 0:
                        speed = extracted_size / elapsed_time
                        if speed > 0:
                            remaining = total_size - extracted_size
                            eta = remaining / speed
                        else:
                            eta = 0
                        self.update_progress(
                            extracted_size, total_size, eta
                        )
                    last_update_time = current_time

            self.update_progress(total_size, total_size, 0)

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
                b64_icon = self.download_icon_as_base64(
                    config["icon_url"], profile_dir
                )
                if b64_icon:
                    final_icon = b64_icon
            except Exception as e:
                log("ERROR icon base64: " + repr(e))
                log(traceback.format_exc())

        default_args = (
            "-Xmx4096m -Xms256m "
            "-Dfml.ignorePatchDiscrepancies=true "
            "-Dfml.ignoreInvalidMinecraftCertificates=true "
            "-Duser.language=en -Duser.country=US"
        )
        custom_jvm_args = config.get("jvm_args", default_args)

        self.update_json_profile(
            mc_dir=mc_dir,
            name=config["profile_name"],
            game_dir=profile_dir,
            version_id=config["version_id"],
            icon=final_icon,
            jvm_args=custom_jvm_args,
        )

    def update_json_profile(self, mc_dir, name, game_dir, version_id, icon, jvm_args):
        profiles_file = os.path.join(mc_dir, "launcher_profiles.json")
        if not os.path.exists(profiles_file):
            raise Exception(
                "launcher_profiles.json not found (open Minecraft Launcher once first)."
            )

        with open(profiles_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        if "profiles" not in data:
            data["profiles"] = {}

        profile_id = name.replace(" ", "_")
        current_time = time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime())

        final_java_args = (
            f'{jvm_args} -Dminecraft.applet.TargetDirectory="{game_dir}"'
        )

        data["profiles"][profile_id] = {
            "created": current_time,
            "gameDir": game_dir,
            "icon": icon,
            "lastUsed": current_time,
            "lastVersionId": version_id,
            "name": name,
            "type": "custom",
            "javaArgs": final_java_args,
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
