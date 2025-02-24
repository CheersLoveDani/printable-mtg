import requests
from requests.exceptions import Timeout, RequestException
import urllib.parse

CONNECT_TIMEOUT = 5  # seconds
READ_TIMEOUT = 10    # seconds

class MTGJSONDatabase:
    def find_variant(self, card_name, variant_info=None):
        """Find specific variant of a card using Scryfall API directly."""
        if not variant_info:
            return None

        try:
            # Clean up the variant info
            set_code = None
            if '(' in variant_info and ')' in variant_info:
                set_code = variant_info[variant_info.find('(')+1:variant_info.find(')')].lower()
                # Remove any special characters from set code
                set_code = ''.join(c for c in set_code if c.isalnum())

            if not set_code:
                return None

            # Clean the card name
            clean_name = card_name.split('(')[0].strip()  # Remove anything in parentheses
            clean_name = clean_name.split('*')[0].strip()  # Remove *F* or similar markers
            clean_name = clean_name.split('#')[0].strip()  # Remove collector numbers

            # Create the search query
            query = f'!"{clean_name}" set:{set_code}'
            url = "https://api.scryfall.com/cards/search"
            params = {
                'q': query,
                'unique': 'prints'
            }
            
            response = requests.get(
                url,
                params=params,
                headers={"User-Agent": "MTGCardPDFGenerator/1.0"},
                timeout=(CONNECT_TIMEOUT, READ_TIMEOUT)
            )
            response.raise_for_status()
            data = response.json()

            if data.get('data') and len(data['data']) > 0:
                card = data['data'][0]
                return {
                    'set': card['set'],
                    'collector_number': card.get('collector_number', ''),
                    'id': card.get('id')
                }

        except Exception as e:
            print(f"Error looking up variant for {card_name} ({variant_info}): {e}")
            return None

        return None
