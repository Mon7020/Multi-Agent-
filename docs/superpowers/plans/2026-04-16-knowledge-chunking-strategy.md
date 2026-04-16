# Knowledge Chunking Strategy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add document-type-aware chunking for HTML/DOCX/outline-aware PDF/XLSX, expand upload support for those types, and rebuild the existing knowledge base with the new chunking rules.

**Architecture:** Keep `tools/rag_tool.py` as the single ingestion entry point, but split chunking into a light classifier plus three concrete paths: recursive text, structured document, and table document. Gate support consistently in backend APIs, admin upload UI, and frontend document preview helpers, then verify the rebuild path uses the new dispatcher end-to-end.

**Tech Stack:** FastAPI, Vue 3, ChromaDB, `langchain_text_splitters.RecursiveCharacterTextSplitter`, `pdfplumber`, `python-docx`, `beautifulsoup4`, `openpyxl`, `unittest`, Vitest

---

### Task 1: Expand Supported File Types Across API, Service, and UI

**Files:**
- Modify: `requirements.txt`
- Modify: `backend/requirements.txt`
- Modify: `backend/app/services/knowledge_admin_service.py`
- Modify: `backend/app/api/v1/knowledge_base.py`
- Modify: `frontend/src/admin/pages/KnowledgeAdminPage.vue`
- Modify: `frontend/src/admin/__tests__/knowledge-admin-page.test.js`
- Modify: `tests/admin/test_knowledge_admin_phase2_api.py`

- [ ] **Step 1: Write the failing backend and frontend support tests**

```python
# tests/admin/test_knowledge_admin_phase2_api.py
    def test_admin_can_upload_html_and_xlsx_documents(self):
        html_response = self.client.post(
            "/api/admin/knowledge/documents",
            headers=self.headers,
            files={"file": ("guide.html", b"<h1>Title</h1><p>Paragraph</p>", "text/html")},
            data={"allowed_roles": '["admin"]'},
        )
        self.assertEqual(html_response.status_code, 200)
        self.assertEqual(html_response.json()["file_type"], ".html")

        xlsx_response = self.client.post(
            "/api/admin/knowledge/documents",
            headers=self.headers,
            files={"file": ("table.xlsx", b"fake-xlsx-binary", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            data={"allowed_roles": '["admin"]'},
        )
        self.assertEqual(xlsx_response.status_code, 200)
        self.assertEqual(xlsx_response.json()["file_type"], ".xlsx")
```

```javascript
// frontend/src/admin/__tests__/knowledge-admin-page.test.js
  it('accepts html and xlsx files in the admin upload inputs', async () => {
    knowledgeAdminApi.listDocuments.mockResolvedValue({
      data: { documents: [makeDocument()], total: 1 }
    })

    const wrapper = mount(KnowledgeAdminPage)
    await flushPromises()

    expect(wrapper.findAll('input[type="file"]')[0].attributes('accept')).toBe('.txt,.pdf,.docx,.html,.htm,.xlsx')
    expect(wrapper.findAll('input[type="file"]')[1].attributes('accept')).toBe('.txt,.pdf,.docx,.html,.htm,.xlsx')
  })
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:

```powershell
D:\agentlearn\miniconda\envs\test3\python.exe -m unittest tests.admin.test_knowledge_admin_phase2_api -v
```

Expected: FAIL with `unsupported document type` or a 400 response for `.html/.xlsx`.

Run:

```powershell
npm run test:admin -- src/admin/__tests__/knowledge-admin-page.test.js
```

Expected: FAIL because the file input `accept` value still omits `.html,.htm,.xlsx`.

- [ ] **Step 3: Implement the extension gates and dependency declarations**

```python
# requirements.txt / backend/requirements.txt
beautifulsoup4==4.12.3
openpyxl==3.1.5
```

```python
# backend/app/services/knowledge_admin_service.py
ALLOWED_DOC_EXTENSIONS = {".txt", ".pdf", ".docx", ".html", ".htm", ".xlsx"}
```

```python
# backend/app/api/v1/knowledge_base.py
_ALLOWED_DOC_EXTENSIONS = {".txt", ".pdf", ".docx", ".html", ".htm", ".xlsx"}
```

```vue
<!-- frontend/src/admin/pages/KnowledgeAdminPage.vue -->
    <input
      ref="createInput"
      class="hidden-input"
      type="file"
      accept=".txt,.pdf,.docx,.html,.htm,.xlsx"
      @change="handleCreateFile"
    />
    <input
      ref="replaceInput"
      class="hidden-input"
      type="file"
      accept=".txt,.pdf,.docx,.html,.htm,.xlsx"
      @change="handleReplaceFile"
    />
