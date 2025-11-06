import os
import streamlit as st
import pandas as pd
import json
from typing import List, TypedDict, Optional
import io

from dotenv import load_dotenv
load_dotenv()
from pydantic import BaseModel, Field

# Import LangGraph and related components
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, SystemMessage
from langchain.output_parsers import PydanticOutputParser

from langchain_groq import ChatGroq

from pypdf import PdfReader

# Pydantic (Agent Goal Structure)

class InvoiceItem(BaseModel):
    """A line item representing a product or service purchased."""
    description: str = Field(description="The description of the product or service.")
    quantity: int = Field(description="The number of units purchased, must be an integer.")
    unit_price: Optional[float] = Field(default=0.0, description="The price per unit, must be a float. Defaults to 0.0 if not found.")
    total_amount: float = Field(description="The total amount for this item (quantity * unit_price), must be a float.")

class DocumentSummary(BaseModel):
    """The complete structured data extracted from a single PDF invoice."""
    invoice_id: str = Field(description="The unique invoice identification number.")
    date_issued: str = Field(description="The date the invoice was issued (YYYY-MM-DD format).")
    vendor_name: str = Field(description="The name of the company or vendor who issued the invoice.")
    customer_name: str = Field(description="The name of the customer receiving the invoice.")
    total_invoice_due: float = Field(description="The grand total amount due for the entire invoice, must be a float.")
    items: List[InvoiceItem] = Field(description="A list of all individual purchased items on the invoice.")

class AgentState(TypedDict):
    """
    Represents the state of our multi-step agent workflow.
    """
    uploaded_file_object: Optional[st.runtime.uploaded_file_manager.UploadedFile]
    pdf_text: str  # Text extracted from the PDF
    structured_data: dict  # JSON data extracted by the LLM
    error_message: str  # Any errors encountered


# Nodes (Tools and Actions)

def extract_text_from_pdf(state: AgentState):
    """
    Simulates the Document Loader tool: Extracts text from the uploaded PDF.
    """
    # CRITICAL CHANGE: Access file object directly from the state
    uploaded_file = state.get('uploaded_file_object')
    if uploaded_file is None:
        return {"error_message": "No PDF file object found in state. Workflow cannot proceed."}

    try:
        uploaded_file.seek(0)
        reader = PdfReader(uploaded_file)
        text = ""
        for page in reader.pages:
            text += page.extract_text()

        st.info(f"PDF Loaded: Extracted {len(text)} characters of text from '{uploaded_file.name}'.")
        return {"pdf_text": text}

    except Exception as e:
        return {"error_message": f"Error loading PDF: {e}"}


def run_extraction_agent(state: AgentState):
    """
    The 'AI Analyst' Node: Uses the Groq LLM to convert raw text to structured JSON.
    """
    pdf_text = state.get("pdf_text")
    if not pdf_text:
        return {"error_message": "Cannot run extraction. No PDF text found."}

    st.info("Agent is analyzing text and structuring data (calling Groq LLM)...")

    # LLM Initialization

    groq_api_key = os.getenv("GROQ_API_KEY")
    if not groq_api_key:
        return {"error_message": "GROQ_API_KEY not found. Please check your .env file or environment variables."}

    llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0.2, groq_api_key=groq_api_key)

    parser = PydanticOutputParser(pydantic_object=DocumentSummary)

    system_instruction = SystemMessage(
        content="You are an expert Data Analyst specializing in extracting financial data from unstructured invoice documents. Your single task is to produce a JSON object that strictly adheres to the provided schema, based on the document text below. Do not output anything other than the JSON object."
    )

    prompt_template = f"""
    PARSE THIS DOCUMENT TEXT:
    {parser.get_format_instructions()}

    DOCUMENT TEXT TO ANALYZE:
    {pdf_text}

    CRITICAL RULE: Return ONLY the JSON object.
    """

    # Initialize response to prevent UnboundLocalError if llm.invoke fails immediately
    response = ""

    try:
        # Pass both system instruction and user prompt to the model
        response = llm.invoke([system_instruction, HumanMessage(content=prompt_template)]).content

        # Validate and parse the response against the Pydantic schema
        # We need to handle cases where Groq might wrap the JSON in markdown fences
        try:
            if response.startswith("```json"):
                response = response.strip().strip("```json").strip("```")
            elif response.startswith("```"):
                response = response.strip().strip("```")

            # Use model_validate_json for robust parsing
            structured_data = DocumentSummary.model_validate_json(response)
        except Exception as validation_e:
            # If the direct JSON validation fails, try to parse it as plain text first
            structured_data = parser.parse(response)


        st.success("Extraction successful and data validated against schema.")
        return {"structured_data": structured_data.model_dump()}

    except Exception as e:
        error_msg = f"LLM Extraction Failed: Could not parse response into structured data. Error: {e}"
        # Print the raw LLM response to the console for easier debugging
        print(f"--- LLM RAW RESPONSE FOR DEBUGGING ---\n{response}\n--------------------------------------")
        st.error(f"LLM Extraction Failed. Check console for raw response. Error: {e}")
        return {"error_message": error_msg}


