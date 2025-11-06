# 🤖 Agentic PDF-to-Excel Data Extractor (Groq Powered)

![Agentic PDF--to--Excel](https://img.shields.io/badge/Agentic%20PDF--to--Excel-Groq%20Powered-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-1.28.0-FF4B4B)
![LangGraph](https://img.shields.io/badge/LangGraph-Orchestration-orange)
![Groq](https://img.shields.io/badge/Groq-mixtral--8x7b--32768-green)

An autonomous AI **Agent Workflow** that extracts structured data from unstructured PDFs (invoices, reports, statements) and exports the results as a downloadable **XLSX (Excel)** file. Built with LangGraph for resilient orchestration and Groq for low-latency, high-accuracy structured extraction.

---

## 🚀 Key Technologies

| Technology | Role |
|------------|------|
| **LangGraph** | Agent orchestration (Load → Extract → Convert flow) |
| **Groq (ChatGroq)** | LLM core using `llama-3.3-70b-versatile` for fast, accurate extraction |
| **Pydantic** | Enforces JSON output schema to avoid post-processing/cleaning |
| **Streamlit** | Interactive web UI for uploads and downloads |
| **pypdf / PyPDF2** | PDF reading and text extraction |
| **Pandas / openpyxl** | Data handling and Excel (XLSX) export |

---

## 🌟 Features

- Autonomous multi-step agent flow (LangGraph) to process PDFs end-to-end  
- LLM-driven structured extraction using strict Pydantic schemas  
- Converts extracted JSON directly to a downloadable XLSX (Excel) file  
- Streamlit dashboard for upload, live extraction progress, and download  
- Configurable schemas for different document types (invoices, receipts, time-sheets)  
- Fast inference via Groq for real-time or near-real-time user experience

---

## ⚙️ Setup & Installation

### Prerequisites
- Python 3.8+
- Groq API key (create one in the Groq Developer Console)
- (Optional) virtual environment

### Install

```bash
git clone https://github.com/yourusername/agentic-pdf-to-excel.git
cd agentic-pdf-to-excel

python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Environment Variables

Create a `.env` file in the project root and add your Groq API key:

```env
GROQ_API_KEY="YOUR_GROQ_API_KEY"
```

This key is required to run the LLM extraction via Groq.

---

## ▶️ Running the Application

Start the Streamlit app:

```bash
streamlit run app.py
```

Steps in the UI:
1. Upload a PDF (invoice, report, bank statement)  
2. Click **Start Agent Workflow** to begin LangGraph extraction  
3. Preview extracted records in a table  
4. Click **Download Data as XLSX** to get your Excel file

---

## 🧭 How It Works (High Level)

1. **Load**: LangGraph agent reads PDF pages (pypdf) and prepares segments for extraction.  
2. **Extract**: Groq LLM (ChatGroq) receives the segment + Pydantic schema prompt and returns structured JSON.  
3. **Validate**: Pydantic validates/serializes the returned JSON; invalid items trigger controlled retries or fallback rules.  
4. **Convert**: Pandas converts valid JSON into a DataFrame and `to_excel()` outputs an XLSX file.  
5. **Deliver**: Streamlit provides the XLSX file as a downloadable asset to the user.

---

## 🛠️ Customizing the Agent & Schema

To adapt to other document types, edit the Pydantic models defined in `app.py` (or `schemas.py` if separated). Example Pydantic models:

```python
from pydantic import BaseModel
from typing import List, Optional

class InvoiceItem(BaseModel):
    description: str
    quantity: Optional[float]
    unit_price: Optional[float]
    total_price: float

class DocumentSummary(BaseModel):
    invoice_number: Optional[str]
    date: Optional[str]
    vendor: Optional[str]
    vendor_tax_id: Optional[str]
    subtotal: Optional[float]
    tax: Optional[float]
    total: float
    items: List[InvoiceItem]
```

Update fields (add `client_tin`, change `quantity` → `hours_billed`, etc.) and the extraction prompt will instruct the LLM to output the adapted JSON schema directly.

---

## ⚠️ Reliability & Validation Strategies

- **Strict schemas (Pydantic)** ensure results meet your contract; invalid outputs can be retried with revised prompts or flagged for human review.  
- **Chunking** large PDFs into smaller, logical sections reduces hallucinations and preserves extraction quality.  
- **Confidence & Heuristics**: Attach simple heuristic checks (e.g., `total ≈ sum(items)`) and numeric thresholds; expose risk scores in the UI.  
- **Retries & Fallbacks**: On schema validation failure, re-run with increased context or use simpler extraction prompts.

---

## 🧪 Example Workflow (Invoice)

1. Upload `invoice_123.pdf`  
2. Agent loads pages and extracts candidate fields using Groq  
3. Pydantic validates the JSON and returns `DocumentSummary` + `InvoiceItem[]`  
4. The UI displays the table and a **Download XLSX** button

Sample extracted JSON (conceptual):

```json
{
  "invoice_number": "INV-123",
  "date": "2025-10-29",
  "vendor": "Acme Supplies",
  "subtotal": 1023.50,
  "tax": 92.12,
  "total": 1115.62,
  "items": [
    {"description": "Widget A", "quantity": 10, "unit_price": 50.0, "total_price": 500.0},
    {"description": "Widget B", "quantity": 5, "unit_price": 100.7, "total_price": 503.5}
  ]
}
```

---

## 📁 Project Structure (suggested)

```
agentic-pdf-to-excel/
├── app.py
├── requirements.txt
├── .env
└── README.md
```

---

## 🧰 Troubleshooting

- **No API Key / Auth Error**: `Error: GROQ_API_KEY missing or invalid` → verify `.env` and restart the app.  
- **Poor Extraction Results**: Try increasing context, improving prompts, or refining the Pydantic schema to better match expected fields.  
- **Validation Failures**: Check the LLM output vs. schema; expand `Optional[]` where legitimate empties occur.  
- **Large PDFs Timeout**: Chunk pages and process incrementally; show partial results in UI.

---

## ♻️ Future Enhancements

- Native integrations with cloud storage (S3, GCS) for automated ingestion  
- Human-in-the-loop review UI for flagged records  
- Multi-language extraction & OCR integration for scanned PDFs (Tesseract or commercial OCR)  
- Export templates (custom Excel sheets, multiple sheets per document)  
- Audit logs & versioning for regulatory compliance

---

## 🤝 Contributing

Contributions are welcome — please open issues and pull requests for bugs, feature requests, and documentation improvements.

---


## 🙏 Acknowledgments

- Groq for high-speed LLM inference  
- LangGraph for robust agent orchestration  
- Streamlit for fast app prototyping  
- Pydantic / Pandas / openpyxl for data validation & export

---

<div align="center">
Made with ❤️ — Agentic PDF extraction simplified with Groq & LangGraph
</div>