```

```python
# tests/admin/test_knowledge_admin_phase2_api.py
    def load_document(self, source, chunk_size=400, chunk_overlap=50):
        del chunk_size, chunk_overlap
        suffix = Path(source).suffix.lower()
        if suffix == ".html":
            return [{"metadata": {"source_file": source}, "page_content": "html-chunk"}]
        if suffix == ".xlsx":
            return [
                {"metadata": {"source_file": source}, "page_content": "row-1"},
                {"metadata": {"source_file": source}, "page_content": "row-2"},
            ]
        line_count = max(1, len(Path(source).read_text(encoding="utf-8").splitlines()))
        return [{"metadata": {"source_file": source}, "page_content": f"chunk-{index}"} for index in range(line_count)]
```

- [ ] **Step 4: Run the tests to verify they pass**

Run:

```powershell
D:\agentlearn\miniconda\envs\test3\python.exe -m unittest tests.admin.test_knowledge_admin_phase2_api -v
```

Expected: PASS, including the new `.html/.xlsx` upload coverage.

Run:

```powershell
npm run test:admin -- src/admin/__tests__/knowledge-admin-page.test.js
```

Expected: PASS, including the new `accepts html and xlsx files` test.

- [ ] **Step 5: Commit**

```powershell
git add requirements.txt backend/requirements.txt backend/app/services/knowledge_admin_service.py backend/app/api/v1/knowledge_base.py frontend/src/admin/pages/KnowledgeAdminPage.vue frontend/src/admin/__tests__/knowledge-admin-page.test.js tests/admin/test_knowledge_admin_phase2_api.py
git commit -m "feat: add html and xlsx knowledge document support"
```

### Task 2: Add Document Strategy Detection and Dispatch in `RAGTool`

**Files:**
- Modify: `tools/rag_tool.py`
- Create: `tests/test_knowledge_chunking_strategies.py`

- [ ] **Step 1: Write the failing classification tests**

```python
# tests/test_knowledge_chunking_strategies.py
import unittest
from pathlib import Path
from unittest.mock import patch

from langchain_text_splitters import RecursiveCharacterTextSplitter

from tools.rag_tool import RAGTool


def build_subject():
    subject = RAGTool.__new__(RAGTool)
    subject.text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=400,
        chunk_overlap=50,
        separators=["\n\n", "\n", ". ", "? ", "! ", ", ", "; ", ": ", " ", ""],
    )
    subject.metrics = type("Metrics", (), {"record_documents_processed": lambda self, count: None})()
    return subject


class KnowledgeChunkingStrategyTest(unittest.TestCase):
    def test_detects_html_as_structured_document(self):
        subject = build_subject()
        self.assertEqual(subject._detect_document_strategy("guide.html"), "structured_document")

    def test_detects_docx_as_structured_document(self):
        subject = build_subject()
        self.assertEqual(subject._detect_document_strategy("guide.docx"), "structured_document")

    def test_detects_xlsx_as_table_document(self):
        subject = build_subject()
        self.assertEqual(subject._detect_document_strategy("price-table.xlsx"), "table_document")

    def test_detects_plain_text_as_recursive_text(self):
        subject = build_subject()
        self.assertEqual(subject._detect_document_strategy("notes.txt"), "recursive_text")

    def test_detects_outline_pdf_as_structured_document(self):
        subject = build_subject()
        with patch.object(subject, "_pdf_has_outline", return_value=True):
            self.assertEqual(subject._detect_document_strategy("manual.pdf"), "structured_document")
