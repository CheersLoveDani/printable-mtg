import requests
from requests.exceptions import Timeout, RequestException
from mtgjson_helper import MTGJSONDatabase

class CardNotFoundError(Exception):
    pass

# Add timeout constants
CONNECT_TIMEOUT = 5  # seconds
READ_TIMEOUT = 10    # seconds

class CardSides:
    def __init__(self, front_url, back_url=None):
        self.front_url = front_url
        self.back_url = back_url

def get_card_image_url(card_name, variant_info=None, image_size="normal"):
    """Get card image URLs, trying variant first then falling back to base version."""
    try:
        # Initialize MTGJSON database for variant lookups
        mtgjson = MTGJSONDatabase()
        
        if variant_info:
            # Try to find specific variant first
            variant_data = mtgjson.find_variant(card_name, variant_info)
            if variant_data and variant_data['id']:
                try:
                    return get_specific_printing_image(variant_data['id'], image_size)
                except (CardNotFoundError, Timeout, RequestException) as e:
                    print(f"Variant lookup failed: {e}, falling back to base version")
                    pass

        # Fall back to base version
        return get_base_version_image(card_name, image_size)
    except Exception as e:
        print(f"Error getting image URL for {card_name}: {e}")
        raise

def get_specific_printing_image(scryfall_id, image_size="normal"):
    """Get image URLs for specific printing, including back face if available."""
    url = f"https://api.scryfall.com/cards/{scryfall_id}"
    try:
        response = requests.get(
            url, 
            headers={"User-Agent": "MTGCardPDFGenerator/1.0"},
            timeout=(CONNECT_TIMEOUT, READ_TIMEOUT)
        )
        response.raise_for_status()
        data = response.json()
        
        # Handle double-faced cards
        if "card_faces" in data and len(data["card_faces"]) > 1:
            front_url = data["card_faces"][0]["image_uris"][image_size]
            back_url = data["card_faces"][1]["image_uris"][image_size]
            return CardSides(front_url, back_url)
        elif "image_uris" in data:
            return CardSides(data["image_uris"][image_size])
        raise CardNotFoundError("No image found")
    except Timeout:
        print(f"Timeout accessing Scryfall API for ID: {scryfall_id}")
        raise
    except Exception as e:
        print(f"Error accessing Scryfall API for ID {scryfall_id}: {e}")
        raise

def progressively_search_card(card_name, image_size="normal"):
    """
    Progressively search for a card by shortening the name until a match is found.
    Example: "Jace, the Mind Sculptor (WWK)" -> "Jace, the Mind Sculptor" -> "Jace"
    """
    original_name = card_name
    variants = []
    
    # First try: full name
    variants.append(card_name)
    
    # Second try: remove everything in parentheses and after
    base_name = card_name.split('(')[0].strip()
    if base_name != card_name:
        variants.append(base_name)
    
    # Third try: split on commas and take first part
    if ',' in base_name:
        variants.append(base_name.split(',')[0].strip())
    
    # Fourth try: split on spaces and try progressively shorter versions
    words = base_name.split()
    if len(words) > 1:
        for i in range(len(words) - 1, 0, -1):
            variants.append(' '.join(words[:i]))

    # Try each variant
    last_error = None
    for variant in variants:
        try:
            print(f"Trying search with: {variant}")
            url = f"https://api.scryfall.com/cards/named?fuzzy={variant}"
            response = requests.get(
                url,
                headers={"User-Agent": "MTGCardPDFGenerator/1.0"},
                timeout=(CONNECT_TIMEOUT, READ_TIMEOUT)
            )
            response.raise_for_status()
            data = response.json()
            
            # If we found a match, return it
            if "card_faces" in data and len(data["card_faces"]) > 1:
                return CardSides(
                    data["card_faces"][0]["image_uris"][image_size],
                    data["card_faces"][1]["image_uris"][image_size]
                )
            elif "image_uris" in data:
                return CardSides(data["image_uris"][image_size])
            
        except Exception as e:
            last_error = e
            continue

    # If we get here, no variant worked
    raise CardNotFoundError(f"Could not find card: {original_name} (tried variants: {', '.join(variants)}). Last error: {last_error}")

def get_base_version_image(card_name, image_size="normal"):
    """Get image URLs for base version, including back face if available."""
    try:
        # First try exact match
        url = f"https://api.scryfall.com/cards/named?exact={card_name}"
        response = requests.get(
            url, 
            headers={"User-Agent": "MTGCardPDFGenerator/1.0"},
            timeout=(CONNECT_TIMEOUT, READ_TIMEOUT)
        )
        
        # If exact match fails, try progressive fallback
        if response.status_code == 404:
            return progressively_search_card(card_name, image_size)
            
        response.raise_for_status()
        data = response.json()
        
        # Handle double-faced cards
        if "card_faces" in data and len(data["card_faces"]) > 1:
            return CardSides(
                data["card_faces"][0]["image_uris"][image_size],
                data["card_faces"][1]["image_uris"][image_size]
            )
        elif "image_uris" in data and image_size in data["image_uris"]:
            return CardSides(data["image_uris"][image_size])
        
        # If we get here with no images, try progressive fallback
        return progressively_search_card(card_name, image_size)
            
    except requests.exceptions.RequestException as e:
        # For any request error, try progressive fallback
        return progressively_search_card(card_name, image_size)
    except Exception as e:
        print(f"Error accessing Scryfall API for card {card_name}: {e}")
        raise

def download_image(url, file_path):
    """Downloads an image from the provided URL and saves it to file_path."""
    try:
        response = requests.get(
            url, 
            headers={"User-Agent": "MTGCardPDFGenerator/1.0"},
            timeout=(CONNECT_TIMEOUT, READ_TIMEOUT)
        )
        response.raise_for_status()
        with open(file_path, "wb") as f:
            f.write(response.content)
    except Exception as e:
        print(f"Error downloading image from {url}: {e}")
        raise

if __name__ == "__main__":
    # Example test: Download image for "Lightning Bolt"
    card = "Lightning Bolt"
    img_url = get_card_image_url(card)
    print(f"Image URL for {card}: {img_url.front_url}")
    download_image(img_url.front_url, f"{card.replace(' ', '_')}.jpg")