def convert_and_display(state: AgentState):
    """
    The 'Excel Writer' Node: Converts the structured JSON to a Pandas DataFrame
    and prepares it for display/download as XLSX.
    """
    data = state.get("structured_data")
    if not data:
        return {"error_message": "Cannot convert to Excel. No structured data found."}

    st.info("Converting structured JSON data into Excel-ready format...")

    try:
        # Pydantic validation ensures the structure is correct
        structured_data = DocumentSummary(**data)
        data_list = []

        # Flatten the structured data
        for item in structured_data.items:
            # Safely extract item data
            item_data = item.model_dump()
            row = {
                'Invoice_ID': structured_data.invoice_id,
                'Date_Issued': structured_data.date_issued,
                'Vendor': structured_data.vendor_name,
                'Customer': structured_data.customer_name,
                'Line_Item_Description': item_data.get('description', 'N/A'),
                'Quantity': item_data.get('quantity', 0),
                'Unit_Price': item_data.get('unit_price', 0.0),
                'Line_Total': item_data.get('total_amount', 0.0),
                'Invoice_Total_Due': structured_data.total_invoice_due
            }
            data_list.append(row)

        if not data_list:
            st.warning("The LLM extracted the main document headers but did not find any line items (empty 'items' list). Please refine the prompt for this PDF type.")
            return {"error_message": "No line items extracted. Empty Excel file would be generated."}


        df = pd.DataFrame(data_list)

        st.subheader("✅ Final Extracted Data (Excel Preview)")
        st.dataframe(df, use_container_width=True)

        excel_buffer = io.BytesIO()
        df.to_excel(excel_buffer, index=False, sheet_name='Extracted Data')
        excel_buffer.seek(0)

        # Create a download button for the XLSX file
        st.download_button(
            label="Download Data as XLSX (Excel File)",
            data=excel_buffer,
            file_name=f"{structured_data.invoice_id}_extracted_data.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

        return {}

    except Exception as e:
        return {"error_message": f"Excel Conversion Failed: {e}"}


# LangGraph Setup

def create_workflow():
    """Defines the sequential flow of the Agent."""
    workflow = StateGraph(AgentState)

    # Add the nodes
    workflow.add_node("load_pdf", extract_text_from_pdf)
    workflow.add_node("extract_data", run_extraction_agent)
    workflow.add_node("convert_and_display", convert_and_display)

    # Set up the edges (the sequence)
    workflow.set_entry_point("load_pdf")

    workflow.add_edge("load_pdf", "extract_data") # after loading PDF, extract data
    workflow.add_edge("extract_data", "convert_and_display") # After extraction move to conversion/display
    workflow.add_edge("convert_and_display", END) # End the process

    return workflow.compile()


# Streamlit UI

def main():
    """The main Streamlit application function."""
    st.set_page_config(page_title="Agentic PDF to Excel Automation", layout="centered")

    st.title("📄 Agentic PDF to Structured Data Analyzer")
    st.markdown("""
        Use this tool to upload an unstructured PDF (like an invoice or report).
        The AI agent orchestrator (LangGraph) will automatically:
        1. Extract the text (Loader Tool).
        2. Analyze and convert the text into structured JSON (AI Analyst Node).
        3. Flatten the JSON into an Excel-ready table (Writer Tool).
    """)

    # File Uploader
    uploaded_file = st.file_uploader(
        "Upload a PDF Document (e.g., Invoice, Financial Report)",
        type="pdf"
    )

    if 'workflow_runner' not in st.session_state:
        st.session_state['workflow_runner'] = create_workflow()

    # The button logic now explicitly checks for a file and passes it to the initial state
    if uploaded_file and st.button("Start Agent Workflow", use_container_width=True, type="primary"):
        with st.spinner("Agent workflow initiated. Analyzing document..."):

            # The LangGraph process starts here
            app = st.session_state['workflow_runner']

            initial_state = AgentState(
                uploaded_file_object=uploaded_file,
                pdf_text="",
                structured_data={},
                error_message=""
            )

            # Stream the execution steps for real-time feedback
            current_state = {} # Initialize current_state for the final check
            for step in app.stream(initial_state):
                
                # Check if the step is the END node (which might return an empty dict or special state)
                if not step:
                    continue # Skip empty steps

                # Get the node name and the state update from the step dictionary
                node_name, state_update = list(step.items())[0]

                # CRITICAL FIX: Ensure state_update is a dictionary before updating.
                # When LangGraph hits the END node, 'step' can contain an update that is not iterable
                # or is None if filtered out by the check above.
                if isinstance(state_update, dict):
                    current_state.update(state_update)
                # Else, if it's the END node, the update might be the final state, which is fine to skip updating 'current_state' with.

                # Check for errors at any step
                error = current_state.get('error_message')
                if error:
                    st.error(f"Workflow Stopped: {error}")
                    # Also show the current state to the user for debugging
                    st.json(current_state)
                    break

                # Display progress (optional, but good for user feedback)
                if node_name not in [END]:
                    st.toast(f"✅ Executed step: {node_name}")

            # Final check to make sure the last step (display) was executed
            if not current_state.get('error_message') and current_state.get('structured_data'):
                 st.toast("🔥 Workflow Complete!")


if __name__ == "__main__":
    main()