```

- [ ] **Step 2: Run the new strategy tests to verify they fail**

Run:

```powershell
D:\agentlearn\miniconda\envs\test3\python.exe -m unittest tests.test_knowledge_chunking_strategies -v
```

Expected: FAIL with `AttributeError` for `_detect_document_strategy` and `_pdf_has_outline`.

- [ ] **Step 3: Implement the classifier and dispatcher skeleton**

```python
# tools/rag_tool.py
from pathlib import Path

    def _detect_document_strategy(self, file_path: str) -> str:
        suffix = Path(file_path).suffix.lower()
        if suffix in {".html", ".htm", ".docx"}:
            return "structured_document"
        if suffix == ".xlsx":
            return "table_document"
        if suffix == ".pdf" and self._pdf_has_outline(file_path):
            return "structured_document"
        return "recursive_text"

    def _pdf_has_outline(self, file_path: str) -> bool:
        try:
            with pdfplumber.open(file_path) as pdf:
                doc = getattr(pdf, "doc", None)
                catalog = getattr(doc, "catalog", None)
                if not catalog:
                    return False
                return catalog.get("Outlines") is not None
        except Exception:
            return False

    def _build_recursive_splitter(
        self,
        chunk_size: int,
        chunk_overlap: int,
        content_type: str,
    ) -> RecursiveCharacterTextSplitter:
        separators = [
            "\n\n",
            "\n",
            "。",
            "！",
            "？",
            ". ",
            "? ",
            "! ",
            "，",
            "、",
            ", ",
            "; ",
            ": ",
            " ",
            "",
        ]
        if content_type == "price_list":
            separators = ["\n===== ", *separators]
        return RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=separators,
        )

    def _read_recursive_text(self, file_path: str) -> str:
        suffix = Path(file_path).suffix.lower()
        if suffix == ".pdf":
            with pdfplumber.open(file_path) as pdf:
                return "\n".join(page.extract_text() or "" for page in pdf.pages)
        if suffix == ".docx":
            document = docx.Document(file_path)
            return "\n".join(para.text for para in document.paragraphs if para.text.strip())
        if suffix == ".txt":
            return Path(file_path).read_text(encoding="utf-8")
        if suffix in {".html", ".htm"}:
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(Path(file_path).read_text(encoding="utf-8"), "html.parser")
            return soup.get_text("\n", strip=True)
        if suffix == ".xlsx":
            from openpyxl import load_workbook

            workbook = load_workbook(file_path, data_only=True)
            lines = []
            for sheet in workbook.worksheets:
                lines.append(f"[{sheet.title}]")
                for row in sheet.iter_rows(values_only=True):
                    values = ["" if cell is None else str(cell).strip() for cell in row]
                    if any(values):
                        lines.append(" | ".join(values))
            return "\n".join(lines)
        raise ValueError(f"unsupported file type: {file_path}")

    def _load_recursive_document(
        self,
        file_path: str,
        chunk_size: int,
        chunk_overlap: int,
        metadata: Dict[str, Any],
    ) -> List[Document]:
        content_type = metadata.get("content_type", "general")
        splitter = self._build_recursive_splitter(chunk_size, chunk_overlap, content_type)
        text = self._read_recursive_text(file_path)
        chunks = splitter.split_text(text)
        documents = [Document(page_content=chunk, metadata=metadata.copy()) for chunk in chunks if chunk.strip()]
        self.metrics.record_documents_processed(len(documents))
        return documents

    def _load_structured_document(
        self,
        file_path: str,
        chunk_size: int,
        chunk_overlap: int,
        metadata: Dict[str, Any],
    ) -> List[Document]:
        return self._load_recursive_document(file_path, chunk_size, chunk_overlap, metadata)

    def _load_table_document(self, file_path: str, metadata: Dict[str, Any]) -> List[Document]:
        return self._load_recursive_document(
            file_path,
            self.text_splitter._chunk_size,
            self.text_splitter._chunk_overlap,
            metadata,
        )

    def load_document(
        self,
        file_path: str,
        chunk_size: int = None,
        chunk_overlap: int = None,
        metadata: Optional[Dict[str, Any]] = None,
        content_type_hint: str = None,
    ) -> List[Document]:
        if not os.path.exists(file_path):
            raise ValueError(f"document does not exist: {file_path}")

        resolved_metadata = dict(metadata or {})
        resolved_metadata["file_path"] = file_path
        resolved_metadata["update_time"] = datetime.now().isoformat()
        resolved_metadata["content_type"] = content_type_hint or self._detect_content_type(file_path)

        if chunk_size is None:
            chunk_size = self.text_splitter._chunk_size
        if chunk_overlap is None:
            chunk_overlap = self.text_splitter._chunk_overlap

        strategy = self._detect_document_strategy(file_path)
        resolved_metadata["document_strategy"] = strategy

        if strategy == "structured_document":
            return self._load_structured_document(file_path, chunk_size, chunk_overlap, resolved_metadata)
        if strategy == "table_document":
            return self._load_table_document(file_path, resolved_metadata)
        return self._load_recursive_document(file_path, chunk_size, chunk_overlap, resolved_metadata)
