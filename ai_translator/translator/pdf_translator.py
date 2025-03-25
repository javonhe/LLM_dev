from typing import Optional
from ai_translator.model import Model
from translator.pdf_parser import PDFParser
from translator.writer import Writer
from utils import LOG

class PDFTranslator:
    def __init__(self, model: Model, progress_callback=None):
        self.model = model
        self.pdf_parser = PDFParser()
        self.writer = Writer()
        self.progress_callback = progress_callback

    def translate_pdf(self, pdf_file_path: str, file_format: str = 'PDF', target_language: str = '中文', output_file_path: str = None, pages: Optional[int] = None):
        self.book = self.pdf_parser.parse_pdf(pdf_file_path, pages)

        total = sum(len(page.contents) for page in self.book.pages)
        current = 0

        for page_idx, page in enumerate(self.book.pages):
            for content_idx, content in enumerate(page.contents):
                prompt = self.model.translate_prompt(content, target_language)
                LOG.debug(prompt)
                translation, status = self.model.make_request(prompt)
                LOG.info(translation)

                # Update the content in self.book.pages directly
                self.book.pages[page_idx].contents[content_idx].set_translation(translation, status)

                current += 1
                if self.progress_callback:
                    self.progress_callback(current/total*100)

        self.writer.save_translated_book(self.book, output_file_path, file_format)
