from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch, mm

def generate_pdf(front_image_files, back_image_file, output_pdf):
    """
    Generates a PDF with perfect front-to-back alignment and identical margins.
    """
    c = canvas.Canvas(output_pdf, pagesize=A4)
    page_width, page_height = A4  # 595.44 x 841.68 points

    # MTG card dimensions (63x88mm)
    card_width = 2.5 * 72    # 180 points
    card_height = 3.5 * 72   # 252 points

    # Fixed 3x3 grid
    cols = rows = 3
    cards_per_page = cols * rows

    # Calculate margins and gaps
    total_cards_width = card_width * cols
    total_cards_height = card_height * rows
    
    # Fixed margin for all sides (use left/right margin for top/bottom too)
    margin = (page_width - total_cards_width) / 2
    
    # Recalculate vertical centering with the same margin
    vertical_space = page_height - (2 * margin) - total_cards_height
    gap = vertical_space / (rows - 1)  # Distribute remaining space between cards

    def draw_page(image_list, is_back=False):
        for index, img_file in enumerate(image_list):
            if index >= cards_per_page:
                break

            row = index // cols
            col = index % cols

            # Calculate position (identical margins on all sides)
            x = margin + col * card_width
            y = margin + (rows - 1 - row) * (card_height + gap)

            if is_back:
                # For backs: rotate 180° around the card's center point
                c.saveState()
                c.translate(x + card_width/2, y + card_height/2)
                c.rotate(180)
                c.drawImage(img_file, -card_width/2, -card_height/2, 
                          width=card_width, height=card_height, 
                          preserveAspectRatio=True)
                c.restoreState()
            else:
                c.drawImage(img_file, x, y, width=card_width, height=card_height,
                          preserveAspectRatio=True)

        # Draw crop marks with identical margins
        c.setLineWidth(0.5)
        c.setStrokeColorRGB(0.8, 0.8, 0.8)
        
        # Vertical marks at fixed margin positions
        for col in range(cols + 1):
            x = margin + col * card_width
            c.line(x - 5, margin - 10, x + 5, margin - 10)  # Bottom
            c.line(x - 5, page_height - margin + 10, 
                  x + 5, page_height - margin + 10)  # Top

        # Horizontal marks
        for row in range(rows + 1):
            y = margin + row * (card_height + gap)
            c.line(margin - 10, y - 5, margin - 10, y + 5)  # Left
            c.line(page_width - margin + 10, y - 5,
                  page_width - margin + 10, y + 5)  # Right

        c.showPage()

    # Generate pages
    total_cards = len(front_image_files)
    for i in range(0, total_cards, cards_per_page):
        group = front_image_files[i:i+cards_per_page]
        # Draw front page
        draw_page(group, is_back=False)
        # Draw back page
        draw_page([back_image_file] * len(group), is_back=True)

    c.save()

if __name__ == "__main__":
    # Test PDF generation
    fronts = ["test_front.jpg"] * 9  # Test with 9 cards
    back = "assets/card_back.jpg"
    generate_pdf(fronts, back, "test_output.pdf")
