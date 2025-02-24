import re

def parse_decklist(file_path):
    """Parse decklist, preserving variant information."""
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
            # Extract base name and variant info
            base_name = clean_card_name(raw_name)
            variant_info = extract_variant_info(raw_name)
            
            deck.extend([(base_name, variant_info)] * count)
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

def extract_variant_info(card_name):
    """Extract variant information from card name."""
    variant = ""
    # Match (set) and/or collector number
    set_match = re.search(r'\((.*?)\)', card_name)
    if set_match:
        variant = set_match.group(0)
    # Add collector number if present
    num_match = re.search(r'\s+\d+$', card_name)
    if num_match:
        variant += num_match.group(0)
    return variant.strip() if variant else None

if __name__ == "__main__":
    # Test the clean function:
    test_line = "Rapid Hybridization (sld) 1126 [Instant]"
    print(clean_card_name(test_line))  # Expected output: "Rapid Hybridization"
    # Test deck parsing (optional)
    deck = parse_decklist("decklist.txt")
    for card in deck:
        print(card)
