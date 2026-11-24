import re
from datetime import date
import streamlit as st
from groq import Groq
from ddgs import DDGS
from weasyprint import HTML

client = Groq(api_key=st.secrets["GEMINI_API_KEY"])
MODEL = "llama-3.3-70b-versatile"  # потужна і швидка безкоштовна модель на Groq

def ask(prompt: str) -> str:
    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
    )
    text = response.choices[0].message.content
    return re.sub(r"^```(?:html)?|```$", "", text.strip(), flags=re.M).strip()

def search(query: str, n: int = 8) -> str:
    try:
        results = DDGS().text(query, max_results=n)
    except Exception:
        results = []
    return "\n".join(f"- {r['title']} | {r['href']} | {r['body']}" for r in results)

CSS = """@page { size: A4; margin: 2cm 2cm 2cm 3cm;        @bottom-center { content: counter(page); font-size: 10pt; } }
@page :first { @bottom-center { content: none; } }
body { font-family: 'DejaVu Serif', serif; font-size: 13pt; line-height: 1.5; }
h1 { font-size: 20pt; text-align: center; }
h2 { font-size: 16pt; margin-top: 1.2em; }
p { text-align: justify; text-indent: 1.25cm; margin: 0.3em 0; }
table { width: 100%; border-collapse: collapse; font-size: 12pt; }
th, td { border: 1px solid #999; padding: 6px 8px; text-align: left; }
th { background: #eee; }
.cover { height: 24cm; text-align: center; page-break-after: always; }
.cover .top { font-size: 14pt; }
.cover .title { margin-top: 7cm; font-size: 24pt; font-weight: bold; }
.cover .kind { margin-top: 1cm; font-size: 16pt; }
.cover .author { margin-top: 5cm; text-align: right; font-size: 13pt; }
.cover .year { margin-top: 3cm; font-size: 13pt; }
.sources li { margin-bottom: 4px; font-size: 11pt; word-break: break-all; }"""

def cover_html(title, kind, school, author):
    return f"""<div class="cover">
      <div class="top">{school}</div>
      <div class="title">{title}</div>
      <div class="kind">{kind}</div>
      <div class="author">Виконав(ла): {author}</div>
      <div class="year">{date.today().year}</div>
    </div>"""

def make_pdf(body_html: str, cover: str = "") -> bytes:
    html = f"<html><head><meta charset='utf-8'><style>{CSS}</style></head><body>{cover}{body_html}</body></html>"
    return HTML(string=html).write_pdf()

st.set_page_config(page_title="PDF генератор", page_icon="📄")
st.title("📄 PDF генератор")

mode = st.radio("Що робимо?", ["Реферат на тему", "Слова з англійської"])

with st.form("form"):
    if mode == "Реферат на тему":
        topic = st.text_input("Тема реферату")
        pages = st.slider("Приблизний обсяг (сторінок)", 3, 15, 5)
        lang = st.selectbox("Мова", ["українська", "англійська"])
    else:
        topic = st.text_area("Встав слова (по одному в рядок або через кому)")
    
    use_cover = st.checkbox("Титулка", value=True)
    school = st.text_input("Навчальний заклад (для титулки)")
    author = st.text_input("Автор (ПІБ, клас) (для титулки)")
    use_sources = st.checkbox("Список літератури", value=True)
    go = st.form_submit_button("Створити PDF")

if go and topic.strip():
    cover = ""
    if use_cover:
        title = topic.strip() if mode == "Реферат на тему" else "Словник англійських слів"
        kind = "РЕФЕРАТ" if mode == "Реферат на тему" else "Словник"
        cover = cover_html(title, kind, school, author)
    
    with st.spinner("Працюю..."):
        if mode == "Слова з англійської":
            body = ask(f"""Ось список англійських слів:{topic}Зроби HTML-таблицю (<table>) з колонками: Слово | Транскрипція | Переклад українською | Приклад речення.Без пояснень, лише HTML таблиці. Заголовок <h1>Словник</h1> перед таблицею.""")
            pdf = make_pdf(body, cover)
        else:
            src = search(topic)
            body = ask(f"""Напиши реферат мовою: {lang}. Тема: "{topic}". Обсяг приблизно {pages} сторінок А4.Використовуй ТІЛЬКИ факти з цих джерел, нічого не вигадуй. Якщо даних бракує, пиши загальніше.Джерела:{src}Структура: <h2>Зміст</h2> (список розділів), <h2>Вступ</h2>, 3-4 розділи <h2>, <h2>Висновки</h2>.{"В кінці <h2>Список літератури</h2> з <ol class='sources'> із наведених URL." if use_sources else ""}Формат: лише HTML (h2, p, ul, ol), без <html> і <body>, без пояснень.""")
            pdf = make_pdf(body, cover)
            
    st.success("Готово!")
    st.download_button("⬇️ Завантажити PDF", pdf, "document.pdf", "application/pdf")