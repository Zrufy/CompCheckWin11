import subprocess
import platform
import os
import sys
import ctypes
import json
from ctypes import windll, wintypes, byref, c_ubyte, sizeof
import re
import winreg
import traceback
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime
import threading
import webbrowser
from PIL import Image, ImageTk

# Definition of colors and style

COLORS = {
    "bg_dark": "#202020",
    "bg_light": "#303030",
    "accent": "#0078D7",  # Windows Color

    "text": "#FFFFFF",
    "success": "#10893E",
    "warning": "#FF8C00",
    "error": "#E81123",
    "disabled": "#666666"
}

class Win11Checker:
    def __init__(self):
        self.results = {
            "cpu": {"status": False, "details": {}},
            "ram": {"status": False, "details": {}},
            "storage": {"status": False, "details": {}},
            "tpm": {"status": False, "details": {}},
            "secure_boot": {"status": False, "details": {}},
            "gpt": {"status": False, "details": {}},  # Aggiunto controllo GPT
            "display": {"status": False, "details": {}},
            "directx": {"status": False, "details": {}},
            "architecture": {"status": False, "details": {}}
        }
        
    def check_cpu_compatibility(self):
        try:
            # Get CPU Insights

            cpu_info = self.get_cpu_info()
            
            # Get cores and frequency

            cores = cpu_info.get("cores", 0)
            freq = cpu_info.get("frequency", 0)
            
            # Controlla se è nella lista CPU compatibili
            cpu_name = cpu_info.get("name", "")
            cpu_generation = self.detect_cpu_generation(cpu_name)
            
            # Check minimum requirements (2 cores and 1GHz)

            min_req_met = cores >= 2 and freq >= 1.0
            generation_ok = cpu_generation >= 8 if "intel" in cpu_name.lower() else cpu_generation >= 2
            
            self.results["cpu"]["status"] = min_req_met and generation_ok
            self.results["cpu"]["details"] = {
                "name": cpu_name,
                "cores": cores,
                "frequency": f"{freq} GHz",
                "generation": cpu_generation,
                "architecture": cpu_info.get("architecture", ""),
                "compatible_generation": generation_ok,
                "meets_min_requirements": min_req_met
            }
        except Exception as e:
            self.results["cpu"]["details"]["error"] = str(e)
            
    def detect_cpu_generation(self, cpu_name):
        cpu_name = cpu_name.lower()
        
        # Intel detection

        if "intel" in cpu_name:
            # Core i3/i5/i7/i9 detection

            match = re.search(r'i[3579]-(\d{1,5})', cpu_name)
            if match:
                model = match.group(1)
                # Extract generation from the first 1-2 model numbers

                if len(model) >= 4:  # 10th gen and above (e.g. i7-1065G7)

                    return int(model[0:2])
                else:
                    return int(model[0])
        
        # AMD detection

        elif "amd" in cpu_name and "ryzen" in cpu_name:
            # Ryzen detection

            match = re.search(r'ryzen [^0-9]*(\d)', cpu_name)
            if match:
                return int(match.group(1))
                
        # Default: assume incompatible (generation 0)

        return 0
            
    def get_cpu_info(self):
        info = {
            "name": platform.processor(),
            "architecture": platform.machine(),
            "cores": 0,
            "frequency": 0.0
        }
        
        try:
            # Ottieni nome CPU più dettagliato
            output = subprocess.check_output("wmic cpu get name", shell=True).decode().strip().split('\n')
            if len(output) >= 2:
                info["name"] = output[1].strip()
                
            # Get Core Number

            output = subprocess.check_output("wmic cpu get NumberOfCores", shell=True).decode().strip().split('\n')
            if len(output) >= 2:
                info["cores"] = int(output[1].strip())
                
            # Get Frequency

            output = subprocess.check_output("wmic cpu get MaxClockSpeed", shell=True).decode().strip().split('\n')
            if len(output) >= 2:
                info["frequency"] = round(int(output[1].strip()) / 1000, 2)
        except:
            pass
            
        return info
    
    def check_ram(self):
        try:
            ram_gb = self.get_ram_size()
            
            self.results["ram"]["status"] = ram_gb >= 4
            self.results["ram"]["details"] = {
                "total": f"{ram_gb} GB",
                "required": "4 GB"
            }
        except Exception as e:
            self.results["ram"]["details"]["error"] = str(e)
            
    def get_ram_size(self):
        try:
            output = subprocess.check_output("wmic computersystem get totalphysicalmemory", shell=True).decode().strip().split("\n")[1]
            return round(int(output) / (1024**3))
        except:
            return 0
            
    def check_storage(self):
        try:
            disk_info = self.get_disk_info()
            
            self.results["storage"]["status"] = disk_info["largest_free_gb"] >= 64
            self.results["storage"]["details"] = {
                "free_space": f"{disk_info['largest_free_gb']} GB",
                "required": "64 GB",
                "system_drive": disk_info["system_drive"],
                "all_drives": disk_info["all_drives"]
            }
        except Exception as e:
            self.results["storage"]["details"]["error"] = str(e)
            
    def get_disk_info(self):
        info = {
            "largest_free_gb": 0,
            "system_drive": "",
            "all_drives": []
        }
        
        try:
            # Get System Drives

            system_drive = os.environ.get('SystemDrive', 'C:')
            info["system_drive"] = system_drive
            
            # Check all available units

            drives = subprocess.check_output("wmic logicaldisk get caption,freespace,size", shell=True).decode().split('\n')[1:]
            for drive in drives:
                parts = drive.split()
                if len(parts) >= 3:
                    try:
                        drive_letter = parts[0].strip()
                        free_space = int(parts[1].strip())
                        total_size = int(parts[2].strip())
                        
                        free_gb = round(free_space / (1024**3))
                        total_gb = round(total_size / (1024**3))
                        
                        info["all_drives"].append({
                            "drive": drive_letter,
                            "free_gb": free_gb,
                            "total_gb": total_gb
                        })
                        
                        if free_gb > info["largest_free_gb"]:
                            info["largest_free_gb"] = free_gb
                            
                        # Specifically check the system drive

                        if drive_letter == system_drive:
                            info["system_drive_free_gb"] = free_gb
                    except:
                        pass
        except:
            pass
            
        return info
            
    def check_tpm(self):
        try:
            tpm_version = self.get_tpm_status()
            
            self.results["tpm"]["status"] = tpm_version >= 2.0
            self.results["tpm"]["details"] = {
                "version": tpm_version,
                "required": "2.0"
            }
        except Exception as e:
            self.results["tpm"]["details"]["error"] = str(e)
            
    def get_tpm_status(self):
        """Rileva TPM usando i risultati della diagnosi"""
        try:
            # TPM verification with wmic
            output = subprocess.check_output("wmic /namespace:\\\\root\\CIMV2\\Security\\MicrosoftTpm path Win32_Tpm get * /format:list", shell=True).decode()
            
            if "SpecVersion" in output:
                match = re.search(r'SpecVersion=([0-9\.]+)', output)
                if match:
                    version_str = match.group(1)
                    if version_str.startswith("2."):
                        return 2.0
                    elif version_str.startswith("1."):
                        return 1.2
            
            # Check if it's enabled
            if "IsEnabled_InitialValue=TRUE" in output:
                return 2.0  # We assume TPM 2.0 if it is enabled but we can't determine the version
        except:
            pass
        
        return 0.0
            
    def check_secure_boot(self):
        try:
            secure_boot = self.check_secure_boot_status()
            
            self.results["secure_boot"]["status"] = secure_boot
            self.results["secure_boot"]["details"] = {
                "enabled": secure_boot,
                "required": True
            }
        except Exception as e:
            self.results["secure_boot"]["details"]["error"] = str(e)
            
    def check_secure_boot_status(self):
        """Check Secure Boot by considering whether it is supported, not just whether it is enabled"""
        try:
            # Check if it is enabled first
            output = subprocess.check_output("reg query \"HKLM\\SYSTEM\\CurrentControlSet\\Control\\SecureBoot\\State\" /v UEFISecureBootEnabled", shell=True).decode()
            if "0x1" in output:
                return True
            
            # If it's not enabled, check if it's supported (UEFI + GPT)
            # Check UEFI
            firmware_output = subprocess.check_output("powershell -Command \"(Get-ComputerInfo).BiosFirmwareType\"", shell=True).decode().strip()
            is_uefi = "Uefi" in firmware_output
            
            # Check GPT
            is_gpt = self.check_disk_partition_style()
            
            # If it's UEFI and GPT, Secure Boot is supported
            if is_uefi and is_gpt:
                return True
        except:
            pass
        
        return False
        
        
    def check_disk_partition_style(self):
        """Check if the system disk is using GPT"""
        try:
            script_file = "diskpart_script.txt"
            with open(script_file, "w") as f:
                f.write("list disk\nexit")
            
            output = subprocess.check_output(f"diskpart /s {script_file}", shell=True).decode()
            os.remove(script_file)
            
            return "GPT" in output
        except:
            pass
        
        return False
    
    def check_directx(self):
        try:
            directx_info = self.get_directx_info()
            
            # Requirements: DirectX 12 or higher and WDDM 2.0 or higher

            dx12_ok = directx_info["directx_version"] >= 12
            wddm_ok = directx_info["wddm_version"] >= 2.0
            
            self.results["directx"]["status"] = dx12_ok and wddm_ok
            self.results["directx"]["details"] = {
                "directx_version": directx_info["directx_version"],
                "wddm_version": directx_info["wddm_version"],
                "required": "DirectX 12, WDDM 2.0"
            }
        except Exception as e:
            self.results["directx"]["details"]["error"] = str(e)
            
    def get_directx_info(self):
        info = {
            "directx_version": 0,
            "wddm_version": 0.0
        }
        
        try:
            # Verifica DirectX tramite dxdiag
            with open("dxinfo.txt", "w") as f:
                subprocess.call("dxdiag /t dxinfo.txt", shell=True)
                
            # Wait for the file to be generated

            import time
            max_wait = 5
            while max_wait > 0 and not os.path.exists("dxinfo.txt"):
                time.sleep(1)
                max_wait -= 1
                
            if os.path.exists("dxinfo.txt"):
                with open("dxinfo.txt", "r") as f:
                    content = f.read()
                    
                    # Search for DirectX version

                    dx_match = re.search(r'DirectX Version: DirectX (\d+)', content)
                    if dx_match:
                        info["directx_version"] = int(dx_match.group(1))
                        
                    # Search for WDDM version

                    wddm_match = re.search(r'Driver Model: WDDM (\d+\.\d+)', content)
                    if wddm_match:
                        info["wddm_version"] = float(wddm_match.group(1))
                
                # Remove the temporary file

                try:
                    os.remove("dxinfo.txt")
                except:
                    pass
                    
            # If you couldn't get the information, try another method

            if info["directx_version"] == 0:
                # Check for d3d12.dll

                if os.path.exists("C:\\Windows\\System32\\d3d12.dll"):
                    info["directx_version"] = 12
                    
                # Check WDDM version in the registry

                try:
                    key_path = r'SOFTWARE\Microsoft\Windows NT\CurrentVersion'
                    key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path)
                    build = winreg.QueryValueEx(key, "CurrentBuildNumber")[0]
                    
                    # Windows 10/11 build 10586 or higher has WDDM 2.0+

                    if int(build) >= 10586:
                        info["wddm_version"] = 2.0
                except:
                    pass
        except:
            pass
            
        return info
        
    def check_architecture(self):
        try:
            arch = platform.machine()
            is_64bit = platform.architecture()[0] == '64bit'
            
            # Windows 11 requires 64-bit

            self.results["architecture"]["status"] = is_64bit
            self.results["architecture"]["details"] = {
                "architecture": arch,
                "is_64bit": is_64bit,
                "required": "64-bit"
            }
        except Exception as e:
            self.results["architecture"]["details"]["error"] = str(e)
        
    def check_gpt(self):
        """Check if the system disk is using GPT"""
        try:
            is_gpt = self.check_disk_partition_style()
            
            self.results["gpt"]["status"] = is_gpt
            self.results["gpt"]["details"] = {
                "is_gpt": is_gpt,
                "required": "GPT partition required for UEFI/Secure Boot"
            }
        except Exception as e:
            self.results["gpt"]["details"]["error"] = str(e)
            
    def run_all_checks(self):
        self.check_cpu_compatibility()
        self.check_ram()
        self.check_storage()
        self.check_tpm()
        self.check_secure_boot()
        self.check_gpt()  
        self.check_directx()
        self.check_architecture()
        
        # Calculate the overall result
        essential_checks = ["cpu", "ram", "storage", "tpm", "secure_boot", "gpt", "architecture"]
        essential_passed = all(self.results[check]["status"] for check in essential_checks)
        
        return {
            "compatible": essential_passed,
            "details": self.results,
            "summary": {
                "essential_requirements_met": essential_passed,
                "total_passed": sum(1 for r in self.results.values() if r["status"]),
                "total_checks": len(self.results)
            }
        }


class Win11CheckerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("CompCheckWin11")
        
        # Set application icon (if available)

        try:
            self.root.iconbitmap("C:\\Users\\vincenzo\\Desktop\\win11_checker.ico")
        except:
            pass
            
        # Configure style

        self.configure_styles()
        
        # Crea il checker
        self.checker = Win11Checker()
        
        # Flags for the audit in progress

        self.checking = False
        
        # Crea l'interfaccia
        self.create_widgets()
        
    def configure_styles(self):
        # Configure style for ttk

        style = ttk.Style()
        style.theme_use('clam')  # Use a basic theme that we can customize

        
        # Configure background colors

        self.root.configure(bg=COLORS["bg_dark"])
        
        # Configure styles for widgets

        style.configure("TFrame", background=COLORS["bg_dark"])
        style.configure("Header.TLabel", 
                        background=COLORS["bg_dark"], 
                        foreground=COLORS["text"], 
                        font=("Segoe UI", 16, "bold"))
        style.configure("Subheader.TLabel", 
                        background=COLORS["bg_dark"], 
                        foreground=COLORS["text"], 
                        font=("Segoe UI", 12))
        style.configure("Result.TLabel", 
                        background=COLORS["bg_dark"], 
                        foreground=COLORS["text"], 
                        font=("Segoe UI", 10))
        
        # Buttons

        style.configure("TButton", 
                        background=COLORS["accent"], 
                        foreground=COLORS["text"],
                        font=("Segoe UI", 10))
        style.map("TButton",
                 background=[("active", COLORS["accent"])])
                 
        # Primary button

        style.configure("Primary.TButton", 
                        background=COLORS["accent"], 
                        foreground=COLORS["text"],
                        font=("Segoe UI", 12, "bold"))
        style.map("Primary.TButton",
                 background=[("active", "#0063B1")])  # Darker color when active

                 
        # Success Button

        style.configure("Success.TButton", 
                        background=COLORS["success"], 
                        foreground=COLORS["text"],
                        font=("Segoe UI", 10))
        style.map("Success.TButton",
                 background=[("active", "#0C6E30")])  # Darker color when active

                    
        # Progress bar

        style.configure("TProgressbar", 
                        background=COLORS["accent"],
                        troughcolor=COLORS["bg_light"],
                        borderwidth=0,
                        thickness=10)
                        
        # Separator

        style.configure("TSeparator", background=COLORS["bg_light"])
        
        # Result Frames

        style.configure("Result.TFrame", 
                        background=COLORS["bg_light"],
                        relief="flat")
                        
        # Status Labels

        style.configure("Pass.TLabel", 
                        background=COLORS["bg_light"], 
                        foreground=COLORS["success"], 
                        font=("Segoe UI", 11, "bold"))
        style.configure("Fail.TLabel", 
                        background=COLORS["bg_light"], 
                        foreground=COLORS["error"], 
                        font=("Segoe UI", 11, "bold"))
        style.configure("Detail.TLabel", 
                        background=COLORS["bg_light"], 
                        foreground=COLORS["text"], 
                        font=("Segoe UI", 9))
        style.configure("DetailTitle.TLabel", 
                        background=COLORS["bg_light"], 
                        foreground=COLORS["text"], 
                        font=("Segoe UI", 9, "bold"))

    def create_widgets(self):
        # Main frame with conditional scrollbar

        self.outer_frame = ttk.Frame(self.root)
        self.outer_frame.pack(fill=tk.BOTH, expand=True)
        
        # Let's create a canvas that will contain everything

        self.main_canvas = tk.Canvas(self.outer_frame, bg=COLORS["bg_dark"], highlightthickness=0)
        self.main_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Scrollbar for small screens (initially hidden)

        self.main_scrollbar = ttk.Scrollbar(self.outer_frame, orient=tk.VERTICAL, command=self.main_canvas.yview)
        # We don't pack here, we will only do it if necessary

        
        # Main frame within the canvas

        self.main_frame = ttk.Frame(self.main_canvas)
        self.main_frame_id = self.main_canvas.create_window((0, 0), window=self.main_frame, anchor=tk.NW)
        
        # Configure Canvas for Scrollbar

        self.main_canvas.configure(yscrollcommand=self.main_scrollbar.set)
        
        # Heading

        self.header_frame = ttk.Frame(self.main_frame)
        self.header_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Windows 11 logo on the left

        try:
            # Use the full path to the ico file

            ico_path = "C:\\Users\\vincenzo\\Desktop\\win11_checker.ico"
            
            # Upload the

            win_logo = Image.open(ico_path)
            win_logo = win_logo.resize((48, 48), Image.LANCZOS)  # Resize smaller

            win_logo_img = ImageTk.PhotoImage(win_logo)
            
            self.logo_label = ttk.Label(self.header_frame, image=win_logo_img, background=COLORS["bg_dark"])
            self.logo_label.image = win_logo_img  # Keep a reference to avoid garbage collection

        except Exception as e:
            print(f"Unable to load icon: {e}")
            # Fallback to Unicode Character

            self.logo_label = ttk.Label(self.header_frame, 
                                      text="⊞", 
                                      style="Header.TLabel",
                                      font=("Segoe UI", 20))
                                      
        self.logo_label.pack(side=tk.LEFT, padx=(0, 20),pady=(20, 10))  # No padding on the left, small padding on the right

        
        # Title immediately after the icon

        self.title_label = ttk.Label(self.header_frame, 
                                   text="Win11 Compatibility Checker", 
                                   style="Header.TLabel")
        self.title_label.pack(side=tk.LEFT)
        
        # Separator

        ttk.Separator(self.main_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=5, pady=5)
        
        # Control button and final result in the same row

        self.button_result_frame = ttk.Frame(self.main_frame)
        self.button_result_frame.pack(fill=tk.X, padx=5, pady=2)
        
        # Left button

        self.check_button = ttk.Button(self.button_result_frame, 
                                      text="Start Audit", 
                                      style="Primary.TButton",
                                      command=self.start_check)
        self.check_button.pack(side=tk.LEFT, padx=5, pady=5)
        
        # Progress bar (initially hidden)

        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(self.button_result_frame, 
                                           variable=self.progress_var,
                                           style="TProgressbar",
                                           length=200,
                                           mode="indeterminate")
        
        # End result on the right (hidden initially)

        self.final_result_label = ttk.Label(self.button_result_frame, 
                                          text="", 
                                          style="Detail.TLabel")
        
        # Frames for results

        self.results_frame = ttk.Frame(self.main_frame, style="TFrame")
        self.results_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Action buttons at the bottom

        self.action_frame = ttk.Frame(self.main_frame)
        self.action_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Posiziona i pulsanti di azione uno accanto all'altro, centrati
        self.export_button = ttk.Button(self.action_frame, 
                                      text="Export results", 
                                      style="TButton",
                                      command=self.export_results)
        self.export_button.pack(side=tk.LEFT, padx=5,pady=10,expand=True, fill=tk.X)
                                      
        self.details_button = ttk.Button(self.action_frame, 
                                       text="Detailed advice", 
                                       style="TButton",
                                       command=self.show_detailed_advice)
        self.details_button.pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)
        
        # Hide action buttons at the beginning

        self.action_frame.pack_forget()
        
        # Initialize result labels

        self.result_labels = {}
        self.initialize_result_labels()
        
        # Configure scaling event

        self.main_frame.bind("<Configure>", self.check_scrollbar_needed)
        self.main_canvas.bind("<Configure>", self.on_canvas_configure)
        
        # Enable scrolling with the mouse wheel

        self.main_canvas.bind_all("<MouseWheel>", self.on_mousewheel)
        

    def check_scrollbar_needed(self, event=None):
        """Check if the scrollbar is needed and show/hide it accordingly"""
        # Update the scroll region

        self.main_canvas.configure(scrollregion=self.main_canvas.bbox("all"))
        
        # Get frame and canvas size

        frame_height = self.main_frame.winfo_reqheight()
        canvas_height = self.main_canvas.winfo_height()
        
        # Show/hide scrollbar by size

        if frame_height > canvas_height:
            self.main_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        else:
            self.main_scrollbar.pack_forget()

    def on_canvas_configure(self, event=None):
        """Handles canvas scaling"""
        # Resize the width of the inner window

        width = event.width
        self.main_canvas.itemconfig(self.main_frame_id, width=width)
        
        # Check if you need the scrollbar

        self.check_scrollbar_needed()

    def on_mousewheel(self, event=None):
        """Handles scrolling with the mouse wheel"""
        # Check if the scrollbar is visible

        if self.main_scrollbar.winfo_ismapped():
            # Calculate the direction of the scroll (different between Windows and macOS)

            if event.delta:
                # Windows (event.delta is positive when scrolling up)

                self.main_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            else:
                # Linux (event.num indicates direction)

                if event.num == 4:
                    self.main_canvas.yview_scroll(-1, "units")
                elif event.num == 5:
                    self.main_canvas.yview_scroll(1, "units")

    def initialize_result_labels(self):
        """Initialize result labels with a uniform layout"""
        categories = {
            "cpu": "Processor (CPU)",
            "ram": "Memory (RAM)",
            "storage": "Storage space",
            "tpm": "Trusted Platform Module (TPM)",
            "secure_boot": "Secure Boot",
            "gpt": "GPT partition", 
            "directx": "DirectX and WDDM 2",
            "architecture": "System architecture"
        }
        
        # Configura stile per le etichette
        style = ttk.Style()
        style.configure("CategoryTitle.TLabel", 
                        background=COLORS["bg_light"], 
                        foreground=COLORS["text"], 
                        font=("Segoe UI", 12, "bold"))
        
        style.configure("ResultDetail.TLabel", 
                        background=COLORS["bg_light"], 
                        foreground=COLORS["text"], 
                        font=("Segoe UI", 10))
        
        # Create a frame for each category

        for i, (key, label) in enumerate(categories.items()):
            # Frames for each result

            result_frame = ttk.Frame(self.results_frame, style="Result.TFrame")
            result_frame.pack(fill=tk.X, padx=5, pady=15, ipady=5)
            
            # Result header

            header_frame = ttk.Frame(result_frame, style="Result.TFrame")
            header_frame.pack(fill=tk.X, padx=10, pady=2)
            
            category_label = ttk.Label(header_frame, 
                                    text=label, 
                                    style="CategoryTitle.TLabel")
            category_label.pack(side=tk.LEFT)
            
            # Status (initially empty)

            status_label = ttk.Label(header_frame, 
                                text="Waiting", 
                                style="Detail.TLabel")
            status_label.pack(side=tk.RIGHT)
            
            # Frame for details

            details_frame = ttk.Frame(result_frame, style="Result.TFrame")
            details_frame.pack(fill=tk.X, padx=20, pady=2)
            
            # Dettagli (inizialmente vuoti)
            details_label = ttk.Label(details_frame, 
                                    text="", 
                                    style="ResultDetail.TLabel",
                                    justify=tk.LEFT,
                                    wraplength=650)
            details_label.pack(anchor=tk.W)
            
            # Separator to improve readability

            if i < len(categories) - 1:  # Do not add separator after the last element

                ttk.Separator(self.results_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=5, pady=2)
            
            # Salva riferimenti
            self.result_labels[key] = {
                "frame": result_frame,
                "status": status_label,
                "details": details_label
            }
        
        # Update the scrollbar


    def on_frame_configure(self, event=None):
        """Handles result frame scaling"""
        self.main_canvas.configure(scrollregion=self.main_canvas.bbox("all"))
    
    def on_canvas_configure(self, event=None):
        """Handles canvas scaling"""
        # Resize the width of the inner window

        width = event.width
        self.main_canvas.itemconfig(self.main_frame_id, width=width)
        
        # Check if you need the scrollbar

        self.check_scrollbar_needed()

    def start_check(self):
        """Start the compatibility check in a separate thread"""
        if self.checking:
            return
            
        # Hide the end result label

        self.final_result_label.pack_forget()
        
        # Hide action buttons

        self.action_frame.pack_forget()
        
        if self.action_frame.winfo_ismapped():
            self.action_frame.pack_forget()
            
        # Change button text and show progress

        self.check_button.configure(text="Checking in progress...", state="disabled")
        self.progress_bar.pack(side=tk.LEFT, padx=10)
        self.progress_bar.start(10)
        
        # Set flags

        self.checking = True
        
        # Start Thread

        threading.Thread(target=self.run_check, daemon=True).start()

    def run_check(self):
        """Runs background check"""
        try:
            # Run the checks

            result = self.checker.run_all_checks()
            
            # Update the interface in the main thread

            self.root.after(0, self.update_results)
        except Exception as e:
            # Handle Errors

            self.root.after(0, lambda: self.show_error(str(e)))

    def update_results(self):
        """Update the interface with the results"""
        # Stop the progress bar

        self.progress_bar.stop()
        self.progress_bar.pack_forget()
        
        # Ripristina il pulsante
        self.check_button.configure(text="Restart Control", state="normal")
        
        # Reset the flag

        self.checking = False
        
        # Update the result labels

        for category, data in self.checker.results.items():
            if category in self.result_labels:
                status_text = "✓ OK" if data["status"] else "✗ NO"
                status_style = "Pass.TLabel" if data["status"] else "Fail.TLabel"
                
                self.result_labels[category]["status"].configure(text=status_text, style=status_style)
                
                # Prepare details in an extremely compact way

                details_parts = []
                
                # Filter and format only essential details

                if category == "cpu":
                    if "name" in data["details"]:
                        details_parts.append(f"Name: {data['details']['name']}")
                    if "cores" in data["details"]:
                        details_parts.append(f"Core: {data['details']['cores']}")
                    if "frequency" in data["details"]:
                        details_parts.append(f"Freq: {data['details']['frequency']}")
                elif category == "ram":
                    if "total" in data["details"]:
                        details_parts.append(f"Total: {data['details']['total']}")
                elif category == "storage":
                    if "free_space" in data["details"]:
                        details_parts.append(f"Free space: {data['details']['free_space']}")
                elif category == "tpm":
                    if "version" in data["details"]:
                        details_parts.append(f"Version: {data['details']['version']}")
                elif category == "secure_boot":
                    if "enabled" in data["details"]:
                        details_parts.append(f"Active: {'Sì' if data['details']['enabled'] else 'No'}")
                elif category == "directx":
                    if "directx_version" in data["details"]:
                        details_parts.append(f"DX: {data['details']['directx_version']}")
                    if "wddm_version" in data["details"]:
                        details_parts.append(f"WDDM: {data['details']['wddm_version']}")
                elif category == "architecture":
                    if "is_64bit" in data["details"]:
                        details_parts.append(f"64-bit: {'Sì' if data['details']['is_64bit'] else 'No'}")
                
                # Add the minimum requirement at the end

                if "required" in data["details"]:
                    details_parts.append(f"(Min: {data['details']['required']})")
                
                # Merge everything into one row

                details_text = " | ".join(details_parts)
                
                # Set a narrower maximum wrapping width

                self.result_labels[category]["details"].configure(text=details_text)
        
        # Show the final result next to the button

        self.show_final_result()
        
        # Show action buttons

        self.action_frame.pack(fill=tk.X, padx=5, pady=5)
        self.check_scrollbar_needed()
        

    def show_final_result(self):
        """Show the final result next to the button"""
        # Calculate the result

        essential_checks = ["cpu", "ram", "storage", "tpm", "secure_boot", "architecture"]
        essential_passed = all(self.checker.results[check]["status"] for check in essential_checks)
        
        total_passed = sum(1 for r in self.checker.results.values() if r["status"])
        total_checks = len(self.checker.results)
        
        # Set text and style

        if essential_passed:
            self.final_result_label.configure(
                text="✓ COMPATIBLE",
                style="Pass.TLabel",
                font=("Segoe UI", 11, "bold")
            )
        else:
            self.final_result_label.configure(
                text="✗ NOT COMPATIBLE",
                style="Fail.TLabel",
                font=("Segoe UI", 11, "bold")
            )
        
        # Show result label

        self.final_result_label.pack(side=tk.RIGHT, padx=5)

    def show_error(self, error_message):
        """Show an error message"""
        # Stop the progress bar

        self.progress_bar.stop()
        self.progress_bar.pack_forget()
        
        # Ripristina il pulsante
        self.check_button.configure(text="Restart Control", state="normal")
        
        # Reset the flag

        self.checking = False
        
        # Show error

        messagebox.showerror("Error", f"An error occurred during the check:\n{error_message}")

    def clear_results(self):
        """Cleans up previous results"""
        for category in self.result_labels:
            self.result_labels[category]["status"].configure(text="Waiting", style="Detail.TLabel")
            self.result_labels[category]["details"].configure(text="")

    def export_results(self):
        """Export results to a JSON file"""
        try:
            # Ask where to save the file

            filename = filedialog.asksaveasfilename(
                defaultextension=".json",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
                    title="Salva risultati"
                )
                
            if not filename:  # User has canceled

                return
                
            # Save the file

            saved_file = self.checker.export_results(filename)
            
            # Show confirmation

            messagebox.showinfo("Export completed", f"Results have been saved in:\n{saved_file}")
                
        except Exception as e:
                messagebox.showerror("Error", f"Unable to export results:\n{str(e)}")
        
    def show_detailed_advice(self):
        """Show a window with detailed recommendations"""
        # Create a new window
        advice_window = tk.Toplevel(self.root)
        advice_window.title("Detailed recommendations for Windows 11")
        advice_window.geometry("700x500")
        advice_window.configure(bg=COLORS["bg_dark"])
        advice_window.resizable(False, False)
        
        # Try setting the icon
        try:
            advice_window.iconbitmap("c:\\users\\vincenzo\\desktop\\win11_checker.ico")
        except:
            pass
            
        # Main frame
        main_frame = ttk.Frame(advice_window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        
        # Heading
        title_label = ttk.Label(main_frame, 
                            text="How to fix compatibility issues", 
                            style="Header.TLabel")
        title_label.pack(pady=10)
        
        # Scrolling canvas
        canvas = tk.Canvas(main_frame, bg=COLORS["bg_dark"], highlightthickness=0)
        canvas.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(main_frame, orient=tk.VERTICAL, command=canvas.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Internal frame
        advice_frame = ttk.Frame(canvas)
        canvas.create_window((0, 0), window=advice_frame, anchor=tk.NW)
        
        # Add recommendations for each problem
        essential_checks = ["cpu", "ram", "storage", "tpm", "secure_boot", "architecture"]
        
        advice_text = {
            "cpu": {
                "title": "Incompatible processor (CPU)",
                "text": "• Check if your processor is on the official list of supported processors.\n"
                        "• Windows 11 requires 8th Gen Intel processors or newer, or AMD Ryzen 2000 or newer.\n"
                        "• The processor must have at least 2 cores and a frequency of 1 GHz or higher.\n"
                        "• If your processor is not supported, the only solution is to upgrade your hardware."
            },
            "ram": {
                "title": "Insufficient memory (RAM)",
                "text": "• Windows 11 requires at least 4 GB of RAM.\n"
                        "• For best performance, we recommend that you have at least 8 GB of RAM.\n"
                        "• Check to see if your computer supports memory expansion.\n"
"• Check the type of supported memory (DDR3, DDR4, etc.) before purchasing new modules."
            },
            "storage": {
                "title": "Insufficient storage space",
                "text": "• Windows 11 requires at least 64 GB of free space.\n"
                        "• You can free up space by deleting unnecessary files, unused programs, or by using Disk Cleanup.\n"
                        "• Consider adding an additional hard drive or SSD.\n"
                        "• SSDs perform better than traditional hard drives."
            },
            "tpm": {
                "title": "TPM 2.0 not detected",
                "text": "• The TPM (Trusted Platform Module) 2.0 is required for Windows 11.\n"
                        "• Enter your computer's BIOS/UEFI (usually by pressing F2, F12, DEL at startup).\n"
"• Look for settings related to 'TPM', 'Security Chip', 'PTT' (for Intel), or 'fTPM' (for AMD).\n"
                        "• Enable TPM/PTT/fTPM if present.\n"
                        "• Some computers may require a firmware update.\n"
                        "• If your computer does not have a TPM, you may need to install a compatible TPM module (if supported by the motherboard)."
            },
            "secure_boot": {
                "title": "Secure Boot not active",
                "text": "• Secure Boot is a required security feature for Windows 11.\n"
                        "• Enter your computer's BIOS/UEFI.\n"
                        "• Look in the security settings for the 'Secure Boot' option.\n"
                        "• You may need to change the boot mode from Legacy to UEFI.\n"
"• CAUTION: Changing these settings may require you to reinstall the operating system.\n"
                        "• Consult your motherboard manual or contact the manufacturer for specific instructions."
            },
            "architecture": {
                "title": "Incompatible architecture",
                "text": "• Windows 11 requires a 64-bit system.\n"
                        "• If you are using a 32-bit version of Windows, you will need to perform a fresh 64-bit installation.\n"
                        "• Check if your processor supports 64-bit architecture.\n"
                        "• Most processors from the last 10-15 years support 64-bit."
            }
        }
        
        for check in essential_checks:
            # Frame for the advice
            check_frame = ttk.Frame(advice_frame, style="Result.TFrame")
            check_frame.pack(fill=tk.X, padx=5, pady=5, ipady=5)
            
            # Title
            title_label = ttk.Label(check_frame, 
                                text=advice_text[check]["title"], 
                                style="DetailTitle.TLabel",
                                font=("Segoe UI", 12, "bold"))
            title_label.pack(anchor=tk.W, padx=10, pady=5)
            
            # Text of the advice
            advice_label = ttk.Label(check_frame, 
                                text=advice_text[check]["text"], 
                                style="Detail.TLabel",
                                justify=tk.LEFT,
                                wraplength=650)
            advice_label.pack(anchor=tk.W, padx=20, pady=5)
                
        # Add useful links
        link_frame = ttk.Frame(advice_frame, style="Result.TFrame")
        link_frame.pack(fill=tk.X, padx=5, pady=10, ipady=5)
        
        link_title = ttk.Label(link_frame, 
                            text="Link utili", 
                            style="DetailTitle.TLabel",
                            font=("Segoe UI", 12, "bold"))
        link_title.pack(anchor=tk.W, padx=10, pady=5)
        
        # Function to open links
        def open_link(url):
            import webbrowser
            webbrowser.open(url)
            
        # Microsoft resources links
        ms_link = ttk.Label(link_frame, 
                        text="• System requirements for Windows 11 (Microsoft)", 
                        style="Detail.TLabel",
                        cursor="hand2",
                        foreground=COLORS["accent"])
        ms_link.pack(anchor=tk.W, padx=20, pady=2)
        ms_link.bind("<Button-1>", lambda e: open_link("https://www.microsoft.com/windows/windows-11-specifications"))
        
        cpu_link = ttk.Label(link_frame, 
                        text="• Windows 11 supported processors", 
                        style="Detail.TLabel",
                        cursor="hand2",
                        foreground=COLORS["accent"])
        cpu_link.pack(anchor=tk.W, padx=20, pady=2)
        cpu_link.bind("<Button-1>", lambda e: open_link("https://docs.microsoft.com/windows-hardware/design/minimum/supported/windows-11-supported-intel-processors"))
        
        bypass_link = ttk.Label(link_frame, 
                            text="•Install Windows 11 on unsupported hardware", 
                            style="Detail.TLabel",
                            cursor="hand2",
                            foreground=COLORS["accent"])
        bypass_link.pack(anchor=tk.W, padx=20, pady=2)
        bypass_link.bind("<Button-1>", lambda e: open_link("https://support.microsoft.com/windows/ways-to-install-windows-11-e0edbbfb-cfc5-4011-868b-2ce77ac7c70e"))
        
        # Configure scrolling
        advice_frame.update_idletasks()
        canvas.config(scrollregion=canvas.bbox("all"))
        
        # Handle resizing
        def on_configure(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
            canvas.itemconfig(canvas.find_all()[0], width=event.width)
            
        canvas.bind("<Configure>", on_configure)
        
        # Add mouse wheel scrolling
        def on_mousewheel(event):
            # Per Windows (delta negativo = scroll giù)
            if operating_system == "Windows":
                canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            # Per macOS (delta positivo = scroll su)
            else:
                canvas.yview_scroll(int(-1 * event.delta), "units")

        # Determina il sistema operativo
        import platform
        operating_system = platform.system()

        # Binding per il mousewheel
        advice_window.bind_all("<MouseWheel>", on_mousewheel)
        # Per Linux
        advice_window.bind_all("<Button-4>", lambda e: canvas.yview_scroll(-1, "units"))
        advice_window.bind_all("<Button-5>", lambda e: canvas.yview_scroll(1, "units"))

        # Assicurati di rimuovere i binding alla chiusura
        def on_closing():
            advice_window.unbind_all("<MouseWheel>")
            advice_window.unbind_all("<Button-4>")
            advice_window.unbind_all("<Button-5>")
            advice_window.destroy()
        
        advice_window.protocol("WM_DELETE_WINDOW", on_closing)

def main():
    # Create the main window

    root = tk.Tk()
    
    # Set fixed size without the ability to resize

    window_width = 420
    window_height = 950
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    x = (screen_width - window_width) // 2
    y = (screen_height - window_height) // 2
    
    # Set Geometry and Disable Scaling

    root.geometry(f"{window_width}x{window_height}+{x}+{y}")
    root.resizable(False, False)  # Disable scaling in both width and height
    app = Win11CheckerGUI(root)
    
    # Start the main loop

    root.mainloop()

if __name__ == "__main__":
    main()