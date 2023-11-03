import os
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, PhotoImage, Label
from PIL import Image
import subprocess
import platform
import threading
import queue
import docx
import fitz
from PIL import ImageTk


class MarkdownSearchApp:
    def __init__(self, root):
        self.root = root
        self.current_page = 0
        self.page_size = 1  # Display the results of one file per page
        self.results_by_file = {}
        self.search_cache = {}  # Cache for storing search results
        self.directory = None  # Directory to be searched
        self.search_queue = queue.Queue()  # Queue to manage search results

        # Load background image
        image = Image.open('C:\\Users\\lth\\Desktop\\微信图片_20231103015351.png')
        self.background_image = ImageTk.PhotoImage(image)

        # Set background image
        self.background_label = tk.Label(root, image=self.background_image)
        self.background_label.place(x=0, y=0, relwidth=1, relheight=1)

        root.geometry("900x1000")  # Set the initial window size
        root.title("Ink Trace Search")

        # Create input box and buttons
        self.default_entry_text = 'Enter the keyword to search for'
        self.entry_keyword = tk.Entry(root, width=50)
        self.entry_keyword.pack(pady=5)
        self.entry_keyword.insert(0, self.default_entry_text)
        self.entry_keyword.bind("<FocusIn>", self.clear_entry)
        self.entry_keyword.bind("<FocusOut>", self.reset_entry)

        self.label_path = tk.Label(root, text="Directory not selected", fg="blue")
        self.label_path.pack(pady=5)

        self.btn_open_dir = tk.Button(root, text="Open Directory", command=self.open_directory)
        self.btn_open_dir.pack(pady=5)

        self.btn_search = tk.Button(root, text="Search", command=self.search_keyword)
        self.btn_search.pack(pady=5)

        # Create a scrolled text box to display results
        self.text_result = scrolledtext.ScrolledText(root, height=30, width=100)
        self.text_result.pack(pady=10)

        # Pagination buttons
        nav_frame = tk.Frame(root)
        nav_frame.pack(pady=5)

        self.btn_prev_page = tk.Button(nav_frame, text="<< Previous Page", command=self.prev_page)
        self.btn_prev_page.pack(side=tk.LEFT, padx=10)

        # New label for showing current page / total pages
        self.page_number_label = tk.Label(nav_frame, text="Page 0/0")
        self.page_number_label.pack(side=tk.LEFT, padx=10)

        self.btn_next_page = tk.Button(nav_frame, text="Next Page >>", command=self.next_page)
        self.btn_next_page.pack(side=tk.RIGHT, padx=10)

        # Label for file type selection
        self.label_file_type = tk.Label(root, text="Select the file format to search for:")
        self.label_file_type.pack(pady=(10, 0))  # Leave some space above the dropdown

        # Dropdown for file type selection
        self.file_type_var = tk.StringVar()
        self.file_type_var.set("markdown")  # default value
        self.file_type_options = ["markdown", "word", "pdf", "all"]
        self.file_type_menu = tk.OptionMenu(root, self.file_type_var, *self.file_type_options)
        self.file_type_menu.pack(pady=5)

        # Copyright information label
        self.label_copyright = tk.Label(root,
                                        text="Produced by HangerLin\nEmbrace open source No commercial use\nContact WeChat for any issues: 17788463828 or HangerLIN via github",
                                        fg="blue")
        self.label_copyright.pack(side=tk.BOTTOM)

        # Start a thread to process search results
        self.processing_thread = threading.Thread(target=self.process_search_results, daemon=True)
        self.processing_thread.start()

    def clear_entry(self, event):
        """Clear the default text in the entry box on focus."""
        if self.entry_keyword.get() == self.default_entry_text:
            self.entry_keyword.delete(0, tk.END)

    def reset_entry(self, event):
        """Reset the default text if the entry box is empty when focus is lost."""
        if not self.entry_keyword.get():
            self.entry_keyword.insert(0, self.default_entry_text)

    def open_directory(self):
        directory = filedialog.askdirectory()
        if directory:
            self.directory = directory
            self.label_path.config(text=self.directory)
            self.search_cache = {}  # Clear cache when a new directory is selected
        else:
            self.label_path.config(text="Directory not selected")

    def search_keyword(self):
        keyword = self.entry_keyword.get()
        if not self.directory or not keyword.strip():
            messagebox.showwarning("Warning", "Please select a directory and enter a keyword.")
            return

        # Change the button color to red when the search starts
        self.btn_search.config(bg='red', state='disabled')

        # Start the search in a separate thread to avoid UI freezing
        threading.Thread(target=self.perform_search, args=(keyword,), daemon=True).start()

    def kmp_table(self, word):
        table = [0] * len(word)
        j = 0
        for i in range(1, len(word)):
            if word[i] == word[j]:
                j += 1
                table[i] = j
            else:
                if j != 0:
                    j = table[j - 1]
                    i -= 1
                else:
                    table[i] = 0
        return table

    def kmp_search(self, text, word):
        table = self.kmp_table(word)
        matches = []

        m = i = 0
        while m + i < len(text):
            if word[i] == text[m + i]:
                if i == len(word) - 1:
                    matches.append(m)
                    m = m + i - table[i]
                    i = 0
                else:
                    i += 1
            else:
                if i != 0:
                    m = m + i - table[i]
                    i = table[i - 1]
                else:
                    m += 1
                    i = 0
        return matches

    # def perform_search(self, keyword):
    #     # 如果可用，使用缓存的结果
    #     if keyword in self.search_cache:
    #         self.search_queue.put(self.search_cache[keyword])
    #     else:
    #         results_by_file = {}  # 重置搜索结果
    #
    #     for root, dirs, files in os.walk(self.directory):
    #         for file in files:
    #             if file.endswith('.md'):
    #                 file_path = os.path.join(root, file)
    #                 with open(file_path, 'r', encoding='utf-8') as f:
    #                     content = f.read()
    #                     matches = self.kmp_search(content, keyword)
    #                     sentences = []
    #                     for match in matches:
    #                         start = max(content.rfind('.', 0, match) + 1, 0)
    #                         end = content.find('.', match) + 1
    #                         sentence = content[start:end].strip()
    #                         if sentence:
    #                             sentences.append(sentence)
    #                     if sentences:
    #                         results_by_file[file_path] = sentences
    #         self.search_cache[keyword] = results_by_file
    #         self.search_queue.put(results_by_file)
    #
    #     self.root.after(0, self.reset_search_button)

    def perform_search(self, keyword):
        # Use cached results if available
        if keyword in self.search_cache:
            self.search_queue.put(self.search_cache[keyword])
            return

        results_by_file = {}  # Reset search results
        file_types = {
            'markdown': ('.md',),
            'word': ('.docx',),
            'pdf': ('.pdf',),
            'all': ('.md', '.docx', '.pdf'),
        }

        selected_file_type = self.file_type_var.get()
        valid_extensions = file_types[selected_file_type]

        for root, dirs, files in os.walk(self.directory):
            for file in files:
                if file.endswith(valid_extensions):
                    file_path = os.path.join(root, file)
                    content = self.read_file_content(file_path)

                    # Search for the keyword using the KMP algorithm
                    matches = self.kmp_search(content, keyword)
                    sentences = []
                    for match in matches:
                        start = max(content.rfind('.', 0, match) + 1, 0)
                        end = content.find('.', match) + 1
                        sentence = content[start:end].strip()
                        if sentence:
                            sentences.append(sentence)
                    if sentences:
                        results_by_file[file_path] = sentences
        self.search_cache[keyword] = results_by_file
        self.search_queue.put(results_by_file)

    def read_file_content(self, file_path):
        content = ''
        try:
            if file_path.endswith('.md'):
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

            elif file_path.endswith('.docx'):
                try:
                    doc = docx.Document(file_path)
                    content = '\n'.join([para.text for para in doc.paragraphs])
                except Exception as e:
                    print(f"无法读取.docx文件: {file_path}, 错误: {e}")
                    content = "&#8203;``【oaicite:1】``&#8203;无法读取文件内容。"

            elif file_path.endswith('.pdf'):
                with fitz.open(file_path) as doc:
                    content = '\n'.join([page.get_text() for page in doc])

        except Exception as e:
            print(f"读取文件时发生错误: {e}")
            content = "&#8203;``【oaicite:0】``&#8203;无法读取文件内容。"

        return content

    def reset_search_button(self):
        # Restore the button's default color and enable it
        self.btn_search.config(bg='SystemButtonFace', state='normal')

    def process_search_results(self):
        while True:
            # Retrieve results from the queue
            self.results_by_file = self.search_queue.get()
            self.current_page = 0  # Reset to the first page
            # Schedule display_page to run on the main thread
            self.root.after(0, self.display_page)

    # def perform_search(self, keyword):
    #     # 如果可用，使用缓存的结果
    #     if keyword in self.search_cache:
    #         self.search_queue.put(self.search_cache[keyword])
    #     else:
    #         results_by_file = {}  # 重置搜索结果
    #         for root, dirs, files in os.walk(self.directory):
    #             for file in files:
    #                 if file.endswith('.md'):
    #                     file_path = os.path.join(root, file)
    #                     with open(file_path, 'r', encoding='utf-8') as f:
    #                         content = f.read()
    #                         sentences = re.findall(r'[^.]*' + re.escape(keyword) + r'[^.]*\.', content)
    #                         if sentences:
    #                             results_by_file[file_path] = sentences
    #         self.search_cache[keyword] = results_by_file  # 缓存结果
    #         self.search_queue.put(results_by_file)  # 将结果放入队列
    #
    #     # 搜索结束后重置按钮颜色
    #     self.root.after(0, self.reset_search_button)

    # def perform_search(self, keyword):
    #     # 如果可用，使用缓存的结果
    #     if keyword in self.search_cache:
    #         self.search_queue.put(self.search_cache[keyword])
    #     else:
    #         results_by_file = {}  # 重置搜索结果
    #         for root, dirs, files in os.walk(self.directory):
    #             for file in files:
    #                 if file.endswith('.md'):
    #                     file_path = os.path.join(root, file)
    #                     with open(file_path, 'r', encoding='utf-8') as f:
    #                         content = f.read()
    #                         # 使用 Boyer-Moore 算法搜索关键字
    #                         sentences = self.find_with_boyer_moore(content, keyword)
    #                         if sentences:
    #                             results_by_file[file_path] = sentences
    #         self.search_cache[keyword] = results_by_file  # 缓存结果
    #         self.search_queue.put(results_by_file)  # 将结果放入队列
    #
    #     # 搜索结束后重置按钮颜色
    #     self.root.after(0, self.reset_search_button)

    def display_page(self):
        self.text_result.delete(1.0, tk.END)  # Clear the text box
        start = self.current_page * self.page_size
        end = start + self.page_size
        file_paths = list(self.results_by_file.keys())[start:end]

        for file_path in file_paths:
            # Calculate relative path from the directory to the file
            relative_path = os.path.relpath(file_path, self.directory)
            display_text = f"File: {os.path.basename(file_path)} [{relative_path}]\n"
            self.text_result.insert(tk.END, display_text, 'file')
            # Use an inline function to create a closure
            callback = lambda e, path=file_path: self.open_file(path)
            self.text_result.tag_bind('file', '<Button-1>', callback)

            sentences = self.results_by_file[file_path]
            for i, sentence in enumerate(sentences):
                self.highlight_text(sentence, self.entry_keyword.get())
                # Add a separator after each match, except for the last one
                if i < len(sentences) - 1:
                    self.text_result.insert(tk.END, "\n--------------------------------\n")

            self.text_result.insert(tk.END, "\n")

        # Calculate the total number of pages and update the label
        total_pages = len(self.results_by_file) // self.page_size
        if len(self.results_by_file) % self.page_size > 0:
            total_pages += 1
        self.page_number_label.config(text=f"Page {self.current_page + 1}/{total_pages}")

        self.update_pagination_buttons()

    def update_pagination_buttons(self):
        # Update the state of the previous page button
        if self.current_page == 0:
            self.btn_prev_page["state"] = "disabled"
        else:
            self.btn_prev_page["state"] = "normal"

        # Update the state of the next page button
        if (self.current_page + 1) * self.page_size >= len(self.results_by_file):
            self.btn_next_page["state"] = "disabled"
        else:
            self.btn_next_page["state"] = "normal"

        # Calculate the total number of pages and update the label
        total_pages = len(self.results_by_file) // self.page_size
        if len(self.results_by_file) % self.page_size > 0:
            total_pages += 1
        self.page_number_label.config(text=f"Page {self.current_page + 1}/{total_pages}")


    def highlight_text(self, text, keyword):
        start_index = self.text_result.index(tk.END)
        self.text_result.insert(tk.END, text + "\n")
        end_index = self.text_result.index(tk.END)
        self.text_result.tag_add("highlight", start_index, end_index)
        self.text_result.tag_config("highlight", foreground="blue")

        # Search for the keyword and apply the highlight
        start = start_index
        while True:
            pos = self.text_result.search(keyword, start, stopindex=end_index)
            if not pos:
                break
            endpos = f"{pos}+{len(keyword)}c"
            self.text_result.tag_add('match', pos, endpos)
            start = endpos
        self.text_result.tag_config('match', foreground='blue', background='yellow')

    def update_pagination_buttons(self):
        if self.current_page == 0:
            self.btn_prev_page["state"] = "disabled"
        else:
            self.btn_prev_page["state"] = "normal"

        if (self.current_page + 1) * self.page_size >= len(self.results_by_file):
            self.btn_next_page["state"] = "disabled"
        else:
            self.btn_next_page["state"] = "normal"

    def prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self.display_page()

    def next_page(self):
        if (self.current_page + 1) * self.page_size < len(self.results_by_file):
            self.current_page += 1
            self.display_page()

    def open_file(self, file_path):
        print(f"Trying to open: {file_path}")  # Debug output
        if not os.path.isfile(file_path):
            messagebox.showerror("Error", f"The file {file_path} does not exist.")
            return

        try:
            if platform.system() == 'Darwin':  # macOS
                subprocess.call(('open', file_path))
            elif platform.system() == 'Windows':  # Windows
                os.startfile(file_path)
            else:  # Linux
                subprocess.call(('xdg-open', file_path))
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred while opening the file: {e}")


if __name__ == "__main__":
    root = tk.Tk()

    app = MarkdownSearchApp(root)
    root.mainloop()
