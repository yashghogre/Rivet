<div align="center">
   <pre>
   ▄████████  ▄█   ▄█    █▄     ▄████████     ███    
  ███    ███ ███  ███    ███   ███    ███ ▀█████████▄
  ███    ███ ███▌ ███    ███   ███    █▀     ▀███▀▀██
 ▄███▄▄▄▄██▀ ███▌ ███    ███  ▄███▄▄▄         ███   ▀
▀▀███▀▀▀▀▀   ███▌ ███    ███ ▀▀███▀▀▀         ███    
▀███████████ ███  ███    ███   ███    █▄      ███    
  ███    ███ ███  ███    ███   ███    ███     ███    
  ███    ███ █▀    ▀██████▀    ██████████    ▄████▀  
  ███    ███                                         
  </pre>
  <p text-align="center">
Generate production-ready API clients from documentation in minutes, not days.
  </p>
</div>

---


## ⚡ What is Rivet?

Rivet is not just a code generator; it is an autonomous software engineer dedicated to building Python SDKs.

Unlike standard OpenAPI generators that produce rigid, un-pythonic code, Rivet uses a multi-stage Agentic Architecture to read your Swagger/OpenAPI documentation, slice the specification to your exact needs, and generate robust, Pydantic-validated SDKs.

**The Killer Feature:** Rivet verifies its own work. It spins up a Docker container, runs pytest against the generated code, and if the tests fail, it reads the error logs and fixes the code automatically.

### 🚀 Key Features

**🎯 Context Slicing:** Don't need the whole 5,000-endpoint API? Rivet intelligently slices the OpenAPI spec to generate only the micro-SDK you requested (e.g., "Just the Payment endpoints").

**🛡️ Type-Safety First:** Generates strictly typed Pydantic v2 models for all requests and responses.

**🔄 Self-Healing Loop:** Generated code is executed in a sandbox. If pytest fails, the "Auditor" agent analyzes the stack trace and refactors the code until it passes.

**📚 Documentation RAG:** Scrapes your HTML documentation to enrich the SDK with better docstrings and edge-case handling than the raw spec provides.

### 🏗️ Architecture

Puff operates in a three-stage pipeline to ensure quality and correctness.

```mermaid
graph TD
    %% Node Definitions
    Ingest[("Ingest Node<br/>(Fetch Spec & Docs)")]
    Slice[("Slice Node<br/>(Filter Spec)")]
    GenSDK[("Generate SDK<br/>(LLM: Create client.py)")]
    ValSDK[("Validate SDK<br/>(Syntax & Import Check)")]
    GenTests[("Generate Tests<br/>(LLM: Create test_client.py)")]
    RunTests[("Run Tests<br/>(Pytest execution)")]
    
    FixSDK[("Fix SDK Targeted<br/>(LLM: Surgical Fix)")]
    FixTests[("Fix Tests Targeted<br/>(LLM: Adjust Tests)")]
    
    %% End Node
    End((End/Success))
    Fail((End/Fail))

    %% Styles with Darker Backgrounds and Lighter Text
    style Ingest fill:#023e58,stroke:#01579b,stroke-width:2px,color:#ffffff
    style Slice fill:#023e58,stroke:#01579b,stroke-width:2px,color:#ffffff
    style GenSDK fill:#1b5e20,stroke:#2e7d32,stroke-width:2px,color:#ffffff
    style ValSDK fill:#f57f17,stroke:#fbc02d,stroke-width:2px,color:#ffffff
    style GenTests fill:#1b5e20,stroke:#2e7d32,stroke-width:2px,color:#ffffff
    style RunTests fill:#f57f17,stroke:#fbc02d,stroke-width:2px,color:#ffffff
    style FixSDK fill:#bf360c,stroke:#d84315,stroke-width:2px,stroke-dasharray: 5 5,color:#ffffff
    style FixTests fill:#bf360c,stroke:#d84315,stroke-width:2px,stroke-dasharray: 5 5,color:#ffffff
    style End fill:#2e7d32,stroke:#1b5e20,stroke-width:2px,color:#ffffff
    style Fail fill:#c62828,stroke:#b71c1c,stroke-width:2px,color:#ffffff

    %% Main Flow
    Ingest --> Slice
    Slice --> GenSDK
    GenSDK --> ValSDK

    %% Validation Routing (route_after_sdk_validation)
    ValSDK -- "Status: sdk_valid" --> GenTests
    ValSDK -- "Status: sdk_invalid (Retry < 3)" --> FixSDK
    ValSDK -- "Status: sdk_invalid (Retry >= 3)" --> Fail

    %% SDK Fix Loop (Validation Cycle)
    FixSDK --> ValSDK

    %% Test Flow
    GenTests --> RunTests

    %% Test Routing (route_after_test)
    RunTests -- "Status: success" --> End
    RunTests -- "Status: test_failed" --> Analyze{Error Analysis}
    
    %% Error Analysis Routing
    Analyze -- "Is SDK Error? (Retry < 5)" --> FixSDK
    Analyze -- "Is SDK Error? (Retry >= 5)" --> Fail
    Analyze -- "Is Test Error? (Retry < 5)" --> FixTests
    Analyze -- "Is Test Error? (Retry >= 5)" --> Fail

    %% Test Fix Loop (Execution Cycle)
    %% Note: Test fixes go straight back to execution, skipping SDK validation
    FixTests --> RunTests
```


#### 1. The Architect (Analysis)

Rivet pulls the full OpenAPI specification. If you asked for a specific feature set, the **Spec Slicer** traverses the reference graph to isolate only the relevant endpoints and their dependent data models, creating a "Mini-Spec."

#### 2. The Builder (Generation)

A **LangGraph Coding Agent**, equipped with the Mini-Spec and RAG context from your documentation, generates the Python SDK (client.py) and a matching Test Suite (test_client.py). It adheres to strict PEP 8 and Pydantic v2 standards.

#### 3. The Auditor (Verification)

This is where the magic happens.

1. The code is injected into an isolated **Docker Container.**

2. pytest is executed.

3. **If tests pass:** The SDK is packaged and delivered to you.

4. **If tests fail:** The **Error Analyzer** captures the `stderr` output, diagnoses the crash (e.g., `ImportError`, `ValidationError`), and feeds this feedback back to the Builder Agent to attempt a fix.

### 🛠️ Installation

You can install Rivet directly from PyPI or build it from source.

**Option 1: Standard Installation (Recommended)**

```bash
pip install rivet-ai
```

**Option 2: Development Installation If you want to contribute or modify the source code:**

```bash
git clone https://github.com/yashghogre/Rivet.git

cd Rivet

uv sync
```

### 💻 Usage

#### 1. Run the Generator

Point Rivet at any OpenAPI/Swagger URL to generate a client.

If installed via pip:

```bash
rivet https://petstore.swagger.io/v2/swagger.json
```

or simply,

```bash
rivet
```

If running from source:

```bash
uv run rivet https://petstore.swagger.io/v2/swagger.json
```


#### 2. Output

The final package will be available in the ./output directory:

```
output/
├── client.py            # The generated SDK
└── test_client.py       # The test suite used to verify the code
```