```

- [ ] **Step 4: Run the strategy tests to verify they pass**

Run:

```powershell
D:\agentlearn\miniconda\envs\test3\python.exe -m unittest tests.test_knowledge_chunking_strategies -v
```

Expected: PASS for the strategy classification tests while structured and table loaders still delegate to the recursive path.

- [ ] **Step 5: Commit**

```powershell
git add tools/rag_tool.py tests/test_knowledge_chunking_strategies.py
git commit -m "feat: add knowledge document strategy detection"
```

### Task 3: Implement Structured Chunking for HTML and DOCX

**Files:**
- Modify: `tools/rag_tool.py`
- Modify: `tests/test_knowledge_chunking_strategies.py`

- [ ] **Step 1: Write the failing structured chunking tests**

```python
# tests/test_knowledge_chunking_strategies.py
    def test_html_chunking_preserves_heading_path_and_strips_noise(self):
        from tempfile import TemporaryDirectory

        subject = build_subject()
        with TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "guide.html"
            file_path.write_text(
                """
                <html><body>
                  <nav>ignore me</nav>
                  <h1>Overview</h1>
                  <p>System introduction.</p>
                  <h2>Install</h2>
                  <p>Step one.</p>
                  <script>console.log('ignore')</script>
                </body></html>
                """,
                encoding="utf-8",
            )
            docs = subject.load_document(str(file_path), chunk_size=120, chunk_overlap=20)

        self.assertTrue(any("Overview" in doc.page_content for doc in docs))
        self.assertTrue(any("Overview > Install" in doc.page_content for doc in docs))
        self.assertFalse(any("ignore me" in doc.page_content for doc in docs))
        self.assertFalse(any("console.log" in doc.page_content for doc in docs))

    def test_docx_chunking_preserves_heading_path(self):
        import docx
        from tempfile import TemporaryDirectory

        subject = build_subject()
        with TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "guide.docx"
            document = docx.Document()
            document.add_heading("Overview", level=1)
            document.add_paragraph("First paragraph.")
            document.add_heading("Install", level=2)
            document.add_paragraph("Second paragraph.")
            document.save(file_path)

            docs = subject.load_document(str(file_path), chunk_size=120, chunk_overlap=20)

        self.assertTrue(any("Overview" in doc.page_content for doc in docs))
        self.assertTrue(any("Overview > Install" in doc.page_content for doc in docs))
```

- [ ] **Step 2: Run the structured chunking tests to verify they fail**

Run:

```powershell
D:\agentlearn\miniconda\envs\test3\python.exe -m unittest tests.test_knowledge_chunking_strategies -v
```

Expected: FAIL because `load_document()` still falls back to plain extracted text and does not keep title paths.

- [ ] **Step 3: Implement HTML/DOCX structured loaders**

```python
# tools/rag_tool.py
from bs4 import BeautifulSoup

    def _load_structured_document(
        self,
        file_path: str,
        chunk_size: int,
        chunk_overlap: int,
        metadata: Dict[str, Any],
    ) -> List[Document]:
        suffix = Path(file_path).suffix.lower()
        if suffix in {".html", ".htm"}:
            blocks = self._extract_html_blocks(file_path)
        elif suffix == ".docx":
            blocks = self._extract_docx_blocks(file_path)
        elif suffix == ".pdf":
            blocks = self._extract_pdf_blocks(file_path)
        else:
            raise ValueError(f"unsupported structured document type: {file_path}")
        return self._chunk_structured_blocks(blocks, chunk_size, chunk_overlap, metadata)

    def _extract_html_blocks(self, file_path: str) -> List[Dict[str, str]]:
        soup = BeautifulSoup(Path(file_path).read_text(encoding="utf-8"), "html.parser")
        for tag_name in ("script", "style", "nav", "footer"):
            for node in soup.find_all(tag_name):
                node.decompose()

        heading_stack: List[str] = []
        blocks: List[Dict[str, str]] = []
        for node in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6", "p", "li"]):
            text = node.get_text(" ", strip=True)
            if not text:
                continue
            if node.name.startswith("h"):
                level = int(node.name[1])
                heading_stack = heading_stack[: level - 1]
                heading_stack.append(text)
                continue
            blocks.append({"heading_path": " > ".join(heading_stack), "body": text})
        return blocks

    def _extract_docx_blocks(self, file_path: str) -> List[Dict[str, str]]:
        document = docx.Document(file_path)
        heading_stack: List[str] = []
        blocks: List[Dict[str, str]] = []
        for para in document.paragraphs:
            text = para.text.strip()
            if not text:
                continue
            style_name = (para.style.name or "").lower()
            if style_name.startswith("heading"):
                raw_level = style_name.replace("heading", "").strip() or "1"
                level = int(raw_level)
                heading_stack = heading_stack[: level - 1]
                heading_stack.append(text)
                continue
            blocks.append({"heading_path": " > ".join(heading_stack), "body": text})
        return blocks

    def _chunk_structured_blocks(
        self,
        blocks: List[Dict[str, str]],
        chunk_size: int,
        chunk_overlap: int,
        metadata: Dict[str, Any],
    ) -> List[Document]:
        splitter = self._build_recursive_splitter(chunk_size, chunk_overlap, "general")
        documents: List[Document] = []
        for block in blocks:
            prefix = block["heading_path"].strip()
            content = f"{prefix}\n\n{block['body']}".strip() if prefix else block["body"]
            for chunk in splitter.split_text(content):
                if chunk.strip():
                    documents.append(Document(page_content=chunk, metadata=metadata.copy()))
        self.metrics.record_documents_processed(len(documents))
        return documents
```

- [ ] **Step 4: Run the structured chunking tests to verify they pass**

Run:

```powershell
D:\agentlearn\miniconda\envs\test3\python.exe -m unittest tests.test_knowledge_chunking_strategies -v
```

Expected: PASS for HTML and DOCX heading-path preservation.

- [ ] **Step 5: Commit**

```powershell
git add tools/rag_tool.py tests/test_knowledge_chunking_strategies.py
git commit -m "feat: add structured chunking for html and docx"
```

### Task 4: Implement Table Chunking for XLSX

**Files:**
- Modify: `tools/rag_tool.py`
- Modify: `tests/test_knowledge_chunking_strategies.py`

- [ ] **Step 1: Write the failing XLSX chunking tests**

```python
# tests/test_knowledge_chunking_strategies.py
    def test_xlsx_chunking_keeps_sheet_headers_and_row_ranges(self):
        from openpyxl import Workbook
        from tempfile import TemporaryDirectory

        subject = build_subject()
        with TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "prices.xlsx"
            workbook = Workbook()
            sheet = workbook.active
            sheet.title = "Prices"
            sheet.append(["Product", "Price"])
            sheet.append(["Alpha", 99])
            sheet.append(["Beta", 199])
            sheet.append(["Gamma", 299])
            workbook.save(file_path)

            docs = subject.load_document(str(file_path), chunk_size=400, chunk_overlap=50)

        self.assertTrue(any("Sheet: Prices" in doc.page_content for doc in docs))
        self.assertTrue(any("Headers: Product | Price" in doc.page_content for doc in docs))
        self.assertTrue(any("Rows 2-4" in doc.page_content for doc in docs))

    def test_xlsx_chunking_falls_back_to_generated_headers(self):
        from openpyxl import Workbook
        from tempfile import TemporaryDirectory

        subject = build_subject()
        with TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "blank-header.xlsx"
            workbook = Workbook()
            sheet = workbook.active
            sheet.title = "Sheet1"
            sheet.append([None, None])
            sheet.append(["Alpha", 99])
            workbook.save(file_path)

            docs = subject.load_document(str(file_path), chunk_size=400, chunk_overlap=50)

        self.assertTrue(any("Headers: Column 1 | Column 2" in doc.page_content for doc in docs))
```

- [ ] **Step 2: Run the XLSX tests to verify they fail**

Run:

```powershell
D:\agentlearn\miniconda\envs\test3\python.exe -m unittest tests.test_knowledge_chunking_strategies -v
```

Expected: FAIL because `.xlsx` is not yet parsed into header-aware row windows.

- [ ] **Step 3: Implement the XLSX table loader**

```python
# tools/rag_tool.py
from openpyxl import load_workbook

    def _load_table_document(self, file_path: str, metadata: Dict[str, Any]) -> List[Document]:
        workbook = load_workbook(file_path, data_only=True)
        documents: List[Document] = []
        row_window = 10

        for sheet in workbook.worksheets:
            rows = list(sheet.iter_rows(values_only=True))
            if not rows:
                continue

            raw_headers = list(rows[0])
            headers = [
                str(value).strip() if value not in (None, "") else f"Column {index + 1}"
                for index, value in enumerate(raw_headers)
            ]
            has_header = any(str(value).strip() for value in raw_headers if value is not None)
            body_rows = rows[1:] if has_header else rows

            for start in range(0, len(body_rows), row_window):
                window = body_rows[start:start + row_window]
                if not window:
                    continue

                row_lines = []
                for offset, row in enumerate(window, start=start + 2):
                    values = ["" if cell is None else str(cell).strip() for cell in row]
                    row_lines.append(f"{offset}: " + " | ".join(values))

                content = "\n".join(
                    [
                        f"Sheet: {sheet.title}",
                        f"Headers: {' | '.join(headers)}",
                        f"Rows {start + 2}-{start + 1 + len(window)}",
                        *row_lines,
                    ]
                )
                row_metadata = metadata.copy()
                row_metadata["sheet_name"] = sheet.title
                row_metadata["row_range"] = f"{start + 2}-{start + 1 + len(window)}"
                documents.append(Document(page_content=content, metadata=row_metadata))

        self.metrics.record_documents_processed(len(documents))
        return documents
