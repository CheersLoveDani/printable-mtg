import re

def parse_decklist(file_path):
    """
    Parse a decklist file where each line is formatted like:
      4 Lightning Bolt
    Returns a list of cleaned card names (with extraneous info removed).
    """
    deck = []
    with open(file_path, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split(maxsplit=1)
            if len(parts) < 2:
                continue
            try:
                count = int(parts[0])
            except ValueError:
                count = 1
            raw_name = parts[1].strip()
            # Clean the card name to remove extra annotations.
            cleaned_name = clean_card_name(raw_name)
            deck.extend([cleaned_name] * count)
    return deck

def clean_card_name(card_name):
    """
    Remove extraneous annotations from the card name.
    For example, "Rapid Hybridization (sld) 1126 [Instant]" becomes "Rapid Hybridization".
    """
    # Remove parenthesized text.
    cleaned = re.sub(r'\s*\(.*?\)', '', card_name)
    # Remove square-bracketed text.
    cleaned = re.sub(r'\s*\[.*?\]', '', cleaned)
    # Remove trailing numbers.
    cleaned = re.sub(r'\s*\d+$', '', cleaned)
    return cleaned.strip()

if __name__ == "__main__":
    # Test the clean function:
    test_line = "Rapid Hybridization (sld) 1126 [Instant]"
    print(clean_card_name(test_line))  # Expected output: "Rapid Hybridization"
    # Test deck parsing (optional)
    deck = parse_decklist("decklist.txt")
    for card in deck:
        print(card)
