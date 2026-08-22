# NDEF Virtual NFC Production Guide

## 1. Architectural Overview
This document outlines the production architecture for the NDEF Virtual Hardware Bridge within Track 4 of the QThorium Mesh. To ensure maximum reliability during high-stakes demonstrations and to bypass browser-level HTTPS/Mobile restrictions, the NFC interface is implemented as a software-simulated hardware bridge. It visually and functionally replicates an ISO/IEC 14443 Type A contactless subsystem.

## 2. Component Design: The NDEF Bridge Interface
The interface is built as an isolated React component integrated into the main task submission dashboard. It maintains a clean, minimalist design utilizing a dark neutral background, precise visual hierarchy, and modern typography.

* **State Management**: The component strictly tracks three hardware states: `Idle`, `Scanning` (simulating a 650ms cryptographic handshake), and `Active Session` (lease established).
* **Card Selector Grid**: A visual layout representing different physical cards (e.g., Enterprise Admin, Standard DevOps, Demo Judge).
* **Induction Zone**: A central tap target that provides immediate visual feedback (color changes and status text updates) to indicate the success or failure of the hardware handshake.

## 3. The NDEF Payload Structure
When a virtual card is engaged, it injects a highly structured data payload into the application state. This payload acts as the immutable truth for the duration of the session so that both frontend and backend developers share a strict type contract.

The payload consists of:
* **User NFC Token**: A unique alphanumeric string identifying the physical card.
* **Project ID**: The exact namespace used by Track 2 to partition the ChromaDB vector search.
* **Security Tier**: The authorization level (e.g., `PRIORITY_ROOT`, `STANDARD`) dictating which worker nodes are permitted to process the task.
* **Compute Credits**: A predefined integer representing remaining inference operations available to the cardholder.

### NDEF JSON Schema Contract
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "user_nfc_token": { "type": "string" },
    "project_id": { "type": "string" },
    "tier": { "type": "string" },
    "userName": { "type": "string" },
    "remainingCredits": { "type": "number" }
  },
  "required": ["user_nfc_token", "project_id", "tier", "userName", "remainingCredits"]
}
```

### Example Output Payload
```json
{
  "user_nfc_token": "CARD-DEMO-JUDGE-001",
  "project_id": "engineering_docs",
  "tier": "PRIORITY_ROOT",
  "userName": "Hackathon Evaluation Lead",
  "remainingCredits": 9999
}
```

## 4. Orchestrator Integration (Track 2 Validation)
The Virtual NFC interface acts as the gatekeeper for Track 2 (the Orchestrator).
* **Prompt Locking**: The text input for the AI prompt remains completely disabled until the NDEF Bridge registers an Active Session.
* **Payload Injection**: Upon prompt submission, the interface seamlessly binds the User NFC Token, Project ID, and Node Requirements to the outbound HTTP request.
* **Backend Verification**: Track 2 receives this payload, verifies the token against the active registry, filters the LangChain retrieval pipeline using the Project ID, and dispatches the task to Track 3.

## 5. Failsafes and Demo Reliability
To guarantee a flawless presentation, the NDEF Bridge includes a hidden developer override. This ensures that even if the primary UI interactions fail or the presentation flow is interrupted, the end-to-end distributed network and real-time streaming capabilities can still be demonstrated to the judges without hesitation.

### Developer Override Binding
Pressing `Ctrl + Shift + N` while the dashboard window is in focus will instantly bypass the visual tap target, simulate a successful 650ms NDEF read, and inject the `CARD-DEMO-JUDGE-001` root payload into the active session state. This allows the presenter to immediately submit an authenticated prompt to the mesh.
