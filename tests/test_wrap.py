import fitz
doc = fitz.open()
page = doc.new_page()
font_path = "/System/Library/Fonts/ヒラギノ角ゴシック W8.ttc"
page.insert_font(fontname="notojp", fontfile=font_path)

long_text = "深層ニューラルネットワークは自然言語処理に大きな影響を与えています。"
zws_text = "".join(c + "\u200B" for c in long_text)

# Small bbox width to force wrap
res = page.insert_textbox(fitz.Rect(10, 10, 100, 500), zws_text, fontname="notojp", fontsize=11)
print(f"Result < 0 means overflow: {res}")
doc.save("test_wrap.pdf")
doc.close()