```

- [ ] **Step 4: Run the XLSX tests to verify they pass**

Run:

```powershell
D:\agentlearn\miniconda\envs\test3\python.exe -m unittest tests.test_knowledge_chunking_strategies -v
```

Expected: PASS for XLSX row-window chunking and generated fallback headers.

- [ ] **Step 5: Commit**

```powershell
git add tools/rag_tool.py tests/test_knowledge_chunking_strategies.py requirements.txt backend/requirements.txt
git commit -m "feat: add xlsx table chunking"
```

### Task 5: Add Outline-Aware PDF Structured Chunking and Frontend Preview Support

**Files:**
- Modify: `tools/rag_tool.py`
- Modify: `backend/app/api/v1/knowledge_base.py`
- Modify: `tests/test_knowledge_chunking_strategies.py`

- [ ] **Step 1: Write the failing PDF and preview tests**

```python
# tests/test_knowledge_chunking_strategies.py
from app.api.v1.knowledge_base import _read_document_content

    def test_outline_pdf_uses_structured_pdf_blocks(self):
        from tempfile import TemporaryDirectory

        subject = build_subject()
        with TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "manual.pdf"
            file_path.write_bytes(b"%PDF-1.4 fake")

            fake_pdf = type(
                "FakePdf",
                (),
                {
                    "pages": [
                        type(
                            "FakePage",
                            (),
                            {"extract_text": lambda self: "Chapter 1 Overview\nSystem introduction\n1.1 Install\nStep one"},
                        )()
                    ],
                    "__enter__": lambda self: self,
                    "__exit__": lambda self, exc_type, exc, tb: False,
                    "doc": type("FakeDoc", (), {"catalog": {"Outlines": object()}})(),
                },
            )()

            with patch("tools.rag_tool.pdfplumber.open", return_value=fake_pdf):
                docs = subject.load_document(str(file_path), chunk_size=120, chunk_overlap=20)

        self.assertTrue(any("Chapter 1 Overview" in doc.page_content for doc in docs))
        self.assertTrue(any("1.1 Install" in doc.page_content for doc in docs))

    def test_read_document_content_supports_html_and_xlsx(self):
        from openpyxl import Workbook
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as temp_dir:
            html_path = Path(temp_dir) / "guide.html"
            html_path.write_text("<h1>Guide</h1><p>Step one</p>", encoding="utf-8")

            workbook = Workbook()
            sheet = workbook.active
            sheet.title = "Prices"
            sheet.append(["Product", "Price"])
            sheet.append(["Alpha", 99])
            xlsx_path = Path(temp_dir) / "prices.xlsx"
            workbook.save(xlsx_path)

            html_content = _read_document_content(html_path)
            xlsx_content = _read_document_content(xlsx_path)

        self.assertIn("Guide", html_content)
        self.assertIn("Step one", html_content)
        self.assertIn("[Prices]", xlsx_content)
        self.assertIn("Product | Price", xlsx_content)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:

```powershell
D:\agentlearn\miniconda\envs\test3\python.exe -m unittest tests.test_knowledge_chunking_strategies -v
```

Expected: FAIL because outline PDF still reads as flat text and `_read_document_content()` rejects `.html/.xlsx`.

- [ ] **Step 3: Implement outline-aware PDF extraction and content preview**

```python
# tools/rag_tool.py
import re

    PDF_HEADING_PATTERNS = [
        re.compile(r"^chapter\s+\d+\b.*$", re.IGNORECASE),
        re.compile(r"^section\s+\d+\b.*$", re.IGNORECASE),
        re.compile(r"^\d+(?:\.\d+)*\s+\S+"),
    ]

    def _pdf_heading_level(self, line: str) -> int:
        lowered = line.lower()
        if lowered.startswith("chapter ") or lowered.startswith("section "):
            return 1
        match = re.match(r"^(?P<number>\d+(?:\.\d+)*)\s+\S+", line)
        if match is None:
            return 1
        return match.group("number").count(".") + 1

    def _extract_pdf_blocks(self, file_path: str) -> List[Dict[str, str]]:
        blocks: List[Dict[str, str]] = []
        heading_stack: List[str] = []
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                for raw_line in (page.extract_text() or "").splitlines():
                    line = raw_line.strip()
                    if not line:
                        continue
                    if any(pattern.match(line) for pattern in self.PDF_HEADING_PATTERNS):
                        level = self._pdf_heading_level(line)
                        heading_stack = heading_stack[: level - 1]
                        heading_stack.append(line)
                        continue
                    blocks.append({"heading_path": " > ".join(heading_stack), "body": line})
        return blocks
```

