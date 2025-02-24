from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

def generate_pdf(front_image_files, back_image_file, output_pdf):
    """
    Generates a PDF with alternating pages:
      - Front pages: grid of card front images.
      - Back pages: grid of the card back image repeated for each card.
    
    Each pair of pages corresponds to a group of card images.
    """
    c = canvas.Canvas(output_pdf, pagesize=letter)
    page_width, page_height = letter

    # Standard card dimensions: 2.5" x 3.5" (in points)
    card_width = 2.5 * 72
    card_height = 3.5 * 72
    margin = 36  # 0.5 inch margin
    gap = 10     # gap between cards

    # Calculate grid (number of cards per row and column)
    cols = int((page_width - 2 * margin + gap) // (card_width + gap))
    rows = int((page_height - 2 * margin + gap) // (card_height + gap))
    cards_per_page = cols * rows

    def draw_page(image_list):
        for index, img_file in enumerate(image_list):
            pos = index % cards_per_page
            col = pos % cols
            row = pos // cols
            x = margin + col * (card_width + gap)
            # In ReportLab, (0,0) is at the bottom left.
            y = page_height - margin - (row + 1) * card_height - row * gap
            c.drawImage(img_file, x, y, width=card_width, height=card_height, preserveAspectRatio=True, anchor="c")
        c.showPage()

    total_cards = len(front_image_files)
    for i in range(0, total_cards, cards_per_page):
        group = front_image_files[i:i+cards_per_page]
        # Draw the front images page
        draw_page(group)
        # Draw the corresponding back images page (repeat the same back for each card)
        draw_page([back_image_file] * len(group))

    c.save()

if __name__ == "__main__":
    # Test PDF generation (requires test images)
    fronts = ["test_front.jpg"] * 10  # Replace with valid front image paths
    back = "assets/card_back.jpg"
    generate_pdf(fronts, back, "test_output.pdf")
