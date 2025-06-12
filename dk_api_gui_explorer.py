import tkinter as tk
from tkinter import scrolledtext, filedialog, messagebox, Menu, ttk
import threading
import queue
import json
import re
from curl_cffi import requests as cffi_requests
import pandas as pd
from typing import Dict, Any, List

# --- REFERENCE DATA LOADER ---
def load_and_format_reference_data() -> List[Dict]:
    try:
        with open('id_reference.json', 'r') as f: return json.load(f)
    except Exception: return []

# --- ROBUST GENERIC SCRAPER & PARSER ---
def scrape_and_parse_draftkings(log_queue: queue.Queue, league_id: str, category_id: str, subcategory_id: str) -> pd.DataFrame:
    log_queue.put(f"Scraping DraftKings API...")
    log_queue.put(f"  League ID: {league_id}, Category ID: {category_id}, Sub-Category ID: {subcategory_id or 'None'}")
    api_url = f"https://sportsbook-nash.draftkings.com/api/sportscontent/dkusoh/v1/leagues/{league_id}/categories/{category_id}"
    
    try:
        response = cffi_requests.get(api_url, impersonate="chrome110", timeout=30)
        response.raise_for_status(); data = response.json(); log_queue.put("  Successfully fetched data feed.")

        all_markets = data.get('markets', [])
        markets_info = {market['id']: market['name'] for market in all_markets}
        filtered_market_ids = {m['id'] for m in all_markets if not subcategory_id or str(m.get('subcategoryId')) == subcategory_id}
        
        results = []
        for sel in data.get('selections', []):
            market_id = sel.get('marketId')
            if market_id not in filtered_market_ids: continue

            market_name = markets_info.get(market_id, "N/A")
            
            subject = "N/A"; proposition = "N/A"

            # This universal parser correctly identifies the subject and proposition for all market types
            if sel.get('label') in ['Over', 'Under']:
                subject = re.sub(r'\s+Regular Season.*', '', market_name).strip()
                proposition = f"{sel.get('label')} {sel.get('points')}"
            elif "Finishing Position" in market_name:
                subject = sel.get('label')
                position = sel.get('points')
                if position is not None:
                    position_suffix = {1: "st", 2: "nd", 3: "rd"}.get(int(position), "th")
                    proposition = f"Finish {int(position)}{position_suffix}"
                else: proposition = "N/A"
            else:
                subject = sel.get('label'); proposition = market_name

            results.append({
                'Subject': subject,
                'Proposition': proposition,
                'Odds': sel.get('displayOdds', {}).get('american', '').replace('−', '-')
            })
            
        if not results: log_queue.put("NOTE: No bets found for this combination.")
        log_queue.put(f"  Parsed {len(results)} betting selections.")
        return pd.DataFrame(results)
    except Exception as e:
        log_queue.put(f"ERROR: An error occurred.\nDetails: {e}"); return pd.DataFrame()

# --- GUI APPLICATION ---
class ScraperApp:
    def __init__(self, root):
        self.root = root; self.root.title("DraftKings API Scraper"); self.root.geometry("800x600")
        menubar = Menu(root); root.config(menu=menubar)
        file_menu = Menu(menubar, tearoff=0); menubar.add_cascade(label="File", menu=file_menu); file_menu.add_command(label="Exit", command=root.quit)
        self.notebook = ttk.Notebook(root); self.notebook.pack(expand=True, fill='both', padx=10, pady=10)
        self.scraper_tab = ttk.Frame(self.notebook); self.notebook.add(self.scraper_tab, text='Scraper'); self.setup_scraper_tab()
        self.reference_tab = ttk.Frame(self.notebook); self.notebook.add(self.reference_tab, text='ID Reference'); self.setup_reference_tab()
        self.log_queue = queue.Queue(); self.root.after(100, self.process_queue)

    def setup_scraper_tab(self):
        input_frame = tk.Frame(self.scraper_tab, padx=10, pady=10); input_frame.pack(fill=tk.X)
        tk.Label(input_frame, text="League ID:", font=("Helvetica", 10, "bold")).grid(row=0, column=0, padx=5, pady=5, sticky='w')
        self.league_id_var = tk.StringVar(value="88808"); tk.Entry(input_frame, textvariable=self.league_id_var, width=20).grid(row=0, column=1, padx=5, sticky='w')
        tk.Label(input_frame, text="Category ID:", font=("Helvetica", 10, "bold")).grid(row=1, column=0, padx=5, pady=5, sticky='w')
        self.category_id_var = tk.StringVar(value=""); tk.Entry(input_frame, textvariable=self.category_id_var, width=20).grid(row=1, column=1, padx=5, sticky='w')
        tk.Label(input_frame, text="Sub-Category ID (Optional):", font=("Helvetica", 10, "bold")).grid(row=2, column=0, padx=5, pady=5, sticky='w')
        self.subcategory_id_var = tk.StringVar(value=""); tk.Entry(input_frame, textvariable=self.subcategory_id_var, width=20).grid(row=2, column=1, padx=5, sticky='w')
        
        button_frame = tk.Frame(input_frame); button_frame.grid(row=0, column=2, rowspan=3, padx=(20, 10), sticky='ns')
        self.scrape_button = tk.Button(button_frame, text="Grab Data", command=self.start_scraping_thread, width=15); self.scrape_button.pack(pady=2, fill=tk.X)
        self.clear_button = tk.Button(button_frame, text="Clear Log", command=self.clear_log, width=15); self.clear_button.pack(pady=2, fill=tk.X)
        self.save_button = tk.Button(button_frame, text="Save Results...", command=self.save_results, state=tk.DISABLED, width=15); self.save_button.pack(pady=2, fill=tk.X)
        
        log_frame = tk.Frame(self.scraper_tab, padx=10, pady=5); log_frame.pack(fill=tk.BOTH, expand=True)
        self.log_widget = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, state=tk.DISABLED, font=("Courier New", 9)); self.log_widget.pack(fill=tk.BOTH, expand=True)

    def setup_reference_tab(self):
        ref_frame = tk.Frame(self.reference_tab, padx=10, pady=10); ref_frame.pack(fill=tk.BOTH, expand=True)
        self.ref_text_widget = scrolledtext.ScrolledText(ref_frame, wrap=tk.WORD, font=("Courier New", 10)); self.ref_text_widget.pack(fill=tk.BOTH, expand=True)
        self.ref_text_widget.tag_config("clickable", foreground="blue", underline=True)
        self.ref_text_widget.insert(tk.END, "DRAFTKINGS API CATEGORY REFERENCE\n=================================\nLeague ID for NFL: 88808\n")
        self.ref_text_widget.insert(tk.END, "---------------------------------\nNOTE: Click any blue ID to auto-fill it on the Scraper tab.\n")
        reference_data = load_and_format_reference_data()
        for category in reference_data:
            cat_name = category['category_name']; self.ref_text_widget.insert(tk.END, f"\n{cat_name}\n")
            cat_id_match = re.search(r'ID: (\d+)', cat_name)
            if cat_id_match:
                cat_id = cat_id_match.group(1); tag_name = f"cat-{cat_id}"; start_index = self.ref_text_widget.search(cat_id, "end-2l", "end")
                if start_index: self.ref_text_widget.tag_add(tag_name, start_index, f"{start_index}+{len(cat_id)}c"); self.ref_text_widget.tag_add("clickable", start_index, f"{start_index}+{len(cat_id)}c"); self.ref_text_widget.tag_bind(tag_name, "<Button-1>", self.on_reference_click)
            for sub in category['subcategories']:
                self.ref_text_widget.insert(tk.END, f"  - {sub}\n")
                sub_id_match = re.search(r'ID: (\d+)', sub)
                if sub_id_match and cat_id_match:
                    sub_id = sub_id_match.group(1); tag_name = f"sub-{sub_id}-parent-{cat_id}"
                    start_index = self.ref_text_widget.search(sub_id, "end-2l", "end")
                    if start_index: self.ref_text_widget.tag_add(tag_name, start_index, f"{start_index}+{len(sub_id)}c"); self.ref_text_widget.tag_add("clickable", start_index, f"{start_index}+{len(sub_id)}c"); self.ref_text_widget.tag_bind(tag_name, "<Button-1>", self.on_reference_click)
        self.ref_text_widget.config(state=tk.DISABLED)

    def on_reference_click(self, event):
        index = self.ref_text_widget.index(f"@{event.x},{event.y}"); tags = self.ref_text_widget.tag_names(index)
        for tag in tags:
            if tag.startswith("cat-"): self.category_id_var.set(tag.split('-')[1]); self.subcategory_id_var.set(""); break
            elif tag.startswith("sub-"): parts = tag.split('-'); self.category_id_var.set(parts[3]); self.subcategory_id_var.set(parts[1]); break
        self.notebook.select(self.scraper_tab)

    def log_message(self, msg):
        self.log_widget.config(state=tk.NORMAL); self.log_widget.insert(tk.END, f"{msg}\n"); self.log_widget.config(state=tk.DISABLED); self.log_widget.see(tk.END)

    def process_queue(self):
        try:
            while True: self.log_message(self.log_queue.get_nowait())
        except queue.Empty: pass
        finally: self.root.after(100, self.process_queue)

    def start_scraping_thread(self):
        self.scrape_button.config(state=tk.DISABLED); self.save_button.config(state=tk.DISABLED)
        self.log_message("\n--- New Scraping Request ---"); self.scraped_df = None
        league_id = self.league_id_var.get().strip(); category_id = self.category_id_var.get().strip(); subcategory_id = self.subcategory_id_var.get().strip()
        if not league_id or not category_id:
            self.log_message("ERROR: League ID and Category ID cannot be empty."); self.scrape_button.config(state=tk.NORMAL); return
        threading.Thread(target=self.run_scraping_logic, args=(league_id, category_id, subcategory_id), daemon=True).start()

    def run_scraping_logic(self, league_id, category_id, subcategory_id):
        raw_df = scrape_and_parse_draftkings(self.log_queue, league_id, category_id, subcategory_id)
        if raw_df.empty:
            self.log_queue.put("Scraping finished with no results."); self.scrape_button.config(state=tk.NORMAL); return
        
        # --- THE INTELLIGENT DISPATCHER ---
        is_over_under = raw_df['Proposition'].str.match(r'^(Over|Under)\s\d+(\.\d+)?$').all()
        
        if is_over_under:
            self.log_queue.put("  Pattern detected: Over/Under. Applying pivot format...")
            # --- THE FIX IS HERE ---
            # Correctly split the proposition into Bet and Line columns
            split_data = raw_df['Proposition'].str.split(' ', n=1, expand=True)
            raw_df['Bet'] = split_data[0]
            raw_df['Line'] = split_data[1]
            
            pivot_df = raw_df.pivot_table(index='Subject', columns='Bet', values=['Line', 'Odds'], aggfunc='first').reset_index()
            pivot_df.columns = [' '.join(col).strip() for col in pivot_df.columns.values]
            self.scraped_df = pivot_df.rename(columns={
                'Subject': 'Participant', 'Line Over': 'Line', 'Odds Over': 'Over Odds', 'Odds Under': 'Under Odds'
            })[['Participant', 'Line', 'Over Odds', 'Under Odds']]
        else:
            self.log_queue.put("  Pattern detected: Generic Futures. Applying standard format...")
            self.scraped_df = raw_df
        
        if self.scraped_df.empty:
            self.log_queue.put("Processing finished with no results."); self.scrape_button.config(state=tk.NORMAL); return
        self.log_queue.put("\n--- Scraping Complete ---"); self.log_queue.put(f"\n{self.scraped_df.to_string()}")
        self.scrape_button.config(state=tk.NORMAL); self.save_button.config(state=tk.NORMAL)

    def save_results(self):
        if self.scraped_df is None or self.scraped_df.empty: messagebox.showerror("Error", "No data to save."); return
        filepath = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")], title="Save Scraped Data")
        if not filepath: self.log_message("Save operation cancelled."); return
        try:
            self.scraped_df.to_csv(filepath, index=False); self.log_message(f"\nSuccessfully saved results to: {filepath}"); messagebox.showinfo("Success", f"Data saved successfully to:\n{filepath}")
        except Exception as e:
            self.log_message(f"ERROR saving file: {e}"); messagebox.showerror("Save Error", f"An error occurred: {e}")
    
    def clear_log(self):
        self.log_widget.config(state=tk.NORMAL); self.log_widget.delete('1.0', tk.END); self.log_widget.config(state=tk.DISABLED)
        self.save_button.config(state=tk.DISABLED); self.scraped_df = None; self.log_message("--- Log Cleared ---")
        
if __name__ == "__main__":
    root = tk.Tk()
    app = ScraperApp(root)
    root.mainloop()