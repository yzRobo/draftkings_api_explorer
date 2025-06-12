# DraftKings NFL API Data Viewer

This Python GUI application retrieves and displays NFL futures data from the DraftKings API. It is designed to help users easily extract and organize betting market information, such as Regular Season Wins, Awards, Player Props, and more.

---

## How to Run

There are three ways to use this application, depending on your preference.

### Option 1: Standalone Program (Recommended for Windows)

For most users, the easiest method is to use the pre-built `.exe` file. No Python installation is needed.

1.  Go to the [Releases page](https://github.com/yzRobo/draftkings_api_explorer/releases) on GitHub.
2.  Download the `DK_API_Scraper_vX.X.X.exe` file from the latest release.
3.  Run the downloaded file.

---

### Option 2: Running from Source (with `run.bat` for Windows)

This option is for users who download the source code and want a simple way to run it on Windows without using the command line.

1.  Make sure you have Python installed on your system.
2.  Download or clone the project repository.
3.  Install the required dependencies by opening a terminal or command prompt in the project folder and running:
    ```bash
    pip install -r requirements.txt
    ```
4.  Once dependencies are installed, simply double-click the `run.bat` file to start the application.

---

### Option 3: Running from Source (Manual)

This method works for all operating systems (Windows, macOS, Linux) and is the standard way to run a Python application from source.

1.  Ensure you have Python installed.
2.  Download or clone the project repository.
3.  It is highly recommended to create and activate a virtual environment:
    ```bash
    # For Windows
    python -m venv venv
    venv\Scripts\activate

    # For macOS/Linux
    python3 -m venv venv
    source venv/bin/activate
    ```
4.  Install the required dependencies:
    ```bash
    pip install -r requirements.txt
    ```
5.  Run the application from your terminal:
    ```bash
    python dk_api_gui_explorer.py
    ```

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

---

### Explorer Tab

![explorer](https://github.com/user-attachments/assets/98c478d7-3d9b-4a04-a3c9-0821de81ca19)

1. **Input Fields:**
   - League ID (e.g., `88808` for NFL)
   - Category ID (e.g., `1286`)
   - Sub-Category ID (e.g., `17455`)
2. **Click “Grab Data”** to retrieve market data from DraftKings.
3. The data will be displayed in the log window.
4. Click “Save Results” to export the latest data to a CSV file.

### ID Reference Tab

![id_reference](https://github.com/user-attachments/assets/b8388e0a-2085-42ee-9373-89b3f8c83a60)

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
draftkings_api_explorer/
│
├── .gitignore               # Specifies intentionally untracked files to ignore
├── config.json              # Configuration file for API endpoints
├── dk_api_gui_explorer.py   # The main application script with the GUI
├── id_reference.json        # Reference data for market categories and IDs
├── LICENSE                  # The MIT License for the project
├── README.md                # The project's documentation file
└── requirements.txt         # A list of the Python packages required
```

---

## Coming Soon / To Do

- Correct Formatting of more API categories to ensure output looks correct
- Add support for retrieving data across multiple subcategory IDs

---

## License

This project is open source under the MIT License.

---

## Author

yzRobo
