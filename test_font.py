import fitz

doc = fitz.open()
page = doc.new_page()
font_path = "/System/Library/Fonts/ヒラギノ角ゴシック W8.ttc"
try:
    page.insert_font(fontname="F0", fontfile=font_path)
    res = page.insert_textbox(fitz.Rect(10, 10, 500, 500), "テストです。 翻訳テスト。", fontname="F0", fontsize=11)
    if res < 0:
        print("Text didn't fit")
    doc.save("test_font.pdf")
    doc.close()

    doc2 = fitz.open("test_font.pdf")
    text = doc2[0].get_text("text")
    print("Extracted:", repr(text))
except Exception as e:
    print(e)
