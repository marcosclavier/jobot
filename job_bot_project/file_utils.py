import json
import os
import logging

def load_json_file(file_path):
    """
    Loads data from a JSON file.

    Args:
        file_path (str): The absolute path to the JSON file.

    Inputs:
        - file_path (str): Path to the JSON file.

    Returns:
        list or dict: The data loaded from the JSON file, typically a list or dictionary.
                      Returns an empty list if the file does not exist or is empty/malformed.
    """
    if not os.path.exists(file_path):
        logging.info(f"File not found at {file_path}. Returning empty list.")
        return []
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logging.error(f"Error loading JSON from {file_path}: {e}", exc_info=True)
        return []

def save_json_file(data, file_path):
    """
    Saves data to a JSON file.

    Args:
        data (list or dict): The data (list or dictionary) to be saved to the JSON file.
        file_path (str): The absolute path to the JSON file where data will be saved.

    Inputs:
        - data (list or dict): Data to be saved.
        - file_path (str): Path to the output JSON file.

    Outputs:
        - Writes the provided data to the specified JSON file.

    Returns:
        None
    """
    try:
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=4)
        logging.info(f"Data successfully saved to {file_path}.")
    except IOError as e:
        logging.error(f"Error writing to {file_path}: {e}", exc_info=True)