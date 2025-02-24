import os
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from deck_parser import parse_decklist
from scryfall import get_card_image_url, download_image
from pdf_generator import generate_pdf

class MTGPDFGeneratorGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("MTG Card PDF Generator")
        self.geometry("600x400")
        self.resizable(False, False)

        # Variables for file paths and status
        self.decklist_file = tk.StringVar()
        self.output_pdf = tk.StringVar(value="mtg_cards_print.pdf")
        self.status_text = tk.StringVar(value="Idle")

        self.create_widgets()

    def create_widgets(self):
        # Decklist file selection
        tk.Label(self, text="Decklist File:").pack(pady=10)
        frame = tk.Frame(self)
        frame.pack(pady=5)
        tk.Entry(frame, textvariable=self.decklist_file, width=50).pack(side=tk.LEFT, padx=5)
        tk.Button(frame, text="Browse", command=self.browse_file).pack(side=tk.LEFT)

        # Output PDF file selection
        tk.Label(self, text="Output PDF File:").pack(pady=10)
        frame2 = tk.Frame(self)
        frame2.pack(pady=5)
        tk.Entry(frame2, textvariable=self.output_pdf, width=50).pack(side=tk.LEFT, padx=5)
        tk.Button(frame2, text="Browse", command=self.browse_output).pack(side=tk.LEFT)

        # Status and progress bar
        tk.Label(self, textvariable=self.status_text).pack(pady=10)
        self.progress_bar = ttk.Progressbar(self, orient="horizontal", length=400, mode="determinate")
        self.progress_bar.pack(pady=10)

        # Generate PDF button
        tk.Button(self, text="Generate PDF", command=self.start_generation, width=20).pack(pady=10)

    def browse_file(self):
        filename = filedialog.askopenfilename(title="Select Decklist File",
                                              filetypes=[("Text files", "*.txt"), ("All files", "*.*")])
        if filename:
            self.decklist_file.set(filename)

    def browse_output(self):
        filename = filedialog.asksaveasfilename(title="Save PDF As",
                                                defaultextension=".pdf",
                                                filetypes=[("PDF files", "*.pdf")])
        if filename:
            self.output_pdf.set(filename)

    def start_generation(self):
        if not self.decklist_file.get():
            messagebox.showerror("Error", "Please select a decklist file.")
            return

        # Disable the Generate button during processing (optional)
        self.status_text.set("Processing decklist...")
        self.progress_bar["value"] = 0

        thread = threading.Thread(target=self.generate_pdf_workflow)
        thread.start()

    def generate_pdf_workflow(self):
        try:
            deck = parse_decklist(self.decklist_file.get())
            if not deck:
                self.status_text.set("Decklist is empty.")
                return

            # Create folder for downloaded card images
            image_folder = "card_images"
            if not os.path.exists(image_folder):
                os.makedirs(image_folder)

            front_image_files = []
            total_cards = len(deck)
            for index, card in enumerate(deck):
                self.status_text.set(f"Downloading image for '{card}' ({index+1}/{total_cards})...")
                self.progress_bar["value"] = (index / total_cards) * 50
                self.update_idletasks()

                safe_name = card.replace(" ", "_")
                file_path = os.path.join(image_folder, f"{safe_name}.jpg")
                if not os.path.exists(file_path):
                    try:
                        url = get_card_image_url(card, image_size="normal")
                        download_image(url, file_path)
                    except Exception as e:
                        print(f"Error downloading image for {card}: {e}")
                        continue
                front_image_files.append(file_path)

            if not front_image_files:
                self.status_text.set("No images downloaded.")
                return

            # Check for card back image
            card_back_file = os.path.join("assets", "card_back.jpg")
            if not os.path.exists(card_back_file):
                messagebox.showerror("Error", f"Card back image not found at {card_back_file}")
                self.status_text.set("Error: Missing card back image.")
                return

            self.status_text.set("Generating PDF...")
            self.progress_bar["value"] = 75
            self.update_idletasks()

            output_pdf_file = self.output_pdf.get()
            generate_pdf(front_image_files, card_back_file, output_pdf_file)

            self.status_text.set("PDF generation complete!")
            self.progress_bar["value"] = 100
            messagebox.showinfo("Success", f"PDF generated: {output_pdf_file}")
        except Exception as e:
            self.status_text.set("An error occurred.")
            messagebox.showerror("Error", str(e))

if __name__ == "__main__":
    app = MTGPDFGeneratorGUI()
    app.mainloop()
