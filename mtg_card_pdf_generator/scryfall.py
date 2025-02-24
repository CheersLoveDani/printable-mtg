import requests

def get_card_image_url(card_name, image_size="normal"):
    """
    Queries Scryfall API for a card by exact name and returns the image URL.
    """
    url = f"https://api.scryfall.com/cards/named?exact={card_name}"
    headers = {
        "User-Agent": "MTGCardPDFGenerator/1.0",
        "Accept": "application/json"
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    data = response.json()
    if "image_uris" in data and image_size in data["image_uris"]:
        return data["image_uris"][image_size]
    else:
        raise ValueError(f"No image found for card: {card_name}")

def download_image(url, file_path):
    """
    Downloads an image from the provided URL and saves it to file_path.
    """
    headers = {"User-Agent": "MTGCardPDFGenerator/1.0"}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    with open(file_path, "wb") as f:
        f.write(response.content)

if __name__ == "__main__":
    # Example test: Download image for "Lightning Bolt"
    card = "Lightning Bolt"
    img_url = get_card_image_url(card)
    print(f"Image URL for {card}: {img_url}")
    download_image(img_url, f"{card.replace(' ', '_')}.jpg")
