from pathlib import Path
from pypdf import PdfReader
from docx import Document


def parse_pdf(file_path: str) -> str:
    """解析 PDF，提取文本"""

    reader = PdfReader(file_path)

    texts = []

    for page in reader.pages:
        text = page.extract_text()

        if text:
            texts.append(text)

    return "\n".join(texts)


def parse_docx(file_path: str) -> str:
    """解析 Word，提取文本"""

    document = Document(file_path)

    texts = []

    for paragraph in document.paragraphs:
        text = paragraph.text.strip()

        if text:
            texts.append(text)

    return "\n".join(texts)


def parse_resume(file_path: str) -> str:
    """自动根据文件类型解析简历"""

    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(
            f"简历文件不存在：{file_path}"
        )

    suffix = path.suffix.lower()

    if suffix == ".pdf":
        return parse_pdf(file_path)

    elif suffix == ".docx":
        return parse_docx(file_path)

    else:
        raise ValueError(
            f"暂不支持的文件格式：{suffix}"
        )


if __name__ == "__main__":

    # 这里填写你的简历文件路径
    resume_path = "data/实习简历1.pdf"

    text = parse_resume(resume_path)

    print("=" * 60)
    print("简历文本提取成功")
    print("=" * 60)

    print(text)