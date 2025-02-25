import os
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk  # <--- Install Pillow for image display
import threading
import queue
from functools import partial
import re
import time

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
        preview_window.minsize(600, 400)
        preview_window.geometry("800x600")

        # Create main container with reduced padding
        container = tk.Frame(preview_window, padx=5, pady=5)
        container.pack(fill=tk.BOTH, expand=True)

        # Make it scrollable
        canvas = tk.Canvas(container)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        scroll_frame = tk.Frame(canvas)

        # Configure scrolling
        scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # Pack scrollbar and canvas
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Add mousewheel scrolling
        def _on_mousewheel(event):
            # Handle platform-specific scroll behavior
            if hasattr(event, 'num') and event.num == 4 or hasattr(event, 'delta') and event.delta > 0:  # Scroll up
                canvas.yview_scroll(-1, "units")
            elif hasattr(event, 'num') and event.num == 5 or hasattr(event, 'delta') and event.delta < 0:  # Scroll down
                canvas.yview_scroll(1, "units")
        
        # Helper function to bind mousewheel to all child widgets recursively
        def bind_mousewheel_to_children(widget):
            if self.tk.call('tk', 'windowingsystem') == 'aqua':  # macOS
                widget.bind("<MouseWheel>", _on_mousewheel)
            else:  # Windows and Linux
                widget.bind("<MouseWheel>", _on_mousewheel)  # Windows
                widget.bind("<Button-4>", _on_mousewheel)    # Linux scroll up
                widget.bind("<Button-5>", _on_mousewheel)    # Linux scroll down
            
            # Recursively bind to all children as they're created
            widget.bind_class("Widget", "<Button-4>", _on_mousewheel)
            widget.bind_class("Widget", "<Button-5>", _on_mousewheel)
            widget.bind_class("Widget", "<MouseWheel>", _on_mousewheel)
        
        # Bind mousewheel events to container and canvas
        bind_mousewheel_to_children(container)
        bind_mousewheel_to_children(canvas)
        bind_mousewheel_to_children(scroll_frame)
        
        # Bind to the preview window itself
        bind_mousewheel_to_children(preview_window)
        
        # Make sure canvas has focus for mousewheel events
        canvas.focus_set()

        # Store image references
        self._preview_images_cache = []
        
        # Load all card images first
        card_images = []
        loading_label = tk.Label(scroll_frame, text="Loading images, please wait...", font=("Helvetica", 14))
        loading_label.pack(pady=20)
        preview_window.update()
        
        for card_tuple in deck:
            card_name, variant_info = card_tuple
            safe_name = self.sanitize_filename(card_name)
            
            front_path = os.path.join(self.image_folder, f"{safe_name}_front.jpg")
            back_path = os.path.join(self.image_folder, f"{safe_name}_back.jpg")
            
            if not os.path.exists(front_path):
                continue
                
            if not os.path.exists(back_path):
                back_path = self.card_back_file.get()
            
            try:
                # Preload and process images
                img_front = Image.open(front_path)
                img_front = img_front.resize((100, 140), Image.Resampling.LANCZOS)
                tk_front = ImageTk.PhotoImage(img_front)
                
                img_back = Image.open(back_path)
                img_back = img_back.resize((100, 140), Image.Resampling.LANCZOS)
                tk_back = ImageTk.PhotoImage(img_back)
                
                card_images.append((card_name, tk_front, tk_back))
                self._preview_images_cache.extend([tk_front, tk_back])
            except Exception as e:
                print(f"Error loading image for {card_name}: {e}")
                continue
        
        # Remove loading label
        loading_label.destroy()
        
        # Calculate fixed layout
        def update_layout(initial_width=None):
            # Clear existing widgets
            for widget in scroll_frame.winfo_children():
                widget.destroy()
                
            # Get current width or use initial width parameter
            width = initial_width if initial_width else canvas.winfo_width()
            # Subtract container padding (2 * 5 = 10) from available width
            width -= 10
            
            # Default width if window hasn't been drawn yet
            if width <= 1:
                width = 700  # Default width (container width minus scrollbar)
                
            card_width = 100
            label_width = 120
            spacing = 10
            content_width = card_width * 2 + label_width + spacing * 4  # Two cards + label + spacing
            
            # At least 1 column, at most what fits in the window
            cols = max(1, width // content_width)
            
            # Create grid layout
            for i, (card_name, front_img, back_img) in enumerate(card_images):
                row = i // cols
                col = i % cols
                
                # Create a frame for each card set
                card_frame = tk.Frame(scroll_frame)
                card_frame.grid(row=row, column=col, padx=spacing, pady=spacing, sticky="nsew")
                
                # Make each column in card_frame expand equally
                card_frame.grid_columnconfigure(0, weight=1, uniform="card_cols")
                card_frame.grid_columnconfigure(1, weight=1, uniform="card_cols")
                card_frame.grid_columnconfigure(2, weight=1, uniform="card_cols")
                card_frame.grid_rowconfigure(0, weight=1)

                # Place front, name, and back with sticky="nsew" to fill space
                front_label = tk.Label(card_frame, image=front_img)
                front_label.grid(row=0, column=0, sticky="nsew", padx=spacing, pady=spacing)

                name_label = tk.Label(card_frame, text=card_name, wraplength=label_width)
                name_label.grid(row=0, column=1, sticky="nsew", padx=spacing, pady=spacing)

                back_label = tk.Label(card_frame, image=back_img)
                back_label.grid(row=0, column=2, sticky="nsew", padx=spacing, pady=spacing)
            
            # Bind mousewheel to all newly created widgets
            for widget in scroll_frame.winfo_children():
                bind_mousewheel_to_children(widget)
            
            # Update the scrollregion to encompass all items
            scroll_frame.update_idletasks()
            canvas.configure(scrollregion=canvas.bbox("all"))
        
        # Use a single timer for resize events
        resize_timer = None
        def delayed_resize(event=None):
            nonlocal resize_timer
            if resize_timer:
                preview_window.after_cancel(resize_timer)
            resize_timer = preview_window.after(300, update_layout)
        
        # Bind resize handler
        canvas.bind("<Configure>", delayed_resize)
        
        # Initial layout - schedule this after window is shown
        def show_initial_layout():
            # Get container width for initial calculation
            container_width = container.winfo_width()
            update_layout(container_width)
        
        # Schedule the initial layout after window appears
        # Use after_idle for the most immediate execution after window drawing
        preview_window.after(100, show_initial_layout)
        
        # Clean up when window closes
        def on_closing():
            nonlocal resize_timer
            if resize_timer:
                preview_window.after_cancel(resize_timer)
            preview_window.destroy()
        
        preview_window.protocol("WM_DELETE_WINDOW", on_closing)

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
