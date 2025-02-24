import os
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk  # <--- Install Pillow for image display

from deck_parser import parse_decklist
from scryfall import get_card_image_url, download_image
from pdf_generator import generate_pdf

class MTGPDFGeneratorGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("MTG Card PDF Generator")
        # Remove or replace any fixed geometry
        # self.geometry("600x450")

        # Make window resizable
        self.resizable(True, True)

        # Variables for file paths and status
        self.decklist_file = tk.StringVar()
        self.output_pdf = tk.StringVar(value="mtg_cards_print.pdf")
        self.card_back_file = tk.StringVar(value="assets/card_back.jpg")
        self.status_text = tk.StringVar(value="Idle")
        self.error_log = []
        self.save_button = None

        self.create_widgets()

    def create_widgets(self):
        # Create a "main_frame" that expands and centers
        main_frame = tk.Frame(self)
        main_frame.pack(expand=True, fill="both")

        # Decklist file selection
        tk.Label(main_frame, text="Decklist File:").pack(pady=10)
        frame = tk.Frame(main_frame)
        frame.pack(pady=5)
        tk.Entry(frame, textvariable=self.decklist_file, width=50).pack(side=tk.LEFT, padx=5)
        tk.Button(frame, text="Browse", command=self.browse_file).pack(side=tk.LEFT)

        # Output PDF file selection
        tk.Label(main_frame, text="Output PDF File:").pack(pady=10)
        frame2 = tk.Frame(main_frame)
        frame2.pack(pady=5)
        tk.Entry(frame2, textvariable=self.output_pdf, width=50).pack(side=tk.LEFT, padx=5)
        tk.Button(frame2, text="Browse", command=self.browse_output).pack(side=tk.LEFT)

        # Custom card back file selection
        tk.Label(main_frame, text="Custom Card Back:").pack(pady=10)
        frame_back = tk.Frame(main_frame)
        frame_back.pack(pady=5)
        tk.Entry(frame_back, textvariable=self.card_back_file, width=50).pack(side=tk.LEFT, padx=5)
        tk.Button(frame_back, text="Browse", command=self.browse_back).pack(side=tk.LEFT)

        # Status and progress bar
        tk.Label(main_frame, textvariable=self.status_text).pack(pady=10)
        self.progress_bar = ttk.Progressbar(main_frame, orient="horizontal", length=400, mode="determinate")
        self.progress_bar.pack(pady=10)

        # Error log text area
        tk.Label(main_frame, text="Error Log:").pack(pady=(10, 0))
        self.error_text = tk.Text(main_frame, height=6, width=70, state="disabled")
        self.error_text.pack(pady=(0,10))

        # Generate PDF button
        tk.Button(main_frame, text="Generate PDF", command=self.start_generation, width=20).pack(pady=10)
        # Add a separate "Save PDF" button (initially disabled)
        self.save_button = tk.Button(main_frame, text="Save PDF", command=self.save_pdf, state="disabled", width=20)
        self.save_button.pack(pady=5)

        # Add a new button for previewing card images
        tk.Button(main_frame, text="Preview Images", command=self.preview_deck_images, width=20).pack(pady=5)

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

    def browse_back(self):
        filename = filedialog.askopenfilename(title="Select Card Back Image",
                                              filetypes=[("Image files", "*.jpg *.png"), ("All files", "*.*")])
        if filename:
            self.card_back_file.set(filename)

    def start_generation(self):
        if not self.decklist_file.get():
            messagebox.showerror("Error", "Please select a decklist file.")
            return

        self.status_text.set("Processing decklist...")
        self.progress_bar["value"] = 0
        self.error_log = []
        self.clear_error_text()

        # Call workflow directly (blocking) instead of using a thread
        self.generate_pdf_workflow()

    def log_error(self, message):
        self.error_log.append(message)
        self.error_text.config(state="normal")
        self.error_text.insert(tk.END, message + "\n")
        self.error_text.config(state="disabled")

    def clear_error_text(self):
        self.error_text.config(state="normal")
        self.error_text.delete("1.0", tk.END)
        self.error_text.config(state="disabled")

    def save_pdf(self):
        """Copy the generated PDF to a new location."""
        filename = filedialog.asksaveasfilename(title="Save PDF As",
                                                defaultextension=".pdf",
                                                filetypes=[("PDF Files", "*.pdf")])
        if filename:
            try:
                shutil.copy(self.output_pdf.get(), filename)
                messagebox.showinfo("Saved", f"PDF saved as {filename}")
            except Exception as e:
                messagebox.showerror("Error", f"Could not save PDF: {e}")

    def preview_deck_images(self):
        """Open a new window that shows each card's front and back in a grid."""
        if not self.decklist_file.get():
            messagebox.showerror("Error", "No decklist file selected.")
            return

        deck = parse_decklist(self.decklist_file.get())
        if not deck:
            messagebox.showerror("Error", "Deck is empty or invalid.")
            return

        preview_window = tk.Toplevel(self)
        preview_window.title("Deck Image Preview")

        # Make it scrollable
        canvas = tk.Canvas(preview_window)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar = ttk.Scrollbar(preview_window, orient="vertical", command=canvas.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        scroll_frame = tk.Frame(canvas)
        canvas.create_window((0,0), window=scroll_frame, anchor="nw")
        scroll_frame.bind("<Configure>", lambda e: canvas.config(scrollregion=canvas.bbox("all")))
        canvas.config(yscrollcommand=scrollbar.set)

        # Create or reuse the card_images folder
        image_folder = "card_images"
        if not os.path.exists(image_folder):
            os.makedirs(image_folder)

        # We store references to PhotoImages to avoid garbage collection
        self._preview_images_cache = []

        for i, card_name in enumerate(deck):
            # Download front image if needed
            safe_name = card_name.replace(" ", "_")
            front_path = os.path.join(image_folder, f"{safe_name}.jpg")
            if not os.path.exists(front_path):
                try:
                    url = get_card_image_url(card_name, image_size="normal")
                    download_image(url, front_path)
                except Exception as e:
                    # If error, skip display
                    continue

            # Load front image
            try:
                img_front = Image.open(front_path).resize((100, 140), Image.ANTIALIAS)
                tk_front = ImageTk.PhotoImage(img_front)
            except:
                continue

            # Load/back image
            if not os.path.exists(self.card_back_file.get()):
                # If no back found, skip
                continue
            try:
                img_back = Image.open(self.card_back_file.get()).resize((100, 140), Image.ANTIALIAS)
                tk_back = ImageTk.PhotoImage(img_back)
            except:
                continue

            # Create row for each card: front label, then back label
            front_label = tk.Label(scroll_frame, image=tk_front)
            front_label.grid(row=i, column=0, padx=5, pady=5)
            card_label = tk.Label(scroll_frame, text=card_name, wraplength=120)
            card_label.grid(row=i, column=1, padx=5, pady=5)
            back_label = tk.Label(scroll_frame, image=tk_back)
            back_label.grid(row=i, column=2, padx=5, pady=5)

            self._preview_images_cache.extend([tk_front, tk_back])

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
                        error_msg = f"Error downloading image for {card}: {e}"
                        print(error_msg)
                        self.log_error(error_msg)
                        continue
                front_image_files.append(file_path)

            if not front_image_files:
                self.status_text.set("No images downloaded.")
                messagebox.showerror("Error", "No images were successfully downloaded. Check the error log.")
                return

            # Check for card back image
            if not os.path.exists(self.card_back_file.get()):
                self.status_text.set("Error: Missing card back image.")
                messagebox.showerror("Error", f"Card back image not found at {self.card_back_file.get()}")
                return

            self.status_text.set("Generating PDF...")
            self.progress_bar["value"] = 75
            self.update_idletasks()

            output_pdf_file = self.output_pdf.get()
            generate_pdf(front_image_files, self.card_back_file.get(), output_pdf_file)

            self.status_text.set("PDF generation complete!")
            self.progress_bar["value"] = 100
            self.save_button.config(state="normal")  # Enable saving
            msg = f"PDF generated: {output_pdf_file}"
            if self.error_log:
                msg += "\nSome cards failed to download:\n" + "\n".join(self.error_log)
            messagebox.showinfo("Success", msg)
        except Exception as e:
            self.status_text.set("An error occurred.")
            messagebox.showerror("Error", str(e))

if __name__ == "__main__":
    app = MTGPDFGeneratorGUI()
    app.mainloop()
