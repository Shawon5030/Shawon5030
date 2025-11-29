import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import time
import os
import requests
import uuid
import hashlib
import random
import json
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# --- Utility Classes ---

class LicenseManager:
    """Manages license checking with Unique Random Generation based on GitHub check."""
    def __init__(self):
        self.license_file = "license.txt"
        # ⚠️ IMPORTANT: আপনার GitHub RAW লিংক
        self.github_raw_url = "https://raw.githubusercontent.com/Shawon5030/youknow/refs/heads/main/allright.txt"
    
    def get_existing_keys(self):
        """Fetches all existing keys from GitHub to ensure uniqueness."""
        existing_keys = set()
        nocache_url = f"{self.github_raw_url}?v={random.randint(1, 1000000)}"
        try:
            response = requests.get(nocache_url, timeout=10)
            if response.status_code == 200:
                # Handle both single and double quotes
                content = response.text.replace("'", '"')
                try:
                    data = json.loads(content)
                    if isinstance(data, list):
                        for entry in data:
                            existing_keys.update(entry.keys())
                except json.JSONDecodeError:
                    pass # If server data is corrupt, we proceed with empty set
        except:
            pass # If offline, we proceed with empty set (risk is low with random uuid)
        return existing_keys

    def generate_unique_key(self):
        """Generates a guaranteed unique ID by checking against GitHub."""
        existing_keys = self.get_existing_keys()
        
        while True:
            # Generate a Random Unique Key (SHAWON-XXXX-XXXX-XXXX)
            # Using uuid4 (Random) instead of getnode (Hardware) to ensure we can generate fresh keys
            uid = uuid.uuid4().hex.upper()
            new_key = f"SHAWON-{uid[:4]}-{uid[4:8]}-{uid[8:12]}"
            
            # If key doesn't exist in GitHub, break the loop
            if new_key not in existing_keys:
                return new_key

    def check_license(self):
        """Check license from GitHub and local file (JSON Format)"""
        try:
            # Step 1: Check/Create local license file
            if not os.path.exists(self.license_file) or os.stat(self.license_file).st_size == 0:
                unique_key = self.generate_unique_key()
                with open(self.license_file, 'w') as f:
                    f.write(unique_key)
                return False, f"New Key Generated: {unique_key}\nPlease send this key to Admin for activation."
            
            with open(self.license_file, 'r') as f:
                local_key = f.read().strip()
            
            if not local_key:
                unique_key = self.generate_unique_key()
                with open(self.license_file, 'w') as f:
                    f.write(unique_key)
                return False, f"Key Generated: {unique_key}\nPlease send this key to Admin."

            # Step 2: Download License Data with Cache Busting
            nocache_url = f"{self.github_raw_url}?v={random.randint(1, 1000000)}"
            
            try:
                response = requests.get(nocache_url, timeout=10)
            except requests.exceptions.RequestException:
                return False, "Internet connection failed. Cannot verify license."

            if response.status_code == 200:
                server_content = response.text  # Debugging purpose
                try:
                    # JSON Parse Try
                    # FIX: Replace single quotes with double quotes automatically
                    formatted_content = server_content.replace("'", '"')
                    remote_licenses = json.loads(formatted_content)
                    
                    found_expiry_date = None
                    
                    if isinstance(remote_licenses, list):
                        for license_obj in remote_licenses:
                            if local_key in license_obj:
                                found_expiry_date = license_obj[local_key]
                                break
                    
                    if found_expiry_date:
                        try:
                            expiry_date = datetime.strptime(found_expiry_date, "%Y-%m-%d")
                            if datetime.now() > expiry_date:
                                return False, f"License Expired on {found_expiry_date}.\nContact Admin to renew."
                            else:
                                return True, f"Active (Expires: {found_expiry_date})"
                        except ValueError:
                            return False, "Date format error in server database."
                    else:
                        return False, f"Key Not Active.\nYour Key: {local_key}\nSend to Admin."
                        
                except json.JSONDecodeError:
                    preview = server_content[:200]
                    return False, f"Server Data Error!\nServer sent:\n{preview}\n\n(Fix your GitHub file format to valid JSON)"
            else:
                return False, f"Server Error: {response.status_code}"
                
        except Exception as e:
            return False, f"License check error: {str(e)}"

