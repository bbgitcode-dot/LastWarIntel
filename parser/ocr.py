import easyocr


def create_reader():
    return easyocr.Reader(["en"], gpu=False)


def read_ocr(reader, image):
    return reader.readtext(image, detail=1, paragraph=False)


def ocr_to_text(ocr_results):
    return "\n".join([item[1] for item in ocr_results])