import time
import random

class MockGraph:
    """
    A fake LangGraph that just yields events to test the UI.
    """
    def stream(self, initial_state: dict):
        """
        Simulates the AI thinking process with delays.
        """
        url = initial_state.get("url", "https://api.example.com")
        
        # --- Step 1: Ingest (The Crawler) ---
        # Simulates fetching the docs
        time.sleep(1.0)
        yield {
            "node_ingest": {
                "url": url,
                "status": "fetching_spec"
            }
        }
        time.sleep(1.5) # Fake network delay

        # --- Step 2: Code Gen (The Writer) ---
        # Simulates the AI typing out code (streaming effect)
        boilerplate = [
            "import requests",
            "from pydantic import BaseModel",
            "\nclass User(BaseModel):\n    id: int\n    name: str",
            "\nclass APIClient:\n    def __init__(self, base_url: str):",
            "        self.base_url = base_url",
            "    def get_user(self, uid: int):",
            "        return requests.get(f'{self.base_url}/users/{uid}')"
        ]
        
        current_code = ""
        for line in boilerplate:
            current_code += line + "\n"
            time.sleep(0.3) # Simulate typing speed
            yield {
                "node_codegen": {
                    "partial_code": current_code
                }
            }

        # --- Step 3: Testing (The Sandbox) ---
        # Simulates running pytest in Docker
        time.sleep(0.5)
        yield {"node_test": {"status": "running"}} 
        time.sleep(2.0) # Fake test duration

        # --- Step 4: Failure (The Self-Healing) ---
        # Simulates a crash to show off your error handling UI
        yield {
            "node_fix": {
                "error": "ImportError: module 'requests' not found",
                "attempt": 1
            }
        }
        time.sleep(1.5) # Fake "thinking about the fix" time

        # --- Step 5: Success (The Fix) ---
        # Simulates the fixed code
        current_code = "# FIXED: Added imports\n" + current_code
        yield {
            "node_codegen": {
                "partial_code": current_code
            }
        }
        time.sleep(1.0)
        
        # Final success state (optional, usually handled by completion)
        yield {"node_success": {"path": "./output/sdk"}}

def build_graph():
    """
    Returns the mock graph instead of the real LangGraph.
    """
    return MockGraph()
