# Sunbeam SmartBot

Sunbeam SmartBot is a retrieval-augmented generation (RAG) chatbot for answering questions about Sunbeam's institute, internship programs, batch schedules, and modular courses.

The project scrapes Sunbeam website information with Selenium, converts it into text documents, creates local vector embeddings with Chroma, and sends relevant context to a Groq-hosted Llama model.

## Features

- Selenium web scrapers for the Sunbeam About and Internship pages
- A standalone modular-course scraper
- Text-based source data stored in `text_data/`
- Chunked documents with Hugging Face embeddings
- A local Chroma vector database
- Retrieval using Maximal Marginal Relevance (MMR)
- Grounded, context-only answers through Groq
- Interactive command-line chat

## Project Structure

```text
Sunbeam_SmartBot/
|-- app.py                         # Scrapes data and rebuilds the Chroma database
|-- rag_chatbot.py                 # Loads Chroma and runs the interactive chatbot
|-- scraper_util.py                # Selenium manager for about/internship scraping
|-- scrapers/
|   |-- sunbeam_about.py           # About-page scraper
|   |-- sunbeam_internship.py      # Internship and batch-schedule scraper
|   `-- sunbeam_courses.py         # Standalone modular-courses scraper
|-- loaders/
|   `-- sunbeam_txt_loader.py      # Custom LangChain text loader
|-- text_data/
|   |-- sunbeam_about.txt
|   |-- sunbeam_internship.txt
|   `-- sunbeam_courses.txt
|-- chroma_db/                     # Persisted local vector database
|-- .env                           # Groq credentials (create locally)
`-- .gitignore
```

## How It Works

1. Selenium scrapes the About and Internship pages into text files.
2. `app.py` loads the text files, removes the existing Chroma database, splits the text into chunks, and creates embeddings with `sentence-transformers/all-MiniLM-L6-v2`.
3. Chroma stores the chunks in `chroma_db/`.
4. `rag_chatbot.py` searches the vector database with MMR and sends the retrieved context to `llama-3.3-70b-versatile` through Groq.
5. The chatbot answers only from retrieved information and reports when an answer is outside the available context.

## Requirements

- Python 3.10 or newer
- Google Chrome
- Internet access
- A Groq API key

The project does not currently include a `requirements.txt`. Install the Python packages used by the source:

```bash
python -m venv venv
venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install selenium python-dotenv langchain-chroma langchain-huggingface langchain-text-splitters langchain-community langchain-core langchain-groq sentence-transformers webdriver-manager
```

ChromeDriver is managed automatically by Selenium in the main scraper. The standalone course scraper also uses `webdriver-manager`.

## Configuration

Create a `.env` file in the project directory:

```dotenv
GROQ_API_KEY=your_groq_api_key
```

The `.env` file is excluded by `.gitignore`. Never commit API keys or credentials.

## Usage

Run commands from the `Sunbeam_SmartBot` directory.

### 1. Build or rebuild the vector database

```bash
python app.py
```

This starts headless Chrome, scrapes:

- `https://www.sunbeaminfo.in/about-us`
- `https://www.sunbeaminfo.in/internship`

It then writes:

- `text_data/sunbeam_about.txt`
- `text_data/sunbeam_internship.txt`

and recreates `chroma_db/`.

> `app.py` replaces the existing Chroma database on every run. `text_data/sunbeam_courses.txt` is loaded into the vector database because it is part of `TEXT_FILES`, but the modular-course scraper is not called by `app.py`.

### 2. Start the chatbot

```bash
python rag_chatbot.py
```

Example questions:

```text
What internship batches are currently available?
What courses does Sunbeam offer?
What is the duration of the Java course?
Where are the Sunbeam campuses located?
```

Type `exit` to end the chat.

### 3. Run the modular-course scraper

The modular-course scraper is currently a standalone function. From Python:

```bash
python -c "from scrapers.sunbeam_courses import run_modular_courses_scraper; run_modular_courses_scraper()"
```

This prints modular-course information collected from `https://sunbeaminfo.in/modular-courses-home`; it does not automatically write to `text_data/sunbeam_courses.txt`.

## Retrieval Configuration

The chatbot is configured with:

| Setting | Value |
|---|---|
| Embedding model | `sentence-transformers/all-MiniLM-L6-v2` |
| LLM | `llama-3.3-70b-versatile` |
| Temperature | `0.1` |
| Search mode | MMR |
| Retrieved documents | 15 |
| MMR candidate pool | 40 |
| Chunk size | 1,200 characters |
| Chunk overlap | 150 characters |

## Important Notes

- The scraped and indexed content depends on the current website structure and availability.
- Website layout changes can break Selenium selectors.
- The source text should be reviewed periodically because course fees, schedules, and availability may change.
- Without a valid Groq API key, `rag_chatbot.py` cannot generate answers.
- Chatbot responses are intentionally restricted to the retrieved Sunbeam source context.

## Troubleshooting

### `GROQ_API_KEY` is missing

Confirm that `.env` is in the project directory and contains a valid `GROQ_API_KEY`.

### Chrome or ChromeDriver fails to start

- Install or update Google Chrome.
- Close old Chrome processes.
- Ensure Selenium can access Chrome from the terminal.

### Chroma database has stale answers

Run `python app.py` again to delete and rebuild `chroma_db/`.

### Scraper cannot find page elements

The website may have changed. Check the CSS selectors and XPath expressions in `scrapers/` and update them to match the current page markup.