class FloatingWindowManager:
    """Manages the UI for separate browser windows and background mode."""
    def __init__(self):
        self.floating_windows = {} 
        self.floating_mode = tk.BooleanVar(value=True) 
        self.background_mode = tk.BooleanVar(value=False) 
    
    def create_floating_window(self, window_id, driver):
        pass
    
    def close_floating_window(self, window_id):
        if window_id in self.floating_windows:
            self.floating_windows[window_id].destroy()
            del self.floating_windows[window_id]
    
    def close_all_windows(self):
        self.floating_windows.clear()


class FacebookCodeSender:
    """Handles the core logic for sending SMS codes using Selenium."""
    def __init__(self, floating_manager):
        self.results = []
        self.lock = threading.Lock()
        self.floating_manager = floating_manager
        self.drivers = {} 
        self.stop_processing = False
        
    def create_driver(self, window_id):
        """Create separate Chrome driver."""
        options = webdriver.ChromeOptions()
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        if self.floating_manager.background_mode.get():
            options.add_argument("--headless=new") 
            options.add_argument("--disable-gpu")
            options.add_argument("--no-sandbox")
            options.add_argument("--window-size=1920,1080")
        else:
            options.add_argument("--window-size=1000,700")
            options.add_argument(f"--window-position={window_id * 50},{window_id * 50}")

        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=options
        )
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        if not self.floating_manager.background_mode.get():
            try:
                driver.minimize_window()
            except Exception:
                pass 
        
        self.floating_manager.create_floating_window(window_id, driver)
        self.drivers[window_id] = driver 
        return driver
    
    def is_captcha_present(self, driver):
        try:
            page_source = driver.page_source.lower()
            if "g-recaptcha" in page_source: return True
            iframes = driver.find_elements(By.TAG_NAME, "iframe")
            for iframe in iframes:
                if "recaptcha" in (iframe.get_attribute("title") or "").lower(): return True
                if "google.com/recaptcha" in (iframe.get_attribute("src") or ""): return True
            if "security check" in page_source or "enter the text" in page_source: return True
            return False
        except: return False

    def process_single_number(self, phone_number, window_id):
        if self.stop_processing: return False, "Stopped"
        
        driver = self.create_driver(window_id)
        wait_time = 30 if self.floating_manager.background_mode.get() else 15
        wait = WebDriverWait(driver, wait_time)
        
        try:
            driver.get("https://www.facebook.com/login/identify")
            time.sleep(3)
            
            if self.is_captcha_present(driver):
                 driver.quit()
                 if window_id in self.drivers: del self.drivers[window_id]
                 return False, "Captcha"

            phone_input = wait.until(EC.presence_of_element_located((By.ID, "identify_email")))
            phone_input.clear()
            phone_input.send_keys(phone_number)
            time.sleep(2)
            
            search_btn = wait.until(EC.element_to_be_clickable((By.NAME, "did_submit")))
            search_btn.click()
            time.sleep(4)
            
            page_source = driver.page_source.lower()
            
            if self.is_captcha_present(driver):
                 driver.quit()
                 if window_id in self.drivers: del self.drivers[window_id]
                 return False, "Captcha"

            if "no search results" in page_source or "didn't match any account" in page_source:
                driver.quit()
                if window_id in self.drivers: del self.drivers[window_id]
                return False, "Not Found"
            
            self.handle_multi_account_selection(driver)
            self.handle_try_another_way(driver)
            
            if self.is_captcha_present(driver):
                 driver.quit()
                 if window_id in self.drivers: del self.drivers[window_id]
                 return False, "Captcha"
            
            if not self.select_sms_and_continue(driver):
                if self.is_captcha_present(driver):
                    driver.quit()
                    if window_id in self.drivers: del self.drivers[window_id]
                    return False, "Captcha"
                driver.quit()
                if window_id in self.drivers: del self.drivers[window_id]
                return False, "Failed (SMS option not found)"
            
            if self.check_success(driver):
                time.sleep(3)
                driver.quit()
                if window_id in self.drivers: del self.drivers[window_id]
                return True, "Successful"
            else:
                if self.is_captcha_present(driver):
                      driver.quit()
                      if window_id in self.drivers: del self.drivers[window_id]
                      return False, "Captcha"
                driver.quit()
                if window_id in self.drivers: del self.drivers[window_id]
                return False, "Failed"
                
        except Exception as e:
            try:
                driver.quit()
                if window_id in self.drivers: del self.drivers[window_id]
            except: pass
            return False, "Failed"
    
    def handle_multi_account_selection(self, driver):
        try:
            account_buttons = driver.find_elements(By.XPATH, "//a[contains(@class, '_42ft') and contains(text(), 'This is my account')]")
            if account_buttons:
                account_buttons[0].click()
                time.sleep(3)
                return True
            return False
        except: return False
    
    def handle_try_another_way(self, driver):
        try:
            try_another_elements = driver.find_elements(By.XPATH, "//a[contains(@href, 'tryanotherway') or contains(text(), 'Try another way')]")
            if try_another_elements:
                try_another_elements[0].click()
                time.sleep(3)
                return True
            return False
        except: return False
    
    def select_sms_and_continue(self, driver):
        try:
            sms_selected = False
            sms_selectors = ["//input[contains(@id, 'send_sms:')]", "//div[contains(text(),'Send code via SMS')]", "//span[contains(text(),'Send code via SMS')]"]
            for selector in sms_selectors:
                try:
                    sms_elements = driver.find_elements(By.XPATH, selector)
                    if sms_elements:
                        if "input" in selector:
                            radio_id = sms_elements[0].get_attribute("id")
                            if radio_id:
                                driver.find_element(By.XPATH, f"//label[@for='{radio_id}']").click()
                        else:
                            sms_elements[0].click()
                        time.sleep(2)
                        sms_selected = True
                        break
                except: continue
            
            if not sms_selected: return False 
            
            continue_selectors = ["//button[contains(@name, 'reset_action')]", "//button[contains(text(),'Continue')]", "//input[@value='Continue']"]
            for selector in continue_selectors:
                try:
                    continue_buttons = driver.find_elements(By.XPATH, selector)
                    if continue_buttons:
                        continue_buttons[0].click()
                        time.sleep(3)
                        return True
                except: continue
            return False 
        except: return False
    
    def check_success(self, driver):
        try:
            success_indicators = ["code has been sent", "sent to your phone", "recovery code", "check your phone", "sent to your mobile", "we sent a code"]
            page_text = driver.page_source.lower()
            return any(indicator in page_text for indicator in success_indicators)
        except: return False
    
    def process_batch(self, phone_numbers, batch_start):
        if self.stop_processing: return []
        batch_results = []
        threads = []
        
        def worker(phone_number, window_id):
            if self.stop_processing: return
            success, message = self.process_single_number(phone_number, window_id)
            with self.lock:
                batch_results.append({'phone_number': phone_number, 'success': success, 'message': message, 'window': window_id + 1})
        
        for i, phone_number in enumerate(phone_numbers):
            if self.stop_processing: break
            window_id = batch_start + i
            thread = threading.Thread(target=worker, args=(phone_number, window_id))
            threads.append(thread)
            thread.start()
            time.sleep(2) 
        
        for thread in threads: thread.join()
        return batch_results
    
    def stop_specific_process(self, window_id):
        driver_key = window_id - 1 
        driver = self.drivers.get(driver_key)
        if driver:
            try:
                driver.quit()
                del self.drivers[driver_key]
                return True
            except: return False
        return False

    def stop_all_processes(self):
        self.stop_processing = True
        for driver_key in list(self.drivers.keys()):
            try:
                self.drivers[driver_key].quit()
                del self.drivers[driver_key]
            except: pass
        self.drivers.clear()
        self.floating_manager.close_all_windows()

