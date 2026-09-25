import os
import time
import io
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from google import genai
from pypdf import PdfReader


# ============================================================
# LOAD ENVIRONMENT VARIABLES
# ============================================================

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    raise RuntimeError(
        "GEMINI_API_KEY is missing. "
        "Create a .env file inside the backend folder."
    )


# ============================================================
# GEMINI CONFIGURATION
# ============================================================

client = genai.Client(api_key=API_KEY)

MODEL = "gemini-3.6-flash"


# ============================================================
# FASTAPI APP
# ============================================================

app = FastAPI(
    title="SummarAI Backend",
    version="1.0.0",
)


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/api/health")
def health_check():
    return {
        "status": "ok",
        "message": "SummarAI backend is running",
    }


# ============================================================
# FILE TEXT EXTRACTION
# ============================================================

def extract_file_text(file_bytes: bytes, filename: str) -> str:
    filename_lower = filename.lower()

    # -------------------------
    # PDF
    # -------------------------

    if filename_lower.endswith(".pdf"):
        try:
            pdf_file = io.BytesIO(file_bytes)

            reader = PdfReader(pdf_file)

            pages = []

            for page in reader.pages:
                page_text = page.extract_text()

                if page_text:
                    pages.append(page_text)

            extracted_text = "\n\n".join(pages).strip()

            return extracted_text

        except Exception as error:
            raise HTTPException(
                status_code=400,
                detail=f"Could not read the PDF: {error}",
            )

    # -------------------------
    # TXT
    # -------------------------

    if filename_lower.endswith(".txt"):
        try:
            return file_bytes.decode(
                "utf-8",
                errors="ignore",
            ).strip()

        except Exception as error:
            raise HTTPException(
                status_code=400,
                detail=f"Could not read the TXT file: {error}",
            )

    # -------------------------
    # Unsupported file
    # -------------------------

    raise HTTPException(
        status_code=400,
        detail="Only PDF and TXT files are supported.",
    )


# ============================================================
# PROMPT CREATION
# ============================================================

def create_prompt(text: str, length: str) -> str:

    # --------------------------------------------------------
    # SHORT SUMMARY
    # --------------------------------------------------------

    if length == "short":

        instructions = """
Create a very short summary.

Requirements:

- Use only 2 to 3 sentences.
- State the central idea.
- Include only the most important information.
- Do not include unnecessary details.
- Keep the language simple and clear.
"""

    # --------------------------------------------------------
    # MEDIUM SUMMARY
    # --------------------------------------------------------

    elif length == "medium":

        instructions = """
Create a medium-length summary.

Requirements:

- Explain the main idea clearly.
- Include the most important supporting points.
- Include important facts, findings, or conclusions.
- Keep the language simple and easy to understand.
- Do not include unnecessary information.
- The summary should be balanced in length.
"""

    # --------------------------------------------------------
    # DETAILED SUMMARY
    # --------------------------------------------------------

    else:

        instructions = """
Create a detailed and comprehensive summary.

Requirements:

- Cover all major ideas in the source.
- Include important facts and supporting information.
- Include important causes and effects when present.
- Include important examples when present.
- Include important findings or conclusions.
- Use multiple paragraphs or bullet points when appropriate.
- Do not artificially limit the summary to five points.
- Include as many important points as are actually needed.
- Keep the language clear and easy to understand.
- Do not add information that is not present in the source.
"""

    return f"""
You are a professional AI text summarization assistant.

{instructions}

IMPORTANT:

- Only use information from the source.
- Do not invent facts.
- Do not change the meaning of the source.
- Do not discuss how you created the summary.
- Return only the final summary.

SOURCE CONTENT:

{text}
"""


# ============================================================
# SUMMARIZE API
# ============================================================

@app.post("/api/summarize")
async def summarize(
    text: str = Form(""),
    length: str = Form("medium"),
    file: Optional[UploadFile] = File(None),
):

    # --------------------------------------------------------
    # CHECK SUMMARY LENGTH
    # --------------------------------------------------------

    if length not in [
        "short",
        "medium",
        "detailed",
    ]:
        length = "medium"


    # --------------------------------------------------------
    # HANDLE FILE UPLOAD
    # --------------------------------------------------------

    if file is not None:

        file_bytes = await file.read()

        if not file_bytes:
            raise HTTPException(
                status_code=400,
                detail="The uploaded file is empty.",
            )

        extracted_text = extract_file_text(
            file_bytes,
            file.filename or "",
        )

        if extracted_text:
            text = extracted_text


    # --------------------------------------------------------
    # CLEAN TEXT
    # --------------------------------------------------------

    text = text.strip()


    # --------------------------------------------------------
    # CHECK EMPTY TEXT
    # --------------------------------------------------------

    if not text:

        raise HTTPException(
            status_code=400,
            detail="Please enter text or upload a PDF/TXT file.",
        )


    # --------------------------------------------------------
    # CHECK MINIMUM CONTENT
    # --------------------------------------------------------

    if len(text) < 40:

        raise HTTPException(
            status_code=400,
            detail="Please provide more content to summarize.",
        )


    # --------------------------------------------------------
    # LIMIT VERY LARGE INPUT
    # --------------------------------------------------------

    text = text[:100000]


    # --------------------------------------------------------
    # CREATE GEMINI PROMPT
    # --------------------------------------------------------

    prompt = create_prompt(
        text,
        length,
    )


    # ========================================================
    # GEMINI REQUEST WITH EXTENDED RETRY
    # ========================================================

    last_error = None

    MAX_ATTEMPTS = 5

    for attempt in range(MAX_ATTEMPTS):

        try:

            print(
                f"Gemini request attempt "
                f"{attempt + 1}/{MAX_ATTEMPTS}"
            )

            response = client.models.generate_content(
                model=MODEL,
                contents=prompt,
            )


            # ------------------------------------------------
            # GET SUMMARY
            # ------------------------------------------------

            summary = (response.text or "").strip()


            # ------------------------------------------------
            # EMPTY RESPONSE
            # ------------------------------------------------

            if not summary:

                raise Exception(
                    "Gemini returned an empty response."
                )


            # ------------------------------------------------
            # SUCCESS
            # ------------------------------------------------

            print("Gemini request successful.")

            return {
                "success": True,
                "summary": summary,
                "length": length,
                "model": MODEL,
            }


        except Exception as error:

            last_error = error

            error_text = str(error)

            print(
                f"Gemini error on attempt "
                f"{attempt + 1}: {error_text}"
            )


            # ------------------------------------------------
            # TEMPORARY ERROR CHECK
            # ------------------------------------------------

            is_temporary_error = (

                "503" in error_text

                or "UNAVAILABLE" in error_text

                or "429" in error_text

                or "RESOURCE_EXHAUSTED" in error_text
            )


            # ------------------------------------------------
            # RETRY
            # ------------------------------------------------

            if (
                is_temporary_error
                and attempt < MAX_ATTEMPTS - 1
            ):

                wait_seconds = 3 * (attempt + 1)

                print(
                    f"Gemini is temporarily unavailable. "
                    f"Waiting {wait_seconds} seconds "
                    f"before retry..."
                )

                time.sleep(wait_seconds)

                continue


            # ------------------------------------------------
            # STOP RETRYING
            # ------------------------------------------------

            break


    # ========================================================
    # FINAL ERROR
    # ========================================================

    raise HTTPException(
        status_code=502,
        detail=(
            "Gemini is temporarily unavailable after "
            "several attempts. Please wait a few seconds "
            "and try again."
        ),
    )