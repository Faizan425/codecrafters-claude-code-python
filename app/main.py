import argparse
import os
import sys
import json
import subprocess

from openai import OpenAI

# Global toggle: Set to 1 to use local Ollama, set to 0 before pushing to CodeCrafters
USE_LOCAL = 0

def read_tool(file_path):
    try:
        with open(file_path, "r") as file:
            content = file.read()
            return content
    except FileNotFoundError:
        return "read mode (r) does not create files , file does not exist."

def write_tool(file_path, content):
    folder_path = os.path.dirname(file_path)
    if(folder_path):
        os.makedirs(folder_path, exist_ok = True)
    with open(file_path, "w") as file:
        file.write(content)
        return "File written successfully"

def bash_tool(command):
    arguments = command.split()
    try:
        result  = subprocess.run(arguments, capture_output = True, text = True, check = True)
        return (f"Success: result:{result.stdout}")
    except subprocess.CalledProcessError as e:
        return (f"Command failed: error encountered: {e.stderr}") 

def agent_loop(model, messages, tools,client):
    while(True):
        chat = client.chat.completions.create(model=model , messages=messages, tools=tools)
        #print("Using open router", file = sys.stderr)
        if not chat.choices or len(chat.choices) == 0:
            raise RuntimeError("no choices in response")
        chat = chat.choices[0]
        messages.append(chat.message)
        if not chat.message.tool_calls or len(chat.message.tool_calls) == 0:
            #print(chat.choices[0].message.content)
            print(chat.message.content)
            break
        else:
            for tool in chat.message.tool_calls:
                if(tool.function.name == "Read"):
                    arguments = json.loads(tool.function.arguments)
                    result = read_tool(arguments["file_path"])
                    res = {"role": "tool", "tool_call_id" : tool.id, "content" : result}
                    #res = json.loads('''{
                    #    "role": "tool",
                    #    "tool_call_id": {0}
                    #    "content" : {1}
                    #    }'''.format(tool.id, result))
                    messages.append(res)
                elif(tool.function.name == "Write"):
                    arguments = json.loads(tool.function.arguments)
                    result = write_tool(arguments["file_path"], arguments["content"])
                    res = {"role": "tool", "tool_call_id" : tool.id, "content": result}
                    messages.append(res)
                elif(tool.function.name == "Bash"):
                    arguments = json.loads(tool.function.arguments)
                    result = bash_tool(arguments["command"])
                    res = {"role": "tool", "tool_call_id": tool.id, "content": result}
                    messages.append(res)


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
        
        agent_loop(
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
                },
                    {
                        "type": "function",
                        "function": {
                            "name": "Write",
                            "description": "Write content to a file",
                            "parameters": {
                                "type": "object",
                                "required": ["file_path", "content"],
                                "properties": {
                                    "file_path": {
                                        "type": "string",
                                        "description": "The path of the file to write to"
                                        },
                                    "content": {
                                        "type": "string",
                                        "description": "The content to write to the file"
                                        }
                                    }
                                }
                            }
                        },
                    {
                        "type": "function",
                        "function": {
                            "name": "Bash",
                            "description": "Execute a shell command",
                            "parameters": {
                                "type": "object",
                                "required": ["command"],
                                "properties": {
                                    "command": {
                                        "type": "string",
                                        "description": "The command to execute"
                                        }
                                    }
                                }
                            }
                        }
                    ],
            client = client
        )
        print("Using Local Ollama Model...", file=sys.stderr)
        
    else:
        # --- CODECRAFTERS OPENROUTER SETUP ---
        api_key = os.getenv("OPENROUTER_API_KEY")
        base_url = os.getenv("OPENROUTER_BASE_URL", default="https://openrouter.ai/api/v1")
        
        if not api_key:
            raise RuntimeError("OPENROUTER_API_KEY is not set")
            
        client = OpenAI(api_key=api_key, base_url=base_url)
        
        agent_loop(
            model="anthropic/claude-haiku-4.5",
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
                },
                    {
                        "type": "function",
                        "function": {
                            "name": "Write",
                            "description": "Write content to a file",
                            "parameters": {
                                "type": "object",
                                "required": ["file_path", "content"],
                                "properties": {
                                    "file_path": {
                                        "type": "string",
                                        "description": "The path of the file to write to"
                                        },
                                    "content": {
                                        "type": "string",
                                        "description": "The content to write to the file"
                                        }
                                    }
                                }
                            }
                        },
                    {
                        "type": "function",
                        "function": {
                            "name": "Bash",
                            "description": "Execute a shell command",
                            "parameters": {
                                "type": "object",
                                "required": ["command"],
                                "properties": {
                                    "command": {
                                        "type": "string",
                                        "description": "The command to execute"
                                        }
                                    }
                                }
                            }
                        }
                    ],
            client = client
        )
        #print("Using OpenRouter API...", file=sys.stderr)

    # 3. Handle the response
    #if not chat.choices or len(chat.choices) == 0:
     #   raise RuntimeError("no choices in response")
    

    # Logs from your program will appear here! Visible when running tests.
    #print("Logs from your program will appear here!", file=sys.stderr)
    #chat = chat.choices[0]
    

    #if not chat.message.tool_calls or len(chat.message.tool_calls) == 0:
    #    #print(chat.choices[0].message.content)
    #    print(chat.message.content)
    #else:
    #    function = chat.message.tool_calls
    #    if(function[0].function.name == "Read"):
    #        arguments = json.loads(function[0].function.arguments)
    #        read_tool(arguments["file_path"])

if __name__ == "__main__":
    main()
