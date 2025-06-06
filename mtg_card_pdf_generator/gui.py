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
from tqdm import tqdm

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

        # Set background color for dark mode
        self.configure(bg="#2e2e2e")

        # Apply dark mode styles
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TLabel", background="#2e2e2e", foreground="#ffffff")
        style.configure("TButton", background="#444444", foreground="#ffffff", borderwidth=0, relief="flat")
        style.configure("TEntry", fieldbackground="#444444", foreground="#ffffff", borderwidth=0, relief="flat")
        style.configure("TFrame", background="#2e2e2e")
        style.configure("TProgressbar", troughcolor="#444444", background="#00ff00", borderwidth=0, relief="flat")
        style.map("TButton", 
                  background=[("active", "#555555")],
                  relief=[("pressed", "flat"), ("!pressed", "flat")])

        # Modernize input fields
        style.configure("Rounded.TEntry", fieldbackground="#444444", foreground="#ffffff", borderwidth=0, relief="flat", padding=5)
        style.layout("Rounded.TEntry", [
            ("Entry.field", {"children": [("Entry.padding", {"children": [("Entry.textarea", {"sticky": "nswe"})], "sticky": "nswe"})], "sticky": "nswe"})])
        style.configure("Rounded.TEntry", bordercolor="#444444", lightcolor="#444444", darkcolor="#444444", borderwidth=0, relief="flat")

        # Variables for file paths and status
        self.decklist_file = tk.StringVar()
        self.output_pdf = tk.StringVar(value="mtg_cards_print.pdf")
        self.card_back_file = tk.StringVar(value="assets/card_back.jpg")
        self.status_text = tk.StringVar(value="Idle")
        self.success_message = tk.StringVar(value="")
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
        # Create a "main_frame" that expands and centers with padding
        main_frame = ttk.Frame(self, padding=20)  # Add 20 pixels padding around all sides
        main_frame.pack(expand=True, fill="both", padx=20, pady=20)  # Add additional window padding

        # Decklist file selection
        ttk.Label(main_frame, text="Decklist File:").pack(pady=10)
        frame = ttk.Frame(main_frame)
        frame.pack(pady=5)
        ttk.Entry(frame, textvariable=self.decklist_file, width=50, style="Rounded.TEntry").pack(side=tk.LEFT, padx=5)
        ttk.Button(frame, text="Browse", command=self.browse_file).pack(side=tk.LEFT)

        # Custom card back file selection
        ttk.Label(main_frame, text="Custom Card Back:").pack(pady=10)
        frame_back = ttk.Frame(main_frame)
        frame_back.pack(pady=5)
        ttk.Entry(frame_back, textvariable=self.card_back_file, width=50, style="Rounded.TEntry").pack(side=tk.LEFT, padx=5)
        ttk.Button(frame_back, text="Browse", command=self.browse_back).pack(side=tk.LEFT)

        # Status and progress bar
        ttk.Label(main_frame, textvariable=self.status_text).pack(pady=10)
        self.progress_bar = ttk.Progressbar(main_frame, orient="horizontal", length=400, mode="determinate")
        self.progress_bar.pack(pady=10)

        # Console log text area (formerly error log)
        ttk.Label(main_frame, text="Console Output:").pack(pady=(10, 0))
        self.console_text = tk.Text(main_frame, height=8, width=70, state="disabled", 
                                  bg="#2b2b2b", fg="#e6e6e6", bd=0, relief="flat",
                                  font=("Consolas", 9))
        self.console_text.pack(pady=(0,10))

        # Success message label with yellow color
        self.success_label = ttk.Label(main_frame, textvariable=self.success_message, foreground="#ffff00")
        self.success_label.pack(pady=10)

        # Generate PDF button
        ttk.Button(main_frame, text="Generate PDF", command=self.start_generation, width=20).pack(pady=10)
        # Add a separate "Save PDF" button (initially disabled)
        self.save_button = ttk.Button(main_frame, text="Save PDF", command=self.save_pdf, state="disabled", width=20)
        self.save_button.pack(pady=5)

        # Code for potential later use
        # Output PDF file selection
        # ttk.Label(main_frame, text="Output PDF File:").pack(pady=10)
        # frame2 = ttk.Frame(main_frame)
        # frame2.pack(pady=5)
        # ttk.Entry(frame2, textvariable=self.output_pdf, width=50, style="Rounded.TEntry").pack(side=tk.LEFT, padx=5)
        # ttk.Button(frame2, text="Browse", command=self.browse_output).pack(side=tk.LEFT)

        # Add a new button for previewing card images
        # ttk.Button(main_frame, text="Preview Images", command=self.preview_deck_images, width=20).pack(pady=5)

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
                    self.log_message(args)
                elif action == "progress":
                    self.progress_bar["value"] = args
                elif action == "log":
                    self.log_message(*args)
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
            if isinstance(widget, ttk.Button):
                widget.config(state="disabled")

        self.status_text.set("Processing decklist...")
        self.progress_bar["value"] = 0
        self.clear_console()
        self.success_message.set("")

        # Start worker thread
        self.current_thread = threading.Thread(target=self.generate_pdf_workflow)
        self.current_thread.daemon = True
        self.current_thread.start()

    def _handle_completion(self, success, message):
        """Handle completion of the generation process."""
        # Re-enable buttons
        for widget in self.winfo_children():
            if isinstance(widget, ttk.Button):
                widget.config(state="normal")
        
        if success:
            self.save_button.config(state="normal")
            self.success_message.set(message)
        else:
            self.save_button.config(state="disabled")
            self.success_message.set(message)

    def log_message(self, message, level="INFO"):
        """Log a message to the console text widget."""
        message = str(message)
        timestamp = time.strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {level}: {message}\n"
        
        self.console_text.config(state="normal")
        self.console_text.insert(tk.END, formatted_message)
        self.console_text.see(tk.END)  # Auto-scroll to bottom
        self.console_text.config(state="disabled")

    def clear_console(self):
        self.console_text.config(state="normal")
        self.console_text.delete("1.0", tk.END)
        self.console_text.config(state="disabled")

    def save_pdf(self):
        """Copy the generated PDF to a new location."""
        filename = filedialog.asksaveasfilename(title="Save PDF As",
                                                defaultextension=".pdf",
                                                filetypes=[("PDF Files", "*.pdf")])
        if filename:
            try:
                shutil.copy(self.output_pdf.get(), filename)
                self.success_label.configure(foreground="#00ff00")  # Change to green
                self.success_message.set(f"PDF saved as {filename}")
            except Exception as e:
                self.success_label.configure(foreground="#ffff00")  # Keep yellow for errors
                self.success_message.set(f"Could not save PDF: {e}")

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
        container = ttk.Frame(preview_window, padding=(5, 5))
        container.pack(fill=tk.BOTH, expand=True)

        # Make it scrollable
        canvas = tk.Canvas(container)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        scroll_frame = ttk.Frame(canvas)

        # Configure scrolling
        scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # Pack scrollbar and canvas
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Add mousewheel scrolling
        def _on_mousewheel(event):
            # Check if Ctrl is pressed (state & 0x0004 is typical on Windows)
            if (event.state & 0x0004) != 0:
                # Zoom in/out
                if (hasattr(event, 'num') and event.num == 4) or (hasattr(event, 'delta') and event.delta > 0):
                    self._preview_zoom_scale += 0.1
                else:
                    self._preview_zoom_scale = max(0.1, self._preview_zoom_scale - 0.1)
                update_layout()
            else:
                # Normal scrolling
                if (hasattr(event, 'num') and event.num == 4) or (hasattr(event, 'delta') and event.delta > 0):
                    canvas.yview_scroll(-1, "units")
                else:
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
        
        # Zoom scale for adjusting card size
        self._preview_zoom_scale = 1.0
        
        # Store original PIL images to allow repeated resizing
        original_images = []
        
        # Load all card images first
        card_images = []
        loading_label = ttk.Label(scroll_frame, text="Loading images, please wait...", font=("Helvetica", 14))
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
                # Save original PIL images alongside card_name
                original_images.append((card_name, img_front, img_back))
            except Exception as e:
                print(f"Error loading image for {card_name}: {e}")
                continue
        
        # Remove loading label
        loading_label.destroy()
        
        # Calculate fixed layout
        def update_layout(initial_width=None):
            for widget in scroll_frame.winfo_children():
                widget.destroy()

            width = initial_width if initial_width else canvas.winfo_width()
            width -= 10  # account for container padding
            if width <= 1:
                width = 700

            # Recompute card sizes based on zoom
            base_card_width = 100
            base_card_height = 140
            scaled_card_width = int(base_card_width * self._preview_zoom_scale)
            scaled_card_height = int(base_card_height * self._preview_zoom_scale)
            scaled_label_width = int(120 * self._preview_zoom_scale)
            spacing = 10
            content_width = scaled_card_width * 2 + scaled_label_width + spacing * 4

            cols = max(1, width // content_width)

            # Refresh card_images with new sizes
            card_images.clear()
            for (card_name, pil_front, pil_back) in original_images:
                try:
                    # Resize for the current zoom
                    resized_front = pil_front.resize((scaled_card_width, scaled_card_height), Image.Resampling.LANCZOS)
                    tk_front = ImageTk.PhotoImage(resized_front)
                    resized_back = pil_back.resize((scaled_card_width, scaled_card_height), Image.Resampling.LANCZOS)
                    tk_back = ImageTk.PhotoImage(resized_back)
                    card_images.append((card_name, tk_front, tk_back))
                    self._preview_images_cache.extend([tk_front, tk_back])
                except:
                    continue

            for i, (card_name, front_img, back_img) in enumerate(card_images):
                row = i // cols
                col = i % cols
                card_frame = ttk.Frame(scroll_frame)
                card_frame.grid(row=row, column=col, padx=spacing, pady=spacing, sticky="nsew")

                card_frame.grid_columnconfigure(0, weight=1, uniform="card_cols")
                card_frame.grid_columnconfigure(1, weight=1, uniform="card_cols")
                card_frame.grid_columnconfigure(2, weight=1, uniform="card_cols")
                card_frame.grid_rowconfigure(0, weight=1)

                ttk.Label(card_frame, image=front_img).grid(row=0, column=0, sticky="nsew", padx=spacing, pady=spacing)
                ttk.Label(card_frame, text=card_name, wraplength=scaled_label_width).grid(row=0, column=1, sticky="nsew", padx=spacing, pady=spacing)
                ttk.Label(card_frame, image=back_img).grid(row=0, column=2, sticky="nsew", padx=spacing, pady=spacing)

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

            card_images = []
            total_cards = len(deck)
            
            self.queue_action("log", ("Starting card image downloads...", "INFO"))
            
            with tqdm(total=total_cards, desc="Overall Progress", unit="card") as pbar:
                for index, card_tuple in enumerate(deck):
                    card_name, variant_info = card_tuple
                    self.queue_action("status", f"Processing '{card_name}' ({index+1}/{total_cards})...")
                    self.queue_action("progress", (index / total_cards) * 50)

                    safe_name = self.sanitize_filename(card_name)
                    front_path = os.path.join(self.image_folder, f"{safe_name}_front.jpg")
                    back_path = os.path.join(self.image_folder, f"{safe_name}_back.jpg")

                    try:
                        if not os.path.exists(front_path):
                            sides = get_card_image_url(card_name, variant_info, image_size="normal")
                            download_image(sides.front_url, front_path)
                            if sides.back_url:
                                download_image(sides.back_url, back_path)
                                default_back = back_path
                            else:
                                default_back = self.card_back_file.get()
                        else:
                            self.queue_action("log", (f"Using cached: {safe_name}", "INFO"))
                            default_back = self.card_back_file.get()
                            if os.path.exists(back_path):
                                default_back = back_path
                                
                        card_images.append((front_path, default_back))
                        pbar.update(1)
                    except Exception as e:
                        error_msg = f"Error processing {card_name}: {e}"
                        self.queue_action("log", (error_msg, "ERROR"))
                        continue

            self.queue_action("log", ("Image processing complete!", "INFO"))

            if not card_images:
                self.queue_action("status", "No images downloaded.")
                self.queue_action("complete", False, "No images were successfully downloaded. Check the console log.")
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
            self.queue_action("log", ("PDF generation successful!", "INFO"))

            self.queue_action("complete", True, "PDF Generated: Remember to Save!")

        except Exception as e:
            self.queue_action("status", "An error occurred.")
            self.queue_action("log", (str(e), "ERROR"))
            self.queue_action("complete", False, str(e))

if __name__ == "__main__":
    app = MTGPDFGeneratorGUI()
    app.mainloop()
