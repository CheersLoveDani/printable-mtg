import requests
from requests.exceptions import Timeout, RequestException

CONNECT_TIMEOUT = 5  # seconds
READ_TIMEOUT = 10    # seconds

class MTGJSONDatabase:
    def find_variant(self, card_name, variant_info=None):
        """Find specific variant of a card using Scryfall API directly."""
        if not variant_info:
            return None

        try:
            # Extract set code from variant info (e.g., "(sld)")
            set_code = None
            if '(' in variant_info and ')' in variant_info:
                set_code = variant_info[variant_info.find('(')+1:variant_info.find(')')].lower()

            if not set_code:
                return None

            # Query Scryfall for the specific printing
            url = f"https://api.scryfall.com/cards/search"
            params = {
                'q': f'!"{card_name}" set:{set_code}',
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
                card = data['data'][0]  # Get first matching print
                return {
                    'set': card['set'],
                    'collector_number': card['collector_number'],
                    'id': card['id']
                }

        except Exception as e:
            print(f"Error looking up variant for {card_name} ({variant_info}): {e}")
            return None

        return None
