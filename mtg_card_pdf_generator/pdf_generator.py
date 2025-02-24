from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch, mm

def generate_pdf(front_image_files, back_image_files, output_pdf):
    """
    Generates a PDF with perfect front-to-back alignment.
    Back sides are in reversed order per row for proper double-sided printing.
    """
    c = canvas.Canvas(output_pdf, pagesize=A4)
    page_width, page_height = A4  # 595.44 x 841.68 points

    # MTG card dimensions (63x88mm) + 2%
    scale_factor = 1.02  # 2% larger
    card_width = 2.5 * 72 * scale_factor    # 183.6 points
    card_height = 3.5 * 72 * scale_factor   # 257.04 points

    # Fixed 3x3 grid
    cols = rows = 3
    cards_per_page = cols * rows

    # Calculate margins and gaps
    total_cards_width = card_width * cols
    total_cards_height = card_height * rows
    
    # Fixed margin for all sides (use left/right margin for top/bottom too)
    margin = (page_width - total_cards_width) / 2
    
    # Adjust vertical spacing with scaled cards
    vertical_space = page_height - (2 * margin) - total_cards_height
    gap = max(1, vertical_space / (rows - 1))  # Ensure at least 1 point gap

    def draw_page(front_images, back_images, is_back=False):
        images = back_images if is_back else front_images
        for row in range(rows):
            row_start = row * cols
            row_end = min(row_start + cols, len(images))
            row_images = images[row_start:row_end]
            
            if is_back:
                # Reverse the order of images in each row for back side
                row_images = row_images[::-1]

            for col, img_file in enumerate(row_images):
                # Calculate position (identical margins on all sides)
                x = margin + col * card_width
                y = margin + (rows - 1 - row) * (card_height + gap)

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

    # Generate pages with corresponding backs
    total_cards = len(front_image_files)
    for i in range(0, total_cards, cards_per_page):
        group_fronts = front_image_files[i:i+cards_per_page]
        group_backs = back_image_files[i:i+cards_per_page]
        draw_page(group_fronts, group_backs, is_back=False)
        draw_page(group_fronts, group_backs, is_back=True)

    c.save()

if __name__ == "__main__":
    # Test PDF generation
    fronts = ["test_front.jpg"] * 9  # Test with 9 cards
    backs = ["test_back.jpg"] * 9  # Test with 9 backs
    generate_pdf(fronts, backs, "test_output.pdf")