```python
# backend/app/api/v1/knowledge_base.py
def _read_document_content(file_path: Path) -> str:
    suffix = file_path.suffix.lower()

    if suffix == ".txt":
        for encoding in ("utf-8", "utf-8-sig", "gb18030"):
            try:
                return file_path.read_text(encoding=encoding)
            except UnicodeDecodeError:
                continue
        raise HTTPException(status_code=500, detail="failed to decode text document")

    if suffix == ".pdf":
        import pdfplumber

        with pdfplumber.open(str(file_path)) as pdf:
            return "\n".join((page.extract_text() or "") for page in pdf.pages)

    if suffix == ".docx":
        import docx

        document = docx.Document(str(file_path))
        return "\n".join(para.text for para in document.paragraphs)

    if suffix in {".html", ".htm"}:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(file_path.read_text(encoding="utf-8"), "html.parser")
        return soup.get_text("\n", strip=True)

    if suffix == ".xlsx":
        from openpyxl import load_workbook

        workbook = load_workbook(file_path, data_only=True)
        lines = []
        for sheet in workbook.worksheets:
            lines.append(f"[{sheet.title}]")
            for row in sheet.iter_rows(values_only=True):
                values = ["" if cell is None else str(cell) for cell in row]
                if any(value.strip() for value in values):
                    lines.append(" | ".join(values))
        return "\n".join(lines)

    raise HTTPException(status_code=400, detail="unsupported document type")
```

- [ ] **Step 4: Run the tests to verify they pass**

Run:

```powershell
D:\agentlearn\miniconda\envs\test3\python.exe -m unittest tests.test_knowledge_chunking_strategies -v
```

Expected: PASS for outline-aware PDF structured chunking and preview helper coverage.

- [ ] **Step 5: Commit**

```powershell
git add tools/rag_tool.py backend/app/api/v1/knowledge_base.py tests/test_knowledge_chunking_strategies.py
git commit -m "feat: add structured pdf chunking and preview support"
```

### Task 6: Verify Full Knowledge Base Rebuild Uses the New Dispatcher

**Files:**
- Create: `tests/admin/test_knowledge_base_reload_api.py`
- Modify: `backend/app/api/v1/knowledge_base.py`
- Modify: `backend/app/services/knowledge_admin_service.py`

- [ ] **Step 1: Write the failing rebuild integration test**

```python
# tests/admin/test_knowledge_base_reload_api.py
import shutil
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.admin_main import app as admin_app
from app.services.auth_service import auth_service
from app.services.knowledge_admin_service import knowledge_admin_service


TEST_TMP_ROOT = Path(__file__).resolve().parents[2] / ".pytest_cache" / "knowledge-base-reload-api-tests"
TEST_TMP_ROOT.mkdir(parents=True, exist_ok=True)


class FakeReloadRagTool:
    def __init__(self):
        self._db_available = True
        self.collection = self
        self.sources = {}
        self.loaded_sources = []

    def clear_and_rebuild_collection(self):
        self.sources = {}
        self.loaded_sources = []
        return True

    def load_document(self, source, chunk_size=400, chunk_overlap=50):
        del chunk_size, chunk_overlap
        self.loaded_sources.append(Path(source).name)
        suffix = Path(source).suffix.lower()
        if suffix == ".html":
            return [{"metadata": {"source_file": source}, "page_content": "html-1"}]
        if suffix == ".xlsx":
            return [
                {"metadata": {"source_file": source}, "page_content": "xlsx-1"},
                {"metadata": {"source_file": source}, "page_content": "xlsx-2"},
            ]
        return [{"metadata": {"source_file": source}, "page_content": "txt-1"}]

    def add_documents_to_vector_db(self, documents):
        source = documents[0]["metadata"]["source_file"]
        self.sources[source] = len(documents)
        return [f"{source}:{index}" for index in range(len(documents))]

    def count(self):
        return sum(self.sources.values())


class KnowledgeBaseReloadApiTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = TEST_TMP_ROOT / uuid.uuid4().hex
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.docs_dir = self.temp_dir / "docs"
        self.docs_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_path = self.temp_dir / "knowledge-registry.json"
        self.audit_path = self.temp_dir / "admin-audit.jsonl"

        db_path = self.temp_dir / "auth.sqlite3"
        auth_service.reconfigure(database_url=f"sqlite:///{db_path.as_posix()}")
        knowledge_admin_service.reconfigure(
            docs_dir=str(self.docs_dir),
            metadata_path=str(self.metadata_path),
            audit_storage_path=str(self.audit_path),
        )

        self.client = TestClient(admin_app)
        self.admin = auth_service.register("knowledge.reload.admin", "password123")
        auth_service.update_user_role(self.admin["id"], "admin")
        token = auth_service.create_token(self.admin["id"], self.admin["username"])["token"]
        self.headers = {"Authorization": f"Bearer {token}"}

        self.rag_tool = FakeReloadRagTool()
        self.get_rag_tool_patcher = patch("app.api.v1.knowledge_base.get_rag_tool", return_value=self.rag_tool)
        self.get_rag_tool_patcher.start()

    def tearDown(self):
        self.get_rag_tool_patcher.stop()
        knowledge_admin_service.reconfigure()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_reload_rebuilds_all_supported_documents(self):
        (self.docs_dir / "alpha.txt").write_text("alpha", encoding="utf-8")
        (self.docs_dir / "guide.html").write_text("<h1>Guide</h1><p>Step</p>", encoding="utf-8")
        (self.docs_dir / "table.xlsx").write_bytes(b"xlsx")
        (self.docs_dir / "ignore.json").write_text("{}", encoding="utf-8")

        response = self.client.post("/api/v1/knowledge-base/reload", headers=self.headers)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["verified_chunks"], 4)
        self.assertEqual(sorted(self.rag_tool.loaded_sources), ["alpha.txt", "guide.html", "table.xlsx"])
```

