import cv2
import numpy as np
from PIL import Image, ImageEnhance
import pytesseract
import unidecode
import re
import csv
import os
import glob
import difflib  # Import difflib for finding closest matches

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
    replacements = {
        "IIVs:2": "IVs:", "IVs: 2": "IVs:", "IVs:r": "IVs:", "IVrs": "IVs:", "IV:": "IVs:",
        "Ws:": "IVs:", "Vs:": "IVs:", "Ws": "IVs:", "Wsr": "IVs:", "Wee": "IVs:", "Wer": "IVs:", "WES": "IVs:",
        "EIVs:": "EVs:", "IVs:2": "IVs:"
    }

    # Replace specific common misreads
    for old, new in replacements.items():
        ocr_text = ocr_text.replace(old, new)

    # clean up remaining unwanted characters near "IVs:"
    ocr_text = re.sub(r'IVs?:?\s*[^\d\s/]', 'IVs: ', ocr_text)

    # Replace accented characters using unidecode
    ocr_text = unidecode.unidecode(ocr_text)

    # Remove everything before "Lv" to clean up noise
    lv_index = ocr_text.find("Lv")
    if lv_index != -1:
        ocr_text = ocr_text[lv_index:]

    # replace any remaining special characters and clean up spacing
    ocr_text = re.sub(r'[^\w\s/:]', '', ocr_text)
    ocr_text = re.sub(r'\s+', ' ', ocr_text)

    return ocr_text

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

    # IV extraction
    ivs_match = re.search(r'IVs?:?\s*(\d{1,2}/\d{1,2}/\d{1,2}/\d{1,2}/\d{1,2}/\d{1,2})', cleaned_text)
    ivs = ivs_match.group(1) if ivs_match else "Not Found"
    iv_values = ivs.split('/') if ivs != "Not Found" else ["Not Found"] * 6

    # EV extraction
    evs_pattern = r'EVs?:?\s*(\d{1,3}/\d{1,3}/\d{1,3}/\d{1,3}/\d{1,3}/\d{1,3})'
    evs_match = re.search(evs_pattern, cleaned_text)
    evs = evs_match.group(1) if evs_match else "Not Found"
    ev_values = evs.split('/') if evs != "Not Found" else ["Not Found"] * 6

    # Extract nature
    valid_natures = [
        "Adamant", "Brave", "Lonely", "Naughty", "Bold", "Relaxed", "Impish", "Lax", "Timid", 
        "Hasty", "Jolly", "Naive", "Modest", "Mild", "Quiet", "Rash", "Calm", "Gentle", "Sassy", 
        "Careful", "Quirky"
    ]
    nature_match = re.search(r'Nature:?\s*(' + '|'.join(valid_natures) + ')', cleaned_text, re.IGNORECASE)
    nature = nature_match.group(1) if nature_match else "Not Found"

    # Extract ability from the list
    ability_match = re.search(r'\b(?:{})\b'.format("|".join(possible_abilities)), cleaned_text, re.IGNORECASE)
    ability = ability_match.group(0).capitalize() if ability_match else "Not Found"

    # Extract moves
    moves = re.findall(r'\b(?:{})\b'.format("|".join(possible_moves)), cleaned_text, re.IGNORECASE)
    cleaned_moves = list(set([move.capitalize() for move in moves])) if moves else ["Not Found"]

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
        "nature": nature,
        "ability": ability, 
        "moves": cleaned_moves
    }

# save data to CSV
# Save data to CSV without headers and with blank ID field
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
    folder_path = 'Pokemon'  
    process_folder(folder_path)
