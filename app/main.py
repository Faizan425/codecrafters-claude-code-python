import argparse
import os
import sys

from openai import OpenAI

# Global toggle: Set to 1 to use local Ollama, set to 0 before pushing to CodeCrafters
USE_LOCAL = 0

def main():
    # 1. Parse arguments FIRST, so args.p is ready for either API call
    p = argparse.ArgumentParser()
    p.add_argument("-p", required=True)
    args = p.parse_args()

    # 2. Setup the client and make the API call based on the global toggle
    if USE_LOCAL == 1:
        # --- LOCAL OLLAMA SETUP ---
        api_key = "ollama" 
        base_url = "http://localhost:11434/v1"
        client = OpenAI(api_key=api_key, base_url=base_url)
        
        chat = client.chat.completions.create(
            model="llama3.1", # Ensure you have run `ollama run llama3.1` in your terminal
            messages=[{"role": "user", "content": args.p}],
            tools= [{
                "type": "function",
                "function": {
                    "name": "Read",
                    "description": "Read and return the contents of a file",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "file_path": {
                                "type": "string",
                                "description": "The path to the file to read"
                                }
                            },
                        "required": ["file_path"]
                        }
                    }
                }
                    ]
        )
        print("Using Local Ollama Model...", file=sys.stderr)
        
    else:
        # --- CODECRAFTERS OPENROUTER SETUP ---
        api_key = os.getenv("OPENROUTER_API_KEY")
        base_url = os.getenv("OPENROUTER_BASE_URL", default="https://openrouter.ai/api/v1")
        
        if not api_key:
            raise RuntimeError("OPENROUTER_API_KEY is not set")
            
        client = OpenAI(api_key=api_key, base_url=base_url)
        
        chat = client.chat.completions.create(
            model="anthropic/claude-haiku-4.5",
            messages=[{"role": "user", "content": args.p}],
        )
        print("Using OpenRouter API...", file=sys.stderr)

    # 3. Handle the response
    if not chat.choices or len(chat.choices) == 0:
        raise RuntimeError("no choices in response")

    # Logs from your program will appear here! Visible when running tests.
    print("Logs from your program will appear here!", file=sys.stderr)

    # Uncommented to print the final output to standard out
    print(chat.choices[0].message.content)

if __name__ == "__main__":
    main()
