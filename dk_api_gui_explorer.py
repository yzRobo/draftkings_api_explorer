import tkinter as tk
from tkinter import scrolledtext, filedialog, messagebox, Menu, ttk
import threading
import queue
import json
import re
import os
import sys
from curl_cffi import requests as cffi_requests
import pandas as pd
from typing import Dict, Any, List, Tuple, Optional, Set
from collections import defaultdict, Counter

# --- HELPER FUNCTION FOR PYINSTALLER ---
def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

# --- REFERENCE DATA LOADER ---
def load_and_format_reference_data() -> List[Dict]:
    """Loads reference data from the bundled JSON file."""
    try:
        # Use resource_path to find the file in dev or in the bundled .exe
        path = resource_path('id_reference.json')
        with open(path, 'r') as f: 
            return json.load(f)
    except Exception as e:
        # If there's an error, we can show it for debugging
        messagebox.showerror("Error Loading Data", f"Could not load id_reference.json.\n\nError: {e}")
        return []

# --- DYNAMIC STRUCTURE ANALYZER ---
class StructureAnalyzer:
    """Analyzes API response structure to dynamically determine parsing strategy"""
    
    def __init__(self, data: Dict[str, Any], log_queue: queue.Queue):
        self.data = data
        self.log_queue = log_queue
        self.markets = data.get('markets', [])
        self.selections = data.get('selections', [])
        
    def analyze_structure(self) -> Dict[str, Any]:
        """Analyze the API response structure and return insights"""
        analysis = {
            'market_fields': self._analyze_market_fields(),
            'selection_fields': self._analyze_selection_fields(),
            'patterns': self._detect_patterns(),
            'relationships': self._analyze_relationships()
        }
        
        # Log key findings
        self.log_queue.put("\n--- API Structure Analysis ---")
        self.log_queue.put(f"Markets: {len(self.markets)} found")
        self.log_queue.put(f"Selections: {len(self.selections)} found")
        
        if self.markets:
            self.log_queue.put(f"Market fields: {', '.join(analysis['market_fields']['common_fields'])}")
        if self.selections:
            self.log_queue.put(f"Selection fields: {', '.join(analysis['selection_fields']['common_fields'])}")
        
        return analysis
    
    def _analyze_market_fields(self) -> Dict[str, Any]:
        """Analyze available fields in markets"""
        if not self.markets:
            return {'common_fields': [], 'sample_values': {}}
        
        # Get all unique fields across markets
        all_fields = set()
        field_samples = defaultdict(list)
        
        for market in self.markets[:10]:  # Sample first 10
            for field, value in market.items():
                all_fields.add(field)
                if value and len(field_samples[field]) < 3:
                    field_samples[field].append(str(value)[:50])  # Truncate long values
        
        return {
            'common_fields': sorted(list(all_fields)),
            'sample_values': dict(field_samples)
        }
    
    def _analyze_selection_fields(self) -> Dict[str, Any]:
        """Analyze available fields in selections"""
        if not self.selections:
            return {'common_fields': [], 'sample_values': {}}
        
        # Get all unique fields across selections
        all_fields = set()
        field_samples = defaultdict(list)
        
        for selection in self.selections[:20]:  # Sample first 20
            for field, value in selection.items():
                all_fields.add(field)
                if value and len(field_samples[field]) < 5:
                    field_samples[field].append(str(value)[:50])
        
        return {
            'common_fields': sorted(list(all_fields)),
            'sample_values': dict(field_samples)
        }
    
    def _detect_patterns(self) -> Dict[str, Any]:
        """Detect patterns in labels and market names"""
        patterns = {
            'label_patterns': Counter(),
            'market_name_patterns': [],
            'has_points': False,
            'has_participants': False
        }
        
        # Analyze selection labels
        for sel in self.selections:
            label = sel.get('label', '')
            if label:
                patterns['label_patterns'][label] += 1
            
            # Check for points field
            if sel.get('points') is not None:
                patterns['has_points'] = True
            
            # Check for participant fields
            for field in ['participantName', 'teamName', 'playerName', 'participant']:
                if sel.get(field):
                    patterns['has_participants'] = True
                    break
        
        # Analyze market name patterns
        for market in self.markets[:10]:
            name = market.get('name', '')
            if ' - ' in name:
                patterns['market_name_patterns'].append('dash_separator')
            if any(word in name.lower() for word in ['over', 'under', 'total']):
                patterns['market_name_patterns'].append('over_under')
            if 'regular season' in name.lower():
                patterns['market_name_patterns'].append('regular_season')
        
        return patterns
    
    def _analyze_relationships(self) -> Dict[str, Any]:
        """Analyze relationships between markets and selections"""
        relationships = {
            'market_to_selections': defaultdict(list),
            'unique_market_names': set(),
            'participant_extraction': {}
        }
        
        market_names = {m['id']: m.get('name', '') for m in self.markets}
        
        for sel in self.selections[:50]:  # Analyze first 50 selections
            market_id = sel.get('marketId')
            if market_id in market_names:
                market_name = market_names[market_id]
                relationships['unique_market_names'].add(market_name)
                
                # Try to extract participant from market name
                participant = self._extract_participant_from_market(market_name, sel)
                if participant:
                    relationships['participant_extraction'][market_name] = participant
        
        return relationships
    
    def _extract_participant_from_market(self, market_name: str, selection: Dict) -> Optional[str]:
        """Try to extract participant name from market name"""
        # First check if selection has direct participant field
        for field in ['participantName', 'teamName', 'playerName', 'participant', 'label']:
            if field in selection and selection[field] and field != 'label':
                return selection[field]
        
        # Try to extract from market name
        if ' - ' in market_name:
            return market_name.split(' - ')[0].strip()
        
        # For patterns like "Team Name Regular Season Wins"
        patterns = [
            r'^(.*?)\s+Regular Season',
            r'^(.*?)\s+Total',
            r'^(.*?)\s+to\s+',
            r'^(.*?)\s+Over',
            r'^(.*?)\s+Under'
        ]
        
        for pattern in patterns:
            match = re.match(pattern, market_name, re.IGNORECASE)
            if match:
                participant = match.group(1).strip()
                if len(participant) > 2:  # Avoid single letters
                    return participant
        
        return None

# --- ENHANCED DYNAMIC PARSER ---
class EnhancedDynamicParser:
    """Enhanced parser that uses event data for better team/player extraction"""
    
    def __init__(self, analysis: Dict[str, Any], markets_info: Dict[int, Dict], 
                 events_info: Dict[str, Dict], market_to_event: Dict[int, str]):
        self.analysis = analysis
        self.markets_info = markets_info
        self.events_info = events_info
        self.market_to_event = market_to_event
        
    def parse_selection(self, selection: Dict, market: Dict, market_type: str) -> Dict[str, Any]:
        """Parse a single selection with enhanced context"""
        result = {
            'Subject': 'N/A',
            'Proposition': 'N/A',
            'Odds': 'N/A'
        }
        
        # Extract odds
        odds = selection.get('displayOdds', {}).get('american', '')
        result['Odds'] = odds.replace('−', '-') if odds else 'N/A'
        
        # Extract basic info
        label = selection.get('label', '')
        points = selection.get('points')
        market_name = market.get('name', 'Unknown Market')
        market_id = market.get('id')
        
        # Handle division standings specially
        if market_type == "division_standings" and label in ['1st', '2nd', '3rd', '4th']:
            # Get team info from event
            event_id = self.market_to_event.get(market_id)
            if event_id and event_id in self.events_info:
                event = self.events_info[event_id]
                participants = event.get('participants', [])
                if participants:
                    team_name = participants[0].get('name', 'Unknown Team')
                    result['Subject'] = team_name
                    result['Proposition'] = f"{label} Place"
                    return result
        
        # Handle player props with Over/Under
        if market_type == "player_props" and label in ['Over', 'Under']:
            # Extract player from market name (e.g., "Josh Allen - Regular Season Passing Yards")
            if ' - ' in market_name:
                player_name = market_name.split(' - ')[0].strip()
                prop_type = market_name.split(' - ')[1].strip()
                result['Subject'] = player_name
                result['Proposition'] = f"{prop_type} - {label} {points}" if points else f"{prop_type} - {label}"
                return result
        
        # Handle threshold markets (e.g., "2750+")
        if market_type in ["threshold", "rookie_props"] and label.endswith('+'):
            # Extract player from market name
            if ' - ' in market_name:
                player_name = market_name.split(' - ')[0].strip()
                result['Subject'] = player_name
            else:
                result['Subject'] = "Any Player"  # Default if no player specified
            result['Proposition'] = f"{market_name} - {label}"
            return result
        
        # Standard Over/Under pattern
        if label in ['Over', 'Under'] and points is not None:
            # Extract subject from market name
            subject = self._extract_subject_from_market(market_name)
            result['Subject'] = subject
            result['Proposition'] = f"{label} {points}"
            return result
        
        # Default handling
        result['Subject'] = label
        result['Proposition'] = market_name
        
        return result
    
    def _extract_subject_from_market(self, market_name: str) -> str:
        """Extract subject (team/player) from market name"""
        # Pattern for "Team Name Regular Season Wins"
        patterns = [
            (r'^(.*?)\s+Regular Season', 1),
            (r'^(.*?)\s+-\s+', 1),
            (r'^(.*?)\s+Total', 1),
            (r'^(.*?)\s+to\s+', 1),
        ]
        
        for pattern, group in patterns:
            match = re.match(pattern, market_name, re.IGNORECASE)
            if match:
                subject = match.group(group).strip()
                if len(subject) > 2:  # Avoid single letters
                    return subject
        
        # If no pattern matches, return the full market name
        return market_name

# --- ENHANCED SCRAPER WITH DYNAMIC PARSING ---
def scrape_and_parse_draftkings(log_queue: queue.Queue, league_id: str, category_id: str, 
                                subcategory_id: str, save_raw: bool = False) -> Tuple[pd.DataFrame, str, Dict]:
    """Enhanced scraper with dynamic structure analysis"""
    log_queue.put(f"Scraping DraftKings API...")
    log_queue.put(f"  League ID: {league_id}, Category ID: {category_id}, Sub-Category ID: {subcategory_id or 'None'}")
    
    api_url = f"https://sportsbook-nash.draftkings.com/api/sportscontent/dkusoh/v1/leagues/{league_id}/categories/{category_id}"
    
    try:
        response = cffi_requests.get(api_url, impersonate="chrome110", timeout=30)
        response.raise_for_status()
        data = response.json()
        log_queue.put("  Successfully fetched data feed.")
        
        # Save raw data if requested
        if save_raw:
            with open(f"raw_data_{category_id}_{subcategory_id or 'all'}.json", 'w') as f:
                json.dump(data, f, indent=2)
            log_queue.put(f"  Saved raw data to file.")
        
        # Analyze structure
        analyzer = StructureAnalyzer(data, log_queue)
        analysis = analyzer.analyze_structure()
        
        # Extract all data structures
        all_markets = data.get('markets', [])
        all_selections = data.get('selections', [])
        all_events = data.get('events', [])
        
        if not all_markets:
            log_queue.put("  No markets found in response.")
            return pd.DataFrame(), "unknown", analysis
        
        # Create mappings for enrichment
        markets_info = {market['id']: market for market in all_markets}
        events_info = {event['id']: event for event in all_events}
        
        # Create market to event mapping
        market_to_event = {}
        for market in all_markets:
            if 'eventId' in market:
                market_to_event[market['id']] = market['eventId']
        
        # Filter markets by subcategory if provided
        if subcategory_id:
            filtered_markets = [m for m in all_markets if str(m.get('subcategoryId')) == subcategory_id]
        else:
            filtered_markets = all_markets
            
        filtered_market_ids = {m['id'] for m in filtered_markets}
        
        # Filter selections by market IDs
        filtered_selections = [sel for sel in all_selections if sel.get('marketId') in filtered_market_ids]
        
        if not filtered_selections:
            log_queue.put("  No selections found for the specified criteria.")
            return pd.DataFrame(), "unknown", analysis
        
        # Detect market type based on patterns
        market_type = _detect_market_type_from_analysis(analysis, category_id)
        log_queue.put(f"  Detected market type: {market_type}")
        
        # Create enhanced parser with event data
        parser = EnhancedDynamicParser(analysis, markets_info, events_info, market_to_event)
        results = []
        
        for sel in filtered_selections:
            market_id = sel.get('marketId')
            market = markets_info.get(market_id, {})
            market_name = market.get('name', 'Unknown Market')
            parsed = parser.parse_selection(sel, market, market_type)
            results.append(parsed)
        
        if not results:
            log_queue.put("  No valid betting selections parsed.")
            return pd.DataFrame(), market_type, analysis
            
        log_queue.put(f"  Parsed {len(results)} betting selections.")
        return pd.DataFrame(results), market_type, analysis
        
    except Exception as e:
        log_queue.put(f"ERROR: An error occurred.\nDetails: {e}")
        import traceback
        log_queue.put(f"Traceback: {traceback.format_exc()}")
        return pd.DataFrame(), "unknown", {}

def _detect_market_type_from_analysis(analysis: Dict[str, Any], category_id: str) -> str:
    """Detect market type from structure analysis"""
    patterns = analysis.get('patterns', {})
    label_counts = patterns.get('label_patterns', {})
    
    # Check label patterns
    total_labels = sum(label_counts.values())
    if total_labels > 0:
        over_under_ratio = (label_counts.get('Over', 0) + label_counts.get('Under', 0)) / total_labels
        if over_under_ratio > 0.8:
            # Check if it's player props based on category
            if category_id == "1759":
                return "player_props"
            return "over_under"
        
        ordinal_ratio = sum(label_counts.get(ord, 0) for ord in ['1st', '2nd', '3rd', '4th']) / total_labels
        if ordinal_ratio > 0.8:
            return "division_standings"
        
        # Check for threshold pattern
        threshold_count = sum(1 for label in label_counts if label.endswith('+'))
        if threshold_count > total_labels * 0.5:
            return "threshold"
    
    # Category-based detection
    if category_id == "1759":
        return "player_props"
    elif category_id == "1801":
        return "threshold"  # Rookie props are threshold type
    elif category_id == "820":
        return "division_standings"
    
    return "standard_futures"

# --- SMART PIVOT HANDLER ---
def apply_smart_formatting(df: pd.DataFrame, market_type: str, analysis: Dict) -> pd.DataFrame:
    """Apply smart formatting based on market type and structure"""
    if df.empty:
        return df
    
    if market_type == "over_under":
        # Check if we can pivot
        if 'Over' in df['Subject'].values or 'Under' in df['Subject'].values:
            # Wrong extraction - Subject contains Over/Under
            # Need to re-parse
            return df
        
        # Extract bet type and line from proposition
        df[['Bet', 'Line']] = df['Proposition'].str.extract(r'(Over|Under)\s+([\d.]+)', expand=True)
        
        if df['Bet'].notna().any():
            # Pivot the data
            pivot_df = df.pivot_table(
                index='Subject',
                columns='Bet',
                values=['Line', 'Odds'],
                aggfunc='first'
            ).reset_index()
            
            # Flatten columns
            pivot_df.columns = [' '.join(col).strip() if col[1] else col[0] for col in pivot_df.columns.values]
            
            # Rename and reorder
            column_mapping = {
                'Subject': 'Participant',
                'Line Over': 'Line',
                'Odds Over': 'Over Odds',
                'Odds Under': 'Under Odds'
            }
            pivot_df = pivot_df.rename(columns=column_mapping)
            
            # Select final columns
            final_cols = ['Participant', 'Line', 'Over Odds', 'Under Odds']
            available_cols = [col for col in final_cols if col in pivot_df.columns]
            
            return pivot_df[available_cols]
    
    return df

# --- GUI APPLICATION WITH ENHANCED FEATURES ---
class ScraperApp:
    def __init__(self, root):
        self.root = root
        self.root.title("DraftKings API Scraper - Dynamic Parser")
        self.root.geometry("950x700")
        
        menubar = Menu(root)
        root.config(menu=menubar)
        
        file_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Export Raw Data", command=self.export_raw_data)
        file_menu.add_command(label="View Structure Analysis", command=self.view_structure_analysis)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=root.quit)
        
        tools_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Tools", menu=tools_menu)
        tools_menu.add_command(label="Analyze API Structure", command=self.analyze_structure_only)
        
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(expand=True, fill='both', padx=10, pady=10)
        
        self.scraper_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.scraper_tab, text='Explorer')
        self.setup_scraper_tab()
        
        self.reference_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.reference_tab, text='ID Reference')
        self.setup_reference_tab()
        
        self.log_queue = queue.Queue()
        self.last_analysis = {}
        self.root.after(100, self.process_queue)

    def setup_scraper_tab(self):
        input_frame = tk.Frame(self.scraper_tab, padx=10, pady=10)
        input_frame.pack(fill=tk.X)
        
        # Input fields
        tk.Label(input_frame, text="League ID:", font=("Helvetica", 10, "bold")).grid(row=0, column=0, padx=5, pady=5, sticky='w')
        self.league_id_var = tk.StringVar(value="88808")
        tk.Entry(input_frame, textvariable=self.league_id_var, width=20).grid(row=0, column=1, padx=5, sticky='w')
        
        tk.Label(input_frame, text="Category ID:", font=("Helvetica", 10, "bold")).grid(row=1, column=0, padx=5, pady=5, sticky='w')
        self.category_id_var = tk.StringVar(value="")
        tk.Entry(input_frame, textvariable=self.category_id_var, width=20).grid(row=1, column=1, padx=5, sticky='w')
        
        tk.Label(input_frame, text="Sub-Category ID:", font=("Helvetica", 10, "bold")).grid(row=2, column=0, padx=5, pady=5, sticky='w')
        self.subcategory_id_var = tk.StringVar(value="")
        tk.Entry(input_frame, textvariable=self.subcategory_id_var, width=20).grid(row=2, column=1, padx=5, sticky='w')
        
        # Checkbox for saving raw data
        self.save_raw_var = tk.BooleanVar(value=False)
        tk.Checkbutton(input_frame, text="Save raw API response", variable=self.save_raw_var).grid(row=3, column=0, columnspan=2, pady=5)
        
        # Buttons
        button_frame = tk.Frame(input_frame)
        button_frame.grid(row=0, column=2, rowspan=4, padx=(20, 10), sticky='ns')
        
        self.scrape_button = tk.Button(button_frame, text="Grab Data", command=self.start_scraping_thread, 
                                      width=15, bg="#4CAF50", fg="white", font=("Helvetica", 10, "bold"))
        self.scrape_button.pack(pady=2, fill=tk.X)
        
        self.analyze_button = tk.Button(button_frame, text="Analyze Only", command=self.analyze_structure_only, 
                                       width=15, bg="#2196F3", fg="white")
        self.analyze_button.pack(pady=2, fill=tk.X)
        
        self.clear_button = tk.Button(button_frame, text="Clear Log", command=self.clear_log, width=15)
        self.clear_button.pack(pady=2, fill=tk.X)
        
        self.save_button = tk.Button(button_frame, text="Save Results...", command=self.save_results, 
                                    state=tk.DISABLED, width=15)
        self.save_button.pack(pady=2, fill=tk.X)
        
        # Status label
        self.status_label = tk.Label(input_frame, text="Ready to scrape", fg="gray")
        self.status_label.grid(row=4, column=0, columnspan=3, pady=5)
        
        # Log area
        log_frame = tk.Frame(self.scraper_tab, padx=10, pady=5)
        log_frame.pack(fill=tk.BOTH, expand=True)
        
        self.log_widget = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, state=tk.DISABLED, font=("Courier New", 9))
        self.log_widget.pack(fill=tk.BOTH, expand=True)

    def setup_reference_tab(self):
        ref_frame = tk.Frame(self.reference_tab, padx=10, pady=10)
        ref_frame.pack(fill=tk.BOTH, expand=True)
        
        self.ref_text_widget = scrolledtext.ScrolledText(ref_frame, wrap=tk.WORD, font=("Courier New", 10))
        self.ref_text_widget.pack(fill=tk.BOTH, expand=True)
        
        self.ref_text_widget.tag_config("clickable", foreground="blue", underline=True)
        self.ref_text_widget.tag_config("category", font=("Courier New", 11, "bold"))
        self.ref_text_widget.insert(tk.END, "DRAFTKINGS API CATEGORY REFERENCE\n", "category")
        self.ref_text_widget.insert(tk.END, "="*50 + "\n")
        self.ref_text_widget.insert(tk.END, "League ID for NFL: 88808\n", "category")
        self.ref_text_widget.insert(tk.END, "-"*50 + "\n")
        self.ref_text_widget.insert(tk.END, "Click any blue ID to auto-fill it on the Scraper tab.\n\n")
        
        reference_data = load_and_format_reference_data()
        for category in reference_data:
            cat_name = category['category_name']
            self.ref_text_widget.insert(tk.END, f"{cat_name}\n", "category")
            
            cat_id_match = re.search(r'ID: (\d+)', cat_name)
            if cat_id_match:
                cat_id = cat_id_match.group(1)
                tag_name = f"cat-{cat_id}"
                start_index = self.ref_text_widget.search(cat_id, "end-2l", "end")
                if start_index:
                    self.ref_text_widget.tag_add(tag_name, start_index, f"{start_index}+{len(cat_id)}c")
                    self.ref_text_widget.tag_add("clickable", start_index, f"{start_index}+{len(cat_id)}c")
                    self.ref_text_widget.tag_bind(tag_name, "<Button-1>", self.on_reference_click)
            
            for sub in category['subcategories']:
                self.ref_text_widget.insert(tk.END, f"  • {sub}\n")
                sub_id_match = re.search(r'ID: (\d+)', sub)
                if sub_id_match and cat_id_match:
                    sub_id = sub_id_match.group(1)
                    tag_name = f"sub-{sub_id}-parent-{cat_id}"
                    start_index = self.ref_text_widget.search(sub_id, "end-2l", "end")
                    if start_index:
                        self.ref_text_widget.tag_add(tag_name, start_index, f"{start_index}+{len(sub_id)}c")
                        self.ref_text_widget.tag_add("clickable", start_index, f"{start_index}+{len(sub_id)}c")
                        self.ref_text_widget.tag_bind(tag_name, "<Button-1>", self.on_reference_click)
            
            self.ref_text_widget.insert(tk.END, "\n")
        
        self.ref_text_widget.config(state=tk.DISABLED)

    def on_reference_click(self, event):
        index = self.ref_text_widget.index(f"@{event.x},{event.y}")
        tags = self.ref_text_widget.tag_names(index)
        
        for tag in tags:
            if tag.startswith("cat-"):
                self.category_id_var.set(tag.split('-')[1])
                self.subcategory_id_var.set("")
                self.status_label.config(text="Category ID set", fg="blue")
                break
            elif tag.startswith("sub-"):
                parts = tag.split('-')
                self.category_id_var.set(parts[3])
                self.subcategory_id_var.set(parts[1])
                self.status_label.config(text="Category and Sub-Category IDs set", fg="blue")
                break
        
        self.notebook.select(self.scraper_tab)

    def log_message(self, msg):
        self.log_widget.config(state=tk.NORMAL)
        self.log_widget.insert(tk.END, f"{msg}\n")
        self.log_widget.config(state=tk.DISABLED)
        self.log_widget.see(tk.END)

    def process_queue(self):
        try:
            while True:
                self.log_message(self.log_queue.get_nowait())
        except queue.Empty:
            pass
        finally:
            self.root.after(100, self.process_queue)

    def start_scraping_thread(self):
        self.scrape_button.config(state=tk.DISABLED, bg="#FFA500")
        self.save_button.config(state=tk.DISABLED)
        self.status_label.config(text="Scraping in progress...", fg="orange")
        
        self.log_message("\n" + "="*50)
        self.log_message("--- New Scraping Request ---")
        self.scraped_df = None
        
        league_id = self.league_id_var.get().strip()
        category_id = self.category_id_var.get().strip()
        subcategory_id = self.subcategory_id_var.get().strip()
        save_raw = self.save_raw_var.get()
        
        if not league_id or not category_id:
            self.log_message("ERROR: League ID and Category ID cannot be empty.")
            self.scrape_button.config(state=tk.NORMAL, bg="#4CAF50")
            self.status_label.config(text="Error: Missing required fields", fg="red")
            return
        
        threading.Thread(target=self.run_scraping_logic, 
                        args=(league_id, category_id, subcategory_id, save_raw), 
                        daemon=True).start()

    def run_scraping_logic(self, league_id, category_id, subcategory_id, save_raw):
        raw_df, market_type, analysis = scrape_and_parse_draftkings(
            self.log_queue, league_id, category_id, subcategory_id, save_raw
        )
        
        self.last_analysis = analysis
        
        if raw_df.empty:
            self.log_queue.put("Scraping finished with no results.")
            self.scrape_button.config(state=tk.NORMAL, bg="#4CAF50")
            self.status_label.config(text="No data found", fg="red")
            return
        
        # Apply smart formatting
        self.log_queue.put(f"\nApplying smart formatting for {market_type} market...")
        self.scraped_df = apply_smart_formatting(raw_df, market_type, analysis)
        
        if self.scraped_df.empty:
            self.log_queue.put("Processing finished with no results.")
            self.scrape_button.config(state=tk.NORMAL, bg="#4CAF50")
            self.status_label.config(text="Processing failed", fg="red")
            return
        
        self.log_queue.put("\n--- Scraping Complete ---")
        self.log_queue.put(f"Market Type: {market_type}")
        self.log_queue.put(f"Total Rows: {len(self.scraped_df)}")
        self.log_queue.put(f"\n{self.scraped_df.to_string()}")
        self.log_queue.put("="*50 + "\n")
        
        self.scrape_button.config(state=tk.NORMAL, bg="#4CAF50")
        self.save_button.config(state=tk.NORMAL)
        self.status_label.config(text=f"Success! {len(self.scraped_df)} rows retrieved ({market_type})", fg="green")

    def analyze_structure_only(self):
        """Run structure analysis without full parsing"""
        league_id = self.league_id_var.get().strip()
        category_id = self.category_id_var.get().strip()
        
        if not league_id or not category_id:
            messagebox.showerror("Error", "League ID and Category ID are required for analysis.")
            return
        
        self.log_message("\n--- Running Structure Analysis Only ---")
        threading.Thread(target=self._run_analysis_only, 
                        args=(league_id, category_id), 
                        daemon=True).start()
    
    def _run_analysis_only(self, league_id, category_id):
        """Thread function for structure analysis"""
        api_url = f"https://sportsbook-nash.draftkings.com/api/sportscontent/dkusoh/v1/leagues/{league_id}/categories/{category_id}"
        
        try:
            response = cffi_requests.get(api_url, impersonate="chrome110", timeout=30)
            response.raise_for_status()
            data = response.json()
            
            analyzer = StructureAnalyzer(data, self.log_queue)
            analysis = analyzer.analyze_structure()
            self.last_analysis = analysis
            
            # Display detailed analysis
            self.log_queue.put("\n--- Detailed Structure Report ---")
            self.log_queue.put(f"Total markets: {len(data.get('markets', []))}")
            self.log_queue.put(f"Total selections: {len(data.get('selections', []))}")
            
            # Show sample selection with all fields
            if data.get('selections'):
                self.log_queue.put("\nSample Selection (first item):")
                sample = data['selections'][0]
                for key, value in sample.items():
                    self.log_queue.put(f"  {key}: {value}")
            
            # Show sample market with all fields
            if data.get('markets'):
                self.log_queue.put("\nSample Market (first item):")
                sample = data['markets'][0]
                for key, value in sample.items():
                    self.log_queue.put(f"  {key}: {value}")
            
            self.log_queue.put("\nAnalysis complete. Use 'View Structure Analysis' menu for full details.")
            
        except Exception as e:
            self.log_queue.put(f"ERROR during analysis: {e}")

    def view_structure_analysis(self):
        """View the last structure analysis in a new window"""
        if not self.last_analysis:
            messagebox.showinfo("No Analysis", "No structure analysis available. Run a scrape or analysis first.")
            return
        
        # Create new window
        analysis_window = tk.Toplevel(self.root)
        analysis_window.title("Structure Analysis Details")
        analysis_window.geometry("600x500")
        
        # Create text widget with scrollbar
        text_frame = tk.Frame(analysis_window)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        text_widget = scrolledtext.ScrolledText(text_frame, wrap=tk.WORD, font=("Courier New", 10))
        text_widget.pack(fill=tk.BOTH, expand=True)
        
        # Display analysis
        text_widget.insert(tk.END, "=== API STRUCTURE ANALYSIS ===\n\n")
        
        # Market fields
        if 'market_fields' in self.last_analysis:
            fields_info = self.last_analysis['market_fields']
            text_widget.insert(tk.END, "MARKET FIELDS:\n")
            text_widget.insert(tk.END, f"Fields: {', '.join(fields_info.get('common_fields', []))}\n\n")
            
            text_widget.insert(tk.END, "Sample values:\n")
            for field, samples in fields_info.get('sample_values', {}).items():
                text_widget.insert(tk.END, f"  {field}: {samples[0] if samples else 'N/A'}\n")
            text_widget.insert(tk.END, "\n")
        
        # Selection fields
        if 'selection_fields' in self.last_analysis:
            fields_info = self.last_analysis['selection_fields']
            text_widget.insert(tk.END, "SELECTION FIELDS:\n")
            text_widget.insert(tk.END, f"Fields: {', '.join(fields_info.get('common_fields', []))}\n\n")
            
            text_widget.insert(tk.END, "Sample values:\n")
            for field, samples in fields_info.get('sample_values', {}).items():
                text_widget.insert(tk.END, f"  {field}: {samples[:2]}\n")
            text_widget.insert(tk.END, "\n")
        
        # Patterns
        if 'patterns' in self.last_analysis:
            patterns = self.last_analysis['patterns']
            text_widget.insert(tk.END, "DETECTED PATTERNS:\n")
            
            label_patterns = patterns.get('label_patterns', {})
            if label_patterns:
                text_widget.insert(tk.END, "Label distribution:\n")
                for label, count in sorted(label_patterns.items(), key=lambda x: x[1], reverse=True)[:10]:
                    text_widget.insert(tk.END, f"  {label}: {count} occurrences\n")
            
            text_widget.insert(tk.END, f"\nHas points field: {patterns.get('has_points', False)}\n")
            text_widget.insert(tk.END, f"Has participant fields: {patterns.get('has_participants', False)}\n")
        
        text_widget.config(state=tk.DISABLED)
        
        # Add close button
        close_button = tk.Button(analysis_window, text="Close", command=analysis_window.destroy)
        close_button.pack(pady=10)

    def export_raw_data(self):
        """Export the last raw API response"""
        if not hasattr(self, 'scraped_df') or self.scraped_df is None:
            messagebox.showinfo("No Data", "No data available. Run a scrape first.")
            return
        
        filepath = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")],
            title="Export Raw API Data"
        )
        
        if filepath:
            messagebox.showinfo("Info", "Raw data export requires re-fetching. This will take a moment...")
            # Re-run with save_raw=True would be needed here

    def save_results(self):
        if self.scraped_df is None or self.scraped_df.empty:
            messagebox.showerror("Error", "No data to save.")
            return
        
        filepath = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("Excel files", "*.xlsx")],
            title="Save Scraped Data"
        )
        
        if not filepath:
            self.log_message("Save operation cancelled.")
            return
        
        try:
            if filepath.endswith('.xlsx'):
                self.scraped_df.to_excel(filepath, index=False)
            else:
                self.scraped_df.to_csv(filepath, index=False)
            
            self.log_message(f"\nSuccessfully saved results to: {filepath}")
            messagebox.showinfo("Success", f"Data saved successfully to:\n{filepath}")
            self.status_label.config(text=f"Saved to {filepath.split('/')[-1]}", fg="green")
        except Exception as e:
            self.log_message(f"ERROR saving file: {e}")
            messagebox.showerror("Save Error", f"An error occurred: {e}")
    
    def clear_log(self):
        self.log_widget.config(state=tk.NORMAL)
        self.log_widget.delete('1.0', tk.END)
        self.log_widget.config(state=tk.DISABLED)
        self.save_button.config(state=tk.DISABLED)
        self.scraped_df = None
        self.last_analysis = {}
        self.status_label.config(text="Log cleared", fg="gray")
        self.log_message("--- Log Cleared ---")

if __name__ == "__main__":
    root = tk.Tk()
    app = ScraperApp(root)
    root.mainloop()
