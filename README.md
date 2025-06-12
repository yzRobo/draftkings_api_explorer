# DraftKings NFL Futures Data Viewer (GUI)

This Python GUI application retrieves and displays NFL futures data from the DraftKings API. It is designed to help users easily extract and organize betting market information, such as Regular Season Wins, Awards, Player Props, and more.

---

## Features

- **Graphical User Interface (GUI)** using Tkinter
- Supports multiple market categories including:
  - Wins
  - Futures
  - Awards
  - Player Futures
  - Rookie Watch
  - Stat Leaders
  - Playoffs
  - Division Specials
  - Team Specials
  - Game-Specific Props
- **Data parsing and pivoting** for Over/Under markets
- **Export to CSV**
- **Built-in ID reference** for league, category, and subcategory IDs
- Designed to work with the **DraftKings NFL League ID** (`88808`)

---

## Dependencies

- `tkinter` (included with most Python installations)
- `pandas`
- `curl_cffi`

Install dependencies using pip:

```bash
pip install pandas curl_cffi
```

---

## Setup

It’s recommended to use a virtual environment:

### macOS/Linux

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Windows

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

To deactivate:

```bash
deactivate
```

---

## Usage

Run the GUI:

```bash
python dk_api_gui_explorer.py
```

### Viewer Tab

1. **Input Fields:**
   - League ID (e.g., `88808` for NFL)
   - Category ID (e.g., `1286`)
   - Sub-Category ID (e.g., `17455`)
2. **Click “Grab Data”** to retrieve market data from DraftKings.
3. The data will be displayed in the log window.
4. Click “Save Results” to export the latest data to a CSV file.

### ID Reference Tab

- Browse through categories and subcategories with corresponding IDs.
- Click any ID entry to auto-populate the Viewer tab’s input fields.

---

## Output Example

Example of parsed betting market data:

```
--- New Data Request ---
Fetching data from DraftKings...
  League ID: 88808, Category ID: 1286, Sub-Category ID: 17455
  Successfully fetched data feed.
  Parsed 64 betting selections.
--- Request Complete ---

Participant   Line  Over Odds  Under Odds
-----------  -----  ---------  ----------
Dolphins     10.5   +150       -170
Patriots     7.5    +100       -120
...
```

---

## Notes

- The app uses **regex parsing** to extract numeric IDs and betting labels (e.g., "Over", "Under") from titles.
- Markets like "Regular Season Wins" are automatically **pivoted into a readable format** with `Participant`, `Line`, `Over Odds`, and `Under Odds` columns.
- The application works for **any DraftKings market** with the correct combination of IDs.

---

## ID Reference Format

The `id_reference.json` file contains league market categories and subcategories. Example:

```json
[
  {
    "category_name": "WINS (Category ID: 1286)",
    "subcategories": [
      "Regular Season Wins (ID: 17455)",
      "Most Wins (ID: 13365)",
      "Fewest Wins (ID: 13367)"
    ]
  },
  {
    "category_name": "AWARDS (Category ID: 787)",
    "subcategories": [
      "MVP (ID: 13339)",
      "OPOY (ID: 13340)"
    ]
  }
]
```

The IDs are automatically extracted using regex when clicked, and populate the Viewer tab.

---

## File Structure

```
.
├── dk_api_gui_explorer.py   # Main script with GUI
├── id_reference.json        # Local file for category/subcategory reference
├── requirements.txt         # (Optional) Dependency list
└── README.md
```

---

## Coming Soon / To Do

- Correct Formatting of more API categories to ensure output looks correct
- Add support for retrieving data across multiple subcategory IDs
- Improve error handling and logging granularity

---

## License

This project is open source under the MIT License.

---

## Author

yzRobo
