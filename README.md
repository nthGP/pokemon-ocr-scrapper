# Pokémon OCR Scraper

This project is an **Optical Character Recognition (OCR) scraper** for PokeMMO designed to extract Pokémon data from images and save the results to a CSV file. It's able to scan images taken from the ingame PC like this:


![Pokémon OCR Scraper Preview](https://imgur.com/rZCkMOz.png)

## Features

- Detects Shiny, Alpha, and Hidden Ability icons from Pokémon images.
- Extracts Pokémon names, levels, IVs, EVs, Natures, Abilities, and Moves using OCR.
- Saves the extracted data into a CSV format to easily insert into the spreadsheet

## Requirements

- Python 3.x
- Libraries: `opencv-python`, `pytesseract`, `pillow`, `unidecode`, `numpy`

## Installation

### Step 1: Download the Project

To get started, you can download the project files from the repository:

1. Click on the green **Code** button.
2. Select **Download ZIP**.
3. Extract the downloaded ZIP file to your desired directory.

### Step 2: Install Python and Required Libraries

Ensure you have Python installed (version 3.7 or higher is recommended). If you don't have Python installed, you can download it from the official [Python website](https://www.python.org/downloads/).

After downloading the project, navigate to the project folder in your terminal or command prompt and run the following commands to install the required Python libraries:

```bash
pip install opencv-python numpy pillow pytesseract unidecode
```

### Step 3: Install Tesseract OCR

This project uses the Tesseract OCR engine for text extraction from images. You need to install Tesseract separately based on your operating system:

- **Windows**: Download and install the latest version from [UB Mannheim Tesseract](https://github.com/UB-Mannheim/tesseract/wiki).
- **macOS**: Use Homebrew to install Tesseract by running the following command:

```bash
brew install tesseract
```
  
- **Linux**: Install Tesseract using your package manager. For example, on Ubuntu, run:

```bash
sudo apt-get install tesseract-ocr
```

## Usage

### Step 1: Prepare Your Images
1. Take the images of your pokemon, I recommend you use the built-in Snipping Tool in Windows.
   - Make sure the images are clear and focused on the stats screen of each Pokémon. Try to make the screenshot as similar as possible from the example above.
   - If you are using a custom theme, revert to default theme for PokeMMO when taking the screenshots, as the tool has only been tested with the default theme and it's likely that custom themes will break it.
3. Place your Pokémon images in the `Pokemon` folder inside the project directory.


### Step 2: Run the script
1. Open a terminal or command prompt and navigate to the project directory.
2. Run the following command:

```bash
python script.py
```

### Step 3: Review the result
1. The script will process all images in the `Pokemon` folder and generate a `pokemon_data.csv` file in the project directory.
2. Open the `pokemon_data.csv` file to review the extracted Pokémon data.


### Notes and Known Issues

1. The tool is not 100% accurate in obtaining good results, during my tests I used around 100 screenshots and the results showed that around 6-7 Pokemon had issues
2. For some reason the computer seems to be hilariously bad at reading the word "IVs", it is likely that the tool will fail at recognizing the IV of some Pokemon, and 
3. Because of the sprite animations the Pokemon have depending on their type, sometimes it causes the tool to fail at scanning the Pokemon name, or it triggers the detection for Alpha or Shiny status.
4. Don't worry about the tool not producing 100% accurate results, once the data is inputted into the Spreadsheet any issues will be highlighted and can be manually fixed
