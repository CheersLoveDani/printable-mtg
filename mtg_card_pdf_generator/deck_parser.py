def parse_decklist(file_path):
    """
    Parse a decklist file where each line is formatted like:
        4 Lightning Bolt
    Returns a list of card names (repeating a card name according to its quantity).
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
            card_name = parts[1].strip()
            deck.extend([card_name] * count)
    return deck

if __name__ == "__main__":
    # Test deck parsing (optional)
    deck = parse_decklist("decklist.txt")
    for card in deck:
        print(card)