- [ ] **Step 2: Run the reload integration test to verify it fails**

Run:

```powershell
D:\agentlearn\miniconda\envs\test3\python.exe -m unittest tests.admin.test_knowledge_base_reload_api -v
```

Expected: FAIL because the reload path still filters out `.html/.xlsx` or does not carry the new chunking behavior through.

- [ ] **Step 3: Wire the final rebuild path and extension consistency**

```python
# backend/app/api/v1/knowledge_base.py
        for file_path in sorted([p for p in docs_dir.iterdir() if p.is_file()], key=lambda p: p.name.lower()):
            if file_path.suffix.lower() not in _ALLOWED_DOC_EXTENSIONS:
                continue

            documents = rag_tool.load_document(
                str(file_path),
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
            )
            doc_ids = rag_tool.add_documents_to_vector_db(documents)
            total_chunks += len(doc_ids)
```

```python
# backend/app/services/knowledge_admin_service.py
ALLOWED_DOC_EXTENSIONS = {".txt", ".pdf", ".docx", ".html", ".htm", ".xlsx"}
```

- [ ] **Step 4: Run the full targeted verification suite**

Run:

```powershell
D:\agentlearn\miniconda\envs\test3\python.exe -m unittest tests.test_knowledge_chunking_strategies tests.admin.test_knowledge_admin_phase2_api tests.admin.test_knowledge_base_reload_api tests.admin.test_knowledge_admin_registry -v
```

Expected: PASS for the new classifier, chunker, preview, and rebuild coverage.

Run:

```powershell
npm run test:admin -- src/admin/__tests__/knowledge-admin-page.test.js
```

Expected: PASS.

Run:

```powershell
npm run build
```

Expected: PASS with a production build output in `frontend/dist`.

- [ ] **Step 5: Rebuild the real knowledge base and commit**

Run:

```powershell
$env:PYTHONPATH='D:\agentlearn\ai-engineer-training\projects\test2langchain;D:\agentlearn\ai-engineer-training\projects\test2langchain\backend'; @"
from app.api.v1.knowledge_base import get_docs_dir
from app.services.rag_runtime import get_rag_tool, rag_params_manager

rag_tool = get_rag_tool()
rag_tool.clear_and_rebuild_collection()
docs_dir = get_docs_dir()
total_chunks = 0

for file_path in sorted([p for p in docs_dir.iterdir() if p.is_file()], key=lambda p: p.name.lower()):
    if file_path.suffix.lower() not in {".txt", ".pdf", ".docx", ".html", ".htm", ".xlsx"}:
        continue
    docs = rag_tool.load_document(
        str(file_path),
        chunk_size=rag_params_manager.get_chunk_size(),
        chunk_overlap=rag_params_manager.get_chunk_overlap(),
    )
    total_chunks += len(rag_tool.add_documents_to_vector_db(docs))

print(total_chunks)
"@ | D:\agentlearn\miniconda\envs\test3\python.exe -
```

Expected: A positive integer total chunk count printed, with the current knowledge base fully rebuilt on the new strategy set.

Commit:

```powershell
git add requirements.txt backend/requirements.txt tools/rag_tool.py backend/app/api/v1/knowledge_base.py backend/app/services/knowledge_admin_service.py frontend/src/admin/pages/KnowledgeAdminPage.vue frontend/src/admin/__tests__/knowledge-admin-page.test.js tests/admin/test_knowledge_admin_phase2_api.py tests/admin/test_knowledge_base_reload_api.py tests/test_knowledge_chunking_strategies.py
git commit -m "feat: add document-aware knowledge chunking"
```


