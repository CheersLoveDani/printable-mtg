import os
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk  # <--- Install Pillow for image display
import threading
import queue
from functools import partial
import re

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
        self.queue = queue.Queue()
        self.current_thread = None

        # Create card_images directory at startup
        self.image_folder = os.path.abspath("card_images")
        if not os.path.exists(self.image_folder):
            os.makedirs(self.image_folder)

        self.create_widgets()
        self._start_queue_checker()

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

    def _start_queue_checker(self):
        """Start checking for GUI updates from worker thread."""
        self.after(100, self._process_queue)

    def _process_queue(self):
        """Process any pending GUI updates from the queue."""
        try:
            while True:
                action, args = self.queue.get_nowait()
                if action == "status":
                    self.status_text.set(args)
                elif action == "progress":
                    self.progress_bar["value"] = args
                elif action == "error":
                    self.log_error(str(args))  # Convert args to string
                elif action == "complete":
                    self._handle_completion(*args)
                self.update_idletasks()
                self.queue.task_done()
        except queue.Empty:
            pass
        finally:
            # Check queue again after 100ms
            self.after(100, self._process_queue)

    def queue_action(self, action, *args):
        """Thread-safe way to queue GUI updates."""
        self.queue.put((action, args))

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

        # Disable buttons while processing
        self.save_button.config(state="disabled")
        for widget in self.winfo_children():
            if isinstance(widget, tk.Button):
                widget.config(state="disabled")

        self.status_text.set("Processing decklist...")
        self.progress_bar["value"] = 0
        self.error_log = []
        self.clear_error_text()

        # Start worker thread
        self.current_thread = threading.Thread(target=self.generate_pdf_workflow)
        self.current_thread.daemon = True
        self.current_thread.start()

    def _handle_completion(self, success, message):
        """Handle completion of the generation process."""
        # Re-enable buttons
        for widget in self.winfo_children():
            if isinstance(widget, tk.Button):
                widget.config(state="normal")
        
        if success:
            self.save_button.config(state="normal")
            messagebox.showinfo("Success", message)
        else:
            self.save_button.config(state="disabled")
            messagebox.showerror("Error", message)

    def log_error(self, message):
        """Log an error message to the error text widget."""
        message = str(message)  # Ensure message is a string
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

        # We store references to PhotoImages to avoid garbage collection
        self._preview_images_cache = []

        for i, card_tuple in enumerate(deck):
            card_name, variant_info = card_tuple
            safe_name = card_name.split(" // ")[0].replace(" ", "_").replace("/", "_").replace("\\", "_")
            front_path = os.path.join(self.image_folder, f"{safe_name}_front.jpg")

            if not os.path.exists(front_path):
                try:
                    sides = get_card_image_url(card_name, variant_info, image_size="normal")
                    download_image(sides.front_url, front_path)
                except Exception as e:
                    print(f"Error downloading {card_name}: {e}")
                    continue

            try:
                img_front = Image.open(front_path)
                img_front = img_front.resize((100, 140), Image.Resampling.LANCZOS)
                tk_front = ImageTk.PhotoImage(img_front)

                # Check for double-sided card
                back_path = os.path.join(self.image_folder, f"{safe_name}_back.jpg")
                if os.path.exists(back_path):
                    img_back = Image.open(back_path)
                elif os.path.exists(self.card_back_file.get()):
                    img_back = Image.open(self.card_back_file.get())
                else:
                    # Skip if no back image available
                    continue

                img_back = img_back.resize((100, 140), Image.Resampling.LANCZOS)
                tk_back = ImageTk.PhotoImage(img_back)

                # Create row for each card
                front_label = tk.Label(scroll_frame, image=tk_front)
                front_label.grid(row=i, column=0, padx=5, pady=5)
                card_label = tk.Label(scroll_frame, text=card_name, wraplength=120)
                card_label.grid(row=i, column=1, padx=5, pady=5)
                back_label = tk.Label(scroll_frame, image=tk_back)
                back_label.grid(row=i, column=2, padx=5, pady=5)

                self._preview_images_cache.extend([tk_front, tk_back])
            except Exception as e:
                print(f"Error loading images for {card_name}: {e}")
                continue

    def sanitize_filename(self, name):
        """Sanitize card name for file system use."""
        # Remove special characters and invalid filename chars
        name = name.split(" // ")[0]  # Take only the front card name
        # Remove any special characters and replace with underscore
        name = re.sub(r'[\\/*?:"<>|]', '', name)
        name = re.sub(r'[^a-zA-Z0-9\-_\s]', '', name)
        return name.replace(" ", "_").strip("_")

    def generate_pdf_workflow(self):
        """Worker thread for PDF generation."""
        try:
            deck = parse_decklist(self.decklist_file.get())
            if not deck:
                self.queue_action("status", "Decklist is empty.")
                self.queue_action("complete", False, "Decklist is empty.")
                return

            card_images = []  # List of (front_path, back_path) tuples
            total_cards = len(deck)

            for index, card_tuple in enumerate(deck):
                card_name, variant_info = card_tuple
                self.queue_action("status", f"Downloading image for '{card_name}' ({index+1}/{total_cards})...")
                self.queue_action("progress", (index / total_cards) * 50)

                safe_name = self.sanitize_filename(card_name)
                front_path = os.path.join(self.image_folder, f"{safe_name}_front.jpg")
                back_path = os.path.join(self.image_folder, f"{safe_name}_back.jpg")

                try:
                    if not os.path.exists(front_path):
                        sides = get_card_image_url(card_name, variant_info, image_size="normal")
                        download_image(sides.front_url, front_path)
                        if sides.back_url:  # If it's a double-sided card
                            download_image(sides.back_url, back_path)
                            default_back = back_path
                        else:
                            default_back = self.card_back_file.get()
                    else:
                        default_back = self.card_back_file.get()
                        if os.path.exists(back_path):  # Use existing back if available
                            default_back = back_path
                            
                    card_images.append((front_path, default_back))
                except Exception as e:
                    error_msg = f"Error downloading image for {card_name}: {e}"
                    print(error_msg)
                    self.queue_action("error", error_msg)
                    continue

            if not card_images:
                self.queue_action("status", "No images downloaded.")
                self.queue_action("complete", False, "No images were successfully downloaded. Check the error log.")
                return

            # Generate PDF with card-specific backs
            self.queue_action("status", "Generating PDF...")
            self.queue_action("progress", 75)

            output_pdf_file = self.output_pdf.get()
            fronts = [front for front, _ in card_images]
            backs = [back for _, back in card_images]
            generate_pdf(fronts, backs, output_pdf_file)

            self.queue_action("status", "PDF generation complete!")
            self.queue_action("progress", 100)

            msg = f"PDF generated: {output_pdf_file}"
            if self.error_log:
                msg += "\nSome cards failed to download:\n" + "\n".join(self.error_log)
            
            self.queue_action("complete", True, msg)

        except Exception as e:
            self.queue_action("status", "An error occurred.")
            self.queue_action("complete", False, str(e))

if __name__ == "__main__":
    app = MTGPDFGeneratorGUI()
    app.mainloop()
