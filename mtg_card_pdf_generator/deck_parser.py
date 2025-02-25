import re

def parse_decklist(file_path):
    """Parse decklist, preserving variant information and handling multipliers."""
    deck = []
    with open(file_path, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
                
            # Match different quantity formats: "4 Card", "4x Card", "4X Card"
            quantity_match = re.match(r'^(\d+)\s*x?\s+(.+)$', line, re.IGNORECASE)
            if not quantity_match:
                continue
                
            count = int(quantity_match.group(1))
            raw_name = quantity_match.group(2).strip()
            
            # Extract base name and variant info
            base_name = clean_card_name(raw_name)
            variant_info = extract_variant_info(raw_name)
            
            # Add the specified number of copies
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
