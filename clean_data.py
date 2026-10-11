import json
import csv
import re

ICON_KEYWORDS = {
    "drag_indicator", "more_vert", "check_box_outline_blank", 
    "person", "star_border", "star", "expand_more", "expand_less", 
    "edit", "delete", "checkbox", "unknown"
}

def clean_name(name, email):
    if not name or name.lower().strip() in ICON_KEYWORDS:
        # Infer clean name from email prefix
        prefix = email.split("@")[0]
        # remove numbers
        clean_prefix = re.sub(r'\d+', '', prefix).strip("._- ")
        parts = [p.capitalize() for p in re.split(r'[._-]', clean_prefix) if p]
        if parts:
            return " ".join(parts)
        return "Unknown"
    
    # Remove leading icons if concatenated
    for icon in ICON_KEYWORDS:
        if name.lower().startswith(icon):
            name = name[len(icon):].strip()
            
    # Clean leading/trailing non-alpha except dots
    name = re.sub(r'^[^a-zA-Z]+', '', name).strip()
    return name or "Unknown"

def clean_files():
    json_path = "nsu_directory_contacts.json"
    csv_path = "nsu_directory_contacts.csv"
    
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        cleaned_records = []
        for item in data:
            email = item.get("email", "").lower().strip()
            raw_name = item.get("name", "").strip()
            name = clean_name(raw_name, email)
            cleaned_records.append({"name": name, "email": email})
            
        # Save JSON
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(cleaned_records, f, indent=2, ensure_ascii=False)
            
        # Save CSV
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["name", "email"])
            writer.writeheader()
            writer.writerows(cleaned_records)
            
        print(f"Successfully cleaned {len(cleaned_records)} records in '{json_path}' and '{csv_path}'.")
    except Exception as e:
        print(f"Error during cleanup: {e}")

if __name__ == "__main__":
    clean_files()
