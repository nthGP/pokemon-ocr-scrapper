import cv2
import numpy as np
from PIL import Image, ImageEnhance
import pytesseract
import unidecode
import re
import csv
import os
import glob
import difflib  

# preprocessing
def preprocess_image(image_path):
    image = Image.open(image_path)
    image = image.resize((int(image.width * 1.2), int(image.height * 1.2)))
    enhancer = ImageEnhance.Contrast(image)
    image = enhancer.enhance(1.5)
    image_cv = np.array(image)
    image_cv = cv2.cvtColor(image_cv, cv2.COLOR_RGB2BGR)  # Convert from RGB to BGR for OpenCV
    return image_cv

# crop top-left corner for icon detection
def crop_top_left_for_icons(image_cv, crop_ratio=0.12):
    height, width, _ = image_cv.shape
    cropped_image = image_cv[0:int(height * crop_ratio), 0:int(width * crop_ratio)]
    return cropped_image

# detect shiny, alpha, and hidden ability icons using color matching
def detect_icons(image_cv):
    # shiny and alpha detection
    icon_area = crop_top_left_for_icons(image_cv)
    hsv_icon_area = cv2.cvtColor(icon_area, cv2.COLOR_BGR2HSV)

    # Define color range for shiny icon
    lower_shiny = np.array([20, 100, 50])
    upper_shiny = np.array([50, 255, 255])

    # define color range for alpha icon 
    lower_alpha1 = np.array([0, 50, 50])
    upper_alpha1 = np.array([10, 255, 255])
    lower_alpha2 = np.array([170, 50, 50])
    upper_alpha2 = np.array([180, 255, 255])

    # create masks for shiny and alpha icons based on the color ranges
    shiny_mask = cv2.inRange(hsv_icon_area, lower_shiny, upper_shiny)
    alpha_mask1 = cv2.inRange(hsv_icon_area, lower_alpha1, upper_alpha1)
    alpha_mask2 = cv2.inRange(hsv_icon_area, lower_alpha2, upper_alpha2)
    alpha_mask = alpha_mask1 + alpha_mask2

    # Check if there are any white pixels in the mask (indicating a match)
    is_shiny = np.any(shiny_mask)
    is_alpha = np.any(alpha_mask)

    # hidden ability detection 
    height, width, _ = image_cv.shape
    x_start, y_start = int(width * 0.45), int(height * 0.65)
    x_end, y_end = int(width * 0.65), int(height * 0.73)
    hidden_ability_area = image_cv[y_start:y_end, x_start:x_end]
    hsv_hidden_ability_area = cv2.cvtColor(hidden_ability_area, cv2.COLOR_BGR2HSV)

    # HSV range for hidden ability
    lower_hidden_ability = np.array([90, 200, 200])
    upper_hidden_ability = np.array([100, 255, 255])

    hidden_ability_mask = cv2.inRange(hsv_hidden_ability_area, lower_hidden_ability, upper_hidden_ability)

    # check if hidden ability icon is present
    is_hidden_ability = np.any(hidden_ability_mask)

    return is_shiny, is_alpha, is_hidden_ability

# crop the image to exclude the top-right corner
def crop_image_excluding_top_right(image):
    width, height = image.size
    crop_box = (0, 0, int(width * 0.8), height)  # crop out 20% of the right side
    cropped_image = image.crop(crop_box)
    return cropped_image

# function to extract text from an image using OCR, excluding the top-right corner
def extract_text_from_image(image_path):
    image = Image.open(image_path)
    image = crop_image_excluding_top_right(image) # Crop the image to exclude the top-right corner
    image = image.convert('L') # Convert to grayscale
    extracted_text = pytesseract.image_to_string(image)
    return extracted_text

# function to load lists from files
def load_list_from_file(file_path):
    try:
        with open(file_path, 'r') as file:
            return [line.strip() for line in file.readlines()]
    except FileNotFoundError:
        print(f"File not found: {file_path}")
        return []

# Clean and standardize OCR output
def clean_ocr_output(ocr_text):
    # Fix common misreads and clean up text
    replacements = {
        "EIVs:": "EVs:", "Evs:": "EVs:", "Eve": "EVs:",
        "BV": "EVs:", "Evs": "EVs:", "EVs:r": "EVs:"
    }

    # Replace specific common misreads
    for old, new in replacements.items():
        ocr_text = ocr_text.replace(old, new)

    # clean up remaining unwanted characters between "IVs:" and the actual values
    ocr_text = re.sub(r'IVs?:?\s*[^\d\s/]', 'IVs: ', ocr_text)

    # Handle special cases where "IVs:" might be followed by incorrect characters
    ocr_text = re.sub(r'IVs: \d?\s*', 'IVs: ', ocr_text)

    # Replace accented characters using unidecode
    ocr_text = unidecode.unidecode(ocr_text)

    # Remove everything before "Lv" to clean up noise
    lv_index = ocr_text.find("Lv")
    if lv_index != -1:
        ocr_text = ocr_text[lv_index:]

    # replace any remaining special characters and clean up spacing
    ocr_text = re.sub(r'[^\w\s/:]', '', ocr_text)
    ocr_text = re.sub(r'\s+', ' ', ocr_text)

    print("Cleaned OCR Output:")
    print(ocr_text)
    return ocr_text

# Extract moves (duh)
def extract_moves(cleaned_text, possible_moves):
    # Ensure multi-word moves are prioritized
    sorted_moves = sorted(possible_moves, key=len, reverse=True)  # Sort longest first

    detected_moves = []
    words = cleaned_text.split()  # Split text into words

    for i in range(len(words)):
        # Check for multi-word moves first
        for move in sorted_moves:
            move_words = move.split()
            if words[i:i + len(move_words)] == move_words:
                detected_moves.append(move)
                break  # Stop checking once we find a valid move

    # Fuzzy matching for potential misreads
    cleaned_moves = []
    for move in detected_moves:
        closest_match = difflib.get_close_matches(move, possible_moves, n=1, cutoff=0.8)
        if closest_match:
            cleaned_moves.append(closest_match[0])

    return cleaned_moves if cleaned_moves else ["Not Found"]

import re
import difflib

# Extract ability (wow)
def extract_ability(cleaned_text, possible_abilities):
    # Sort abilities by length to prioritize multi-word abilities
    sorted_abilities = sorted(possible_abilities, key=len, reverse=True)

    # Clean up text: remove special characters, underscores, etc.
    cleaned_text = re.sub(r'[^a-zA-Z\s]', '', cleaned_text)  # Keep only letters & spaces

    detected_ability = "Not Found"

    # **Check for exact matches first**
    for ability in sorted_abilities:
        if ability.lower() in cleaned_text.lower():
            detected_ability = ability
            break

    # **Check for concatenated words (e.g., "SheerForce" → "Sheer Force")**
    if detected_ability == "Not Found":
        for ability in sorted_abilities:
            condensed_ability = ability.replace(" ", "").lower()
            if condensed_ability in cleaned_text.replace(" ", "").lower():
                detected_ability = ability
                break

    # **Fuzzy match to fix OCR misreads (e.g., "lron Barbs" → "Iron Barbs")**  **NOT WORKING VERY WELL**
    if detected_ability == "Not Found":
        closest_match = difflib.get_close_matches(cleaned_text, possible_abilities, n=1, cutoff=0.7)
        if closest_match:
            detected_ability = closest_match[0]

    return detected_ability

# Process the cleaned OCR text and extract relevant Pokémon information
def process_pokemon_data(ocr_text, moves_file='moves.txt', abilities_file='abilities.txt', pokemon_names_file='pokemon_names.txt'):
    cleaned_text = clean_ocr_output(ocr_text)  # Clean the OCR output

    # Load moves, abilities, and Pokémon names from files
    possible_moves = load_list_from_file(moves_file)
    possible_abilities = load_list_from_file(abilities_file)
    pokemon_names = load_list_from_file(pokemon_names_file)

    # Extract Level and Pokémon Name (correct OCR misreads by finding closest match)
    name_level_match = re.search(r'(?:Lv\.?\s*(\d+))\s+([A-Za-z]+)', cleaned_text)
    if name_level_match:
        level = name_level_match.group(1)
        ocr_pokemon_name = name_level_match.group(2)

        # Find closest Pokémon name using difflib
        closest_matches = difflib.get_close_matches(ocr_pokemon_name, pokemon_names, n=1, cutoff=0.7)
        pokemon_name = closest_matches[0] if closest_matches else "Unknown"
    else:
        level, pokemon_name = "Unknown", "Unknown"

    # Extract all six-number sequences in the OCR text
    six_value_matches = re.findall(r'(\d{1,3}/\d{1,3}/\d{1,3}/\d{1,3}/\d{1,3}/\d{1,3})', cleaned_text)

    ivs = "Not Found"
    evs = "Not Found"
    iv_values = ["Not Found"] * 6
    ev_values = ["Not Found"] * 6

    if six_value_matches:
        # Assume last six-number sequence is EVs (Stats -> IVs -> EVs order)
        for possible_values in reversed(six_value_matches):  # Iterate backwards
            values_list = list(map(int, possible_values.split('/')))
            values_sum = sum(values_list)

            if values_sum <= 510:  # Likely EVs (EVs cap at 510)
                evs = possible_values
                ev_values = values_list
                break  # Stop after finding EVs

        # Assume IVs are the second-last valid six-number sequence
        for possible_values in reversed(six_value_matches):
            values_list = list(map(int, possible_values.split('/')))
            
            if values_sum > 510:  # Stats are typically much higher than 510
                continue  # Skip stats
            
            if possible_values != evs:  # Ensure it's different from detected EVs
                ivs = possible_values
                iv_values = values_list
                break  # Stop after finding IVs

    # List of valid natures in English
    valid_natures_english = [
        "Adamant", "Brave", "Lonely", "Naughty", "Bold", "Relaxed", "Impish", "Lax", "Timid", 
        "Hasty", "Jolly", "Naive", "Modest", "Mild", "Quiet", "Rash", "Calm", "Gentle", "Sassy", 
        "Careful", "Quirky"
    ]

    # Extract Nature by looking directly for valid nature names in cleaned text
    def extract_valid_nature(text, valid_natures):
        for nature in valid_natures:
            # Match natures exactly, ignoring case and allowing for possible concatenation
            match = re.search(rf'\b({nature})(?=\b|[A-Z])', text, re.IGNORECASE)
            if match:
                return nature.capitalize()
        return "Not Found"

    # Extract nature
    found_nature = extract_valid_nature(cleaned_text, valid_natures_english)

    # This implementation for extracting nature causes a very specific bug, if a Pokemon has the Brave Bird move it will always display the nature as Brave

    # Extract ability
    ability = extract_ability(cleaned_text, possible_abilities)

    # Extract moves
    moves = extract_moves(cleaned_text, possible_moves)

    return {
        "pokemon_name": pokemon_name,
        "level": level,
        "ivs": ivs,
        "iv_hp": iv_values[0],
        "iv_atk": iv_values[1],
        "iv_def": iv_values[2],
        "iv_sp_atk": iv_values[3],
        "iv_sp_def": iv_values[4],
        "iv_spd": iv_values[5],
        "evs": evs,
        "ev_hp": ev_values[0],
        "ev_atk": ev_values[1],
        "ev_def": ev_values[2],
        "ev_sp_atk": ev_values[3],
        "ev_sp_def": ev_values[4],
        "ev_spd": ev_values[5],
        "nature": found_nature,
        "ability": ability, 
        "moves": moves
    }


# save data to CSV

def save_data_to_csv(data_list, output_csv='pokemon_data.csv'):
    with open(output_csv, mode='w', newline='') as file:
        writer = csv.writer(file)
        print(f"CSV is being saved to: {output_csv}")

        # Write the Pokémon data (without headers, but with a blank ID field)
        for data in data_list:
            # Ensure the moves list has exactly 4 entries, padding with empty strings if needed
            moves = data["moves"] + [""] * (4 - len(data["moves"]))

            # Write the row (with blank ID field and other values)
            writer.writerow([
                "",  # ID (left blank)
                data["pokemon_name"],  # Pokemon Name
                "",  # Type 1 (Not gathered by the script)
                "",  # Type 2 (Not gathered by the script)
                "",  # Tier (Not gathered by the script)
                "",  # Tags (Not gathered by the script)
                data["is_alpha"],  # Alpha
                data["is_shiny"],  # Shiny
                data["is_hidden_ability"],  # HA
                data["nature"],  # Nature
                data["level"],  # Level
                data["ivs"],  # IVs
                data["iv_hp"],  # IV HP
                data["iv_atk"],  # IV Atk
                data["iv_def"],  # IV Def
                data["iv_sp_atk"],  # IV Sp. Atk
                data["iv_sp_def"],  # IV Sp. Def
                data["iv_spd"],  # IV Spd
                data["evs"],  # EVs
                data["ev_hp"],  # EV HP
                data["ev_atk"],  # EV Atk
                data["ev_def"],  # EV Def
                data["ev_sp_atk"],  # EV Sp. Atk
                data["ev_sp_def"],  # EV Sp. Def
                data["ev_spd"],  # EV Spd
                data["ability"],  # Ability
                moves[0],  # Move1
                moves[1],  # Move2
                moves[2],  # Move3
                moves[3],  # Move4
                "",  # On team (Not gathered by the script)
                "",  # Owned by (Not gathered by the script)
                "",  # Held By (Not gathered by the script)
                "",  # Date Rented (Not gathered by the script)
                ""  # Queue (Not gathered by the script)
            ])

# process multiple images in a folder
def process_folder(folder_path, output_csv='pokemon_data.csv'):
    image_files = glob.glob(os.path.join(folder_path, '*.[pj][pn]*g')) 
    all_data = []

    for image_file in image_files:
        print(f"\nProcessing image: {image_file}")
        final_data = run_pokemon_analysis(image_file)
        all_data.append(final_data)

    save_data_to_csv(all_data, output_csv)
    print(f"\nAll data saved to {output_csv}")

# Combined function to run Pokémon analysis (shiny/alpha/HA detection + OCR processing + CSV export)
def run_pokemon_analysis(image_path):
    image_cv = preprocess_image(image_path)

    print("\n--- Detecting Alpha/Shiny/HA Status ---")
    is_shiny, is_alpha, is_hidden_ability = detect_icons(image_cv)
    print(f"Alpha Detected: {is_alpha}, Shiny Detected: {is_shiny}, Hidden Ability Detected: {is_hidden_ability}")

    ocr_output = extract_text_from_image(image_path)
    print("\n--- Extracting and Processing OCR Text ---")
    pokemon_data = process_pokemon_data(ocr_output)

    final_data = {
        **pokemon_data,
        "is_alpha": is_alpha,
        "is_shiny": is_shiny,
        "is_hidden_ability": is_hidden_ability
    }

    print("\n--- Final Pokémon Data ---")
    for key, value in final_data.items():
        print(f"{key}: {value}")

    return final_data

if __name__ == "__main__":
    folder_path = 'Pokemon/'  
    process_folder(folder_path)
