import argparse
import os
import sys
import json
import subprocess
import yaml
import re
import frontmatter
from pathlib import Path

from openai import OpenAI

# Global toggle: Set to 1 to use local Ollama, set to 0 before pushing to CodeCrafters
USE_LOCAL = 0


def initialize_skills():
    target_folder = Path("./.claude/skills")
    skills_metadata = dict()
    prefix = "SKILL.md"
    all_skill_files = [p for p in target_folder.rglob(f"{prefix}") if p.is_file()]
    for skill_file in all_skill_files:
        with open(skill_file, "r") as f:
            try:
                yaml_data = frontmatter.load(f)
                skills_metadata[yaml_data['name']]=yaml_data['description']
                
            except yaml.YAMLError as exc:
                print(f"Error parsing YAML: {exc}")
    return skills_metadata
    

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

def format_content(content, argument):
    arguments_supplied = False if argument == "" else True
    arguments_list = argument.split(" ")
    contents = content.split(" ")
    formatted_content=""
    for c in contents:
        if(re.search(r"^\$ARGUMENTS", c)):
            
            formatted_content = formatted_content + re.sub(r"^\$ARGUMENTS",argument,c) + " "
        elif (match:=re.search(r"^\$\d+",c)):
            if(arguments_supplied):
                formatted_content = formatted_content + re.sub(r"^\$\d+",arguments_list[int(match.group())],c) + " "
            else:
                
                formatted_content = formatted_content + re.sub(r"^\$\d+", "",c ) + " "
        else:
            formatted_content = formatted_content + c + " "
    return formatted_content
    # for c in contents:
    #     if c[0] == "$":
    #         if c[1:] == "ARGUMENTS":
    #             formatted_content = formatted_content + argument + " "
    #         else:
    #             nums = ""
    #             remaining = ""
    #             number = c[1:]
    #             for x in range(len(number)):
    #                 if number[x] in "1234567890":
    #                     nums +=number[x]
    #                 else:
    #                     remaining = number[x:] # append the remaining non numeric characters
    #                     break 
                

    #             n = int(nums)
    #             if(n< len(arguments_list)):
    #                 formatted_content = formatted_content + arguments_list[n] + remaining + " "
    #             else:
    #                 raise Exception("Invalid argument access")
    #     else:
    #         formatted_content = formatted_content + c + " "
    # return formatted_content

def parse_skill_invocation(prompt, skills_metadata):
    if(prompt[0] == "/"):
        parsed_prompt = prompt.split(" ")
        final_prompt = ""
        try:
            skill = parsed_prompt[0][1:].lower()
            if skill in skills_metadata.keys():
                skill_file = Path("./.claude/skills" + "/" +skill + "/SKILL.md")
                with open(skill_file, 'r', encoding= 'utf-8') as f:
                    post = frontmatter.load(f)
                    content = post.content
                    if len(parsed_prompt)>1: # length == 1 implies plain skill invocation >1 implies presence of arguments
                        ARGUMENT = " ".join(parsed_prompt[1:])
                        content = format_content(content, ARGUMENT)
                    else:
                        ARGUMENT = ""
                        content = format_content(content, ARGUMENT)
                    final_prompt  =  content
            return final_prompt
        except Exception as e:
            print(e) 
    else:
        return prompt 
    # parsed_prompt = prompt.split(" ")
    # final_prompt = ""
    # for p in parsed_prompt:
    #     if "/" == p[0]:  #Skill invocation starts with /
    #         try:
    #             skill = p[1:].lower()
    #             if  skill in skills_metadata.keys():
                    
    #                 skill_file = Path("./.claude/skills" + "/" + skill  + "/SKILL.md")
    #                 with open(skill_file, 'r', encoding = 'utf-8') as f:
    #                     post  = frontmatter.load(f)
    #                     final_prompt =final_prompt+ post.content + " " 
    #             else:
    #                 raise Exception("Skill not found.")
    #         except Exception as e:
    #             print(e)
    #     else:
    #         final_prompt= final_prompt+ p + " "
    # return final_prompt  

def main():
    # 1. Parse arguments FIRST, so args.p is ready for either API call
    p = argparse.ArgumentParser()
    p.add_argument("-p", required=True)
    args = p.parse_args()
    skills_metadata = initialize_skills()
    prompt = parse_skill_invocation(args.p, skills_metadata)
    skill_prompt_content = "You have access to the following skills:\n\n-"
    for key, value in skills_metadata.items():
        skill_prompt_content += f" {key}:{value}\n" 

    # 2. Setup the client and make the API call based on the global toggle
    api_key = "ollama" if USE_LOCAL == 1 else os.getenv("OPENROUTER_API_KEY")
    base_url = "http://localhost:11434/v1" if USE_LOCAL == 1 else os.getenv("OPENROUTER_BASE_URL", default="https://openrouter.ai/api/v1") 
    
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY or local Ollama model is not set")
            
    client = OpenAI(api_key=api_key, base_url=base_url)
    model = "llama3.1" if USE_LOCAL == 1 else "anthropic/claude-haiku-4.5"
        
    agent_loop(
            model= model, # Ensure you have run `ollama run llama3.1` in your terminal
            messages=[{"role":"system", "content": skill_prompt_content},{"role": "user", "content": prompt}],
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
    # print("Using Local Ollama Model...", file=sys.stderr)
        
        

if __name__ == "__main__":
    main()
