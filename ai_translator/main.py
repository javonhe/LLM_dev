import sys
import os

# 修改为获取项目根目录路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)  # 替换原来的sys.path.append

from utils import ArgumentParser, ConfigLoader, LOG
from model import GLMModel, OpenAIModel
from translator import PDFTranslator
from gui.main_window import TranslationApp  # 新增

if __name__ == "__main__":
    if len(sys.argv) == 1:  # 无参数时启动GUI
        app = TranslationApp()
        app.mainloop()
    else:  # 保留原有命令行模式
        argument_parser = ArgumentParser()
        args = argument_parser.parse_arguments()
        config_loader = ConfigLoader(args.config)

        config = config_loader.load_config()

        model_name = args.openai_model if args.openai_model else config['OpenAIModel']['model']
        api_key = args.openai_api_key if args.openai_api_key else config['OpenAIModel']['api_key']
        model = OpenAIModel(model=model_name, api_key=api_key)


        pdf_file_path = args.book if args.book else config['common']['book']
        file_format = args.file_format if args.file_format else config['common']['file_format']

        # 实例化 PDFTranslator 类，并调用 translate_pdf() 方法
        translator = PDFTranslator(model)
        translator.translate_pdf(pdf_file_path, file_format)
