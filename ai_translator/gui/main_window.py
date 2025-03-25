import tkinter as tk
from tkinter import ttk, filedialog, font
from ai_translator.model import GLMModel, OpenAIModel
from ai_translator.translator import PDFTranslator
from ai_translator.utils import LOG
import os

class TranslationApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("AI PDF Translator")
        self.geometry("600x400")

        # 设置支持中文字符的字体配置
        self._configure_fonts()

        # 初始化模型和翻译器
        self.model = None
        self.translator = None

        self._create_widgets()

    def _configure_fonts(self):
        """配置字体以正确显示中文字符"""
        # 检查可用字体并使用支持中文的字体
        available_fonts = font.families()

        # 尝试找到支持中文的合适字体
        chinese_fonts = ["SimSun", "Microsoft YaHei", "NSimSun", "FangSong", "KaiTi",
                         "SimHei", "Arial Unicode MS", "WenQuanYi Micro Hei"]

        self.default_font = None
        for font_name in chinese_fonts:
            if font_name in available_fonts:
                self.default_font = font_name
                break

        if self.default_font:
            default_font = font.Font(family=self.default_font, size=10)
            self.option_add("*Font", default_font)

    def _create_widgets(self):
        # 文件选择
        ttk.Label(self, text="源文件:").grid(row=0, column=0, padx=5, pady=5)
        self.file_entry = ttk.Entry(self, width=40)
        self.file_entry.grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(self, text="浏览...", command=self._select_file).grid(row=0, column=2)

        # 目标语言
        ttk.Label(self, text="目标语言:").grid(row=1, column=0)
        self.lang_combo = ttk.Combobox(self, values=["中文", "英文", "日语"], state="readonly")
        self.lang_combo.current(0)
        self.lang_combo.grid(row=1, column=1, sticky=tk.W)

        # 输出格式
        ttk.Label(self, text="输出格式:").grid(row=2, column=0)
        self.format_combo = ttk.Combobox(self, values=["PDF", "Markdown"], state="readonly")
        self.format_combo.current(0)
        self.format_combo.grid(row=2, column=1, sticky=tk.W)

        # 保存路径
        ttk.Label(self, text="保存位置:").grid(row=3, column=0)
        self.save_entry = ttk.Entry(self, width=40)
        self.save_entry.grid(row=3, column=1)
        ttk.Button(self, text="浏览...", command=self._select_save_path).grid(row=3, column=2)

        # 模型选择
        ttk.Label(self, text="翻译模型:").grid(row=4, column=0)
        self.model_combo = ttk.Combobox(self, values=["OpenAI", "GLM"], state="readonly")
        self.model_combo.current(0)
        self.model_combo.grid(row=4, column=1, sticky=tk.W)

        # 翻译按钮
        self.translate_btn = ttk.Button(self, text="开始翻译", command=self._start_translation)
        self.translate_btn.grid(row=5, column=1, pady=20)

        # 进度条
        self.progress = ttk.Progressbar(self, mode='indeterminate')

    def _select_file(self):
        filepath = filedialog.askopenfilename(filetypes=[("PDF Files", "*.pdf")])
        if filepath:
            self.file_entry.delete(0, tk.END)
            self.file_entry.insert(0, filepath)
            # 自动生成默认保存路径
            default_save = filepath.rsplit('.', 1)[0] + "_translated"
            self.save_entry.delete(0, tk.END)
            self.save_entry.insert(0, default_save)

    def _select_save_path(self):
        path = filedialog.asksaveasfilename(defaultextension=".pdf")
        if path:
            self.save_entry.delete(0, tk.END)
            self.save_entry.insert(0, path)

    def _start_translation(self):
        # 从界面获取参数
        config = {
            'pdf_file_path': self.file_entry.get(),
            'file_format': self.format_combo.get().lower(),
            'target_language': self.lang_combo.get(),
            'output_file_path': self.save_entry.get()
        }

        # 初始化模型
        if self.model_combo.get() == "OpenAI":
            self.model = OpenAIModel(model="gpt-3.5-turbo")
        else:
            self.model = GLMModel(model_url="GLM_API_URL", timeout=30)

        # 执行翻译
        self.translator = PDFTranslator(self.model)
        try:
            self.translator.translate_pdf(
                config['pdf_file_path'],
                config['file_format'],
                config['target_language'],
                config['output_file_path']
            )
            self._show_message("翻译完成！")
        except Exception as e:
            LOG.error(f"翻译失败: {e}")
            self._show_message(f"错误: {str(e)}")

    def _show_message(self, msg):
        popup = tk.Toplevel()
        popup.title("提示")
        ttk.Label(popup, text=msg).pack(padx=20, pady=20)
        ttk.Button(popup, text="确定", command=popup.destroy).pack(pady=10)