# --- GUI Class ---

class FacebookCodeSenderGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Facebook Code Sender - Professional Edition")
        self.root.geometry("950x750")
        
        self.license_manager = LicenseManager()
        self.floating_manager = FloatingWindowManager()
        self.sender = FacebookCodeSender(self.floating_manager)
        
        self.is_processing = False
        self.stop_processing_flag = False
        
        self.setup_ui()
        self.check_license_on_startup()
    
    def setup_ui(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        title_label = ttk.Label(main_frame, text="Facebook SMS Code Sender", font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        self.license_status = ttk.Label(main_frame, text="Checking license...", foreground="orange")
        self.license_status.grid(row=1, column=0, columnspan=3, pady=(0, 10))
        
        settings_frame = ttk.LabelFrame(main_frame, text="Settings", padding="10")
        settings_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        
        floating_check = ttk.Checkbutton(settings_frame, text="Enable Chrome Window (Starts Minimized)", 
                                         variable=self.floating_manager.floating_mode,
                                         command=lambda: self.update_floating_mode_state('floating'))
        floating_check.grid(row=0, column=0, sticky=tk.W, padx=(0, 20))
        
        background_check = ttk.Checkbutton(settings_frame, text="Run Chrome in Background (Headless)", 
                                           variable=self.floating_manager.background_mode,
                                           command=lambda: self.update_floating_mode_state('background'))
        background_check.grid(row=0, column=1, sticky=tk.W)
        
        ttk.Label(settings_frame, text="Max Chrome Windows:").grid(row=1, column=0, sticky=tk.W)
        self.max_windows = tk.StringVar(value="3")
        ttk.Spinbox(settings_frame, from_=1, to=5, width=5, textvariable=self.max_windows).grid(row=1, column=1, sticky=tk.W, padx=(5, 0))
        
        input_frame = ttk.LabelFrame(main_frame, text="Phone Numbers", padding="10")
        input_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        self.phone_text = scrolledtext.ScrolledText(input_frame, height=8, width=80)
        self.phone_text.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E))
        
        ttk.Button(input_frame, text="Insert Example Format", command=self.insert_example).grid(row=1, column=0, sticky=tk.W, pady=(5, 0))
        
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=4, column=0, columnspan=3, pady=(0, 10))
        
        self.start_button = ttk.Button(button_frame, text="Start Processing", command=self.start_processing)
        self.start_button.grid(row=0, column=0, padx=(0, 5))
        
        self.stop_button = ttk.Button(button_frame, text="Stop Processing", command=self.stop_processing, state=tk.DISABLED)
        self.stop_button.grid(row=0, column=1, padx=(0, 5))
        
        ttk.Button(button_frame, text="Clear Results", command=self.clear_results).grid(row=0, column=2, padx=(0, 5))
        ttk.Button(button_frame, text="Check License", command=self.check_license).grid(row=0, column=3)
        
        captcha_frame = ttk.LabelFrame(main_frame, text="Control Specific Window (Captchas)", padding="10")
        captcha_frame.grid(row=5, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        ttk.Label(captcha_frame, text="Window ID (e.g., 1, 2, 3):").grid(row=0, column=0, sticky=tk.W, padx=5)
        self.captcha_window_id = tk.StringVar()
        ttk.Entry(captcha_frame, textvariable=self.captcha_window_id, width=10).grid(row=0, column=1, padx=5)
        ttk.Button(captcha_frame, text="Stop Specific Window", command=self.handle_stop_specific_process).grid(row=0, column=2, padx=10)
        
        progress_frame = ttk.LabelFrame(main_frame, text="Progress & Stats", padding="10")
        progress_frame.grid(row=6, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        
        self.progress = ttk.Progressbar(progress_frame, mode='determinate')
        self.progress.grid(row=0, column=0, columnspan=4, sticky=(tk.W, tk.E))
        
        self.progress_label = ttk.Label(progress_frame, text="Ready", font=("Arial", 10))
        self.progress_label.grid(row=1, column=0, columnspan=4, pady=(5, 0))
        
        results_frame = ttk.LabelFrame(main_frame, text="Results", padding="10")
        results_frame.grid(row=7, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.results_text = scrolledtext.ScrolledText(results_frame, height=12, width=80)
        self.results_text.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(7, weight=1)
        input_frame.columnconfigure(0, weight=1)
        results_frame.columnconfigure(0, weight=1)
        results_frame.rowconfigure(0, weight=1)
        
        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN).grid(row=8, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(10, 0))
        
    def handle_stop_specific_process(self):
        try:
            window_id = int(self.captcha_window_id.get().strip())
            if window_id <= 0: return
            if self.sender.stop_specific_process(window_id):
                messagebox.showinfo("Process Stopped", f"Window {window_id} process stopped.")
                self.captcha_window_id.set("")
            else: messagebox.showerror("Error", f"Could not find process for Window {window_id}.")
        except: messagebox.showerror("Error", "Invalid Window ID")

    def update_floating_mode_state(self, changed_mode):
        if changed_mode == 'floating' and self.floating_manager.floating_mode.get():
            self.floating_manager.background_mode.set(False)
        elif changed_mode == 'background' and self.floating_manager.background_mode.get():
            self.floating_manager.floating_mode.set(False)
    
    def check_license_on_startup(self):
        def check():
            valid, message = self.license_manager.check_license()
            self.root.after(0, lambda: self.update_license_status(valid, message))
        threading.Thread(target=check, daemon=True).start()
    
    def update_license_status(self, valid, message):
        if valid:
            self.license_status.config(text=f"✅ {message}", foreground="green")
            self.start_button.config(state=tk.NORMAL)
        else:
            self.license_status.config(text=f"❌ {message}", foreground="red")
            self.start_button.config(state=tk.DISABLED)
            if "Key Generated" in message or "Expires" in message or "Server Data Error" in message:
                 messagebox.showinfo("License Info", message)

    def check_license(self):
        def check():
            valid, message = self.license_manager.check_license()
            self.root.after(0, lambda: self.show_license_message(valid, message))
        threading.Thread(target=check, daemon=True).start()
    
    def show_license_message(self, valid, message):
        if valid: messagebox.showinfo("License Check", f"✅ {message}")
        else: messagebox.showerror("License Check", f"❌ {message}")
    
    def insert_example(self):
        example = """+8801712345678\n+8801812345678"""
        self.phone_text.delete(1.0, tk.END)
        self.phone_text.insert(1.0, example)
    
    def start_processing(self):
        valid, message = self.license_manager.check_license()
        if not valid:
            messagebox.showerror("License Error", f"Cannot start: {message}")
            return
        
        numbers_text = self.phone_text.get(1.0, tk.END).strip()
        if not numbers_text:
            messagebox.showwarning("Input Error", "Enter phone numbers")
            return
        
        phone_numbers = [num.strip() for num in numbers_text.split('\n') if num.strip()]
        try: max_windows = min(int(self.max_windows.get()), 5)
        except: max_windows = 3
        
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.progress.config(maximum=len(phone_numbers))
        self.progress['value'] = 0
        self.results_text.delete(1.0, tk.END)
        
        self.sender = FacebookCodeSender(self.floating_manager)
        self.stop_processing_flag = False
        
        thread = threading.Thread(target=self.process_numbers, args=(phone_numbers, max_windows))
        thread.daemon = True
        thread.start()
    
    def stop_processing(self):
        self.stop_processing_flag = True
        self.sender.stop_all_processes()
        self.status_var.set("Stopping...")
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
    
    def clear_results(self):
        self.results_text.delete(1.0, tk.END)
    
    def process_numbers(self, phone_numbers, max_windows):
        try:
            self.root.after(0, lambda: self.status_var.set("Starting processing..."))
            processed_count = 0
            total_results = []
            
            for batch_start in range(0, len(phone_numbers), max_windows):
                if self.stop_processing_flag: break
                batch_end = min(batch_start + max_windows, len(phone_numbers))
                batch_numbers = phone_numbers[batch_start:batch_end]
                
                self.root.after(0, lambda: self.progress_label.config(text=f"Processing: {batch_start + 1}-{batch_end} / {len(phone_numbers)}"))
                
                batch_results = self.sender.process_batch(batch_numbers, batch_start)
                total_results.extend(batch_results)
                
                for result in batch_results:
                    processed_count += 1
                    self.root.after(0, lambda r=result, pc=processed_count: self.add_result_and_step(r, pc, total_results))
                
                if batch_end < len(phone_numbers) and not self.stop_processing_flag:
                    self.root.after(0, lambda: self.status_var.set("Preparing next batch..."))
                    time.sleep(3)
            
            self.root.after(0, lambda: self.processing_completed(total_results))
            
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Error", f"Processing error: {str(e)}"))
            self.root.after(0, lambda: self.processing_completed([]))
            
    def add_result_and_step(self, result, current_progress, total_results):
        self.add_result(result)
        self.progress['value'] = current_progress
        
        successful = sum(1 for r in total_results if r['message'] == 'Successful')
        not_found = sum(1 for r in total_results if r['message'] == 'Not Found')
        captcha = sum(1 for r in total_results if r['message'] == 'Captcha')
        failed = len(total_results) - successful - not_found - captcha
        
        stats = f"Done: {current_progress}/{self.progress['maximum']} | Success: {successful} | Not Found: {not_found} | Captcha: {captcha} | Failed: {failed}"
        self.progress_label.config(text=stats)

    def add_result(self, result):
        message = result['message']
        phone = result['phone_number']
        win = result['window']
        
        if message == "Successful": icon = "✅"
        elif message == "Captcha": icon = "⚠️"
        elif message == "Not Found": icon = "🚫"
        else: icon = "❌"
        
        mode_text = "Hidden" if self.floating_manager.background_mode.get() else f"Win {win}"
        text = f"{icon} {mode_text}: {phone} - {message}\n"
        self.results_text.insert(tk.END, text)
        self.results_text.see(tk.END)
    
    def processing_completed(self, total_results):
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.status_var.set("Processing completed")
        
        if total_results:
            successful = sum(1 for r in total_results if r['message'] == 'Successful')
            total = len(total_results)
            messagebox.showinfo("Completed", f"Completed!\nSuccess: {successful}\nTotal: {total}")

def main():
    root = tk.Tk()
    style = ttk.Style()
    style.theme_use('vista') 
    app = FacebookCodeSenderGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
