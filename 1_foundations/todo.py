from rich.console import Console 
from dotenv import load_dotenv
from openai import OpenAI
import json
load_dotenv(overide=True)

def show(text):
    try:
        Console().print(text)
    except Exception:
        print(text)    
        
        
openai = OpenAI()

todos: list[str] = []
completed: list[bool]  = []

def get_todo_report() -> str:
    result =""
    for index,todo in enumerate(todos):
        if completed[index]:
            result += f"Todo #{index + 1}: [green][strike]{todo}[/strike][/green]\n"
        else:
            result += f"Todo #{index + 1}: {todo}\n"
    show(result)
    return result


get_todo_report()

def create_todos(descriptions: list[str]) -> str:
    todos.extend(descriptions)
    completed.extend([False] * len(descriptions))
    return get_todo_report()

def mark_complete(index: int, completion_notes: str) -> str:
    if 1 <= index <= len(todos):
        completed[index - 1] = True
    else:
        return "No todo at this index."
    Console().print(completion_notes)
    return get_todo_report()


todos, completed = [], []

create_todos(["Buy groceries", "Finish extra lab", "Eat banana"])