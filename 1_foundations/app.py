from dotenv import load_dotenv
from openai import OpenAI
import json
import os
import requests
from pypdf import PdfReader
import gradio as gr

# Load environment variables from .env (OPENAI_API_KEY, PUSHOVER_TOKEN, PUSHOVER_USER)
load_dotenv(override=True)


# --- Notification helper ---

def push(text):
    """Send a real-time push notification to your phone via Pushover."""
    requests.post(
        "https://api.pushover.net/1/messages.json",
        data={
            "token": os.getenv("PUSHOVER_TOKEN"),
            "user": os.getenv("PUSHOVER_USER"),
            "message": text,
        }
    )


# --- Tool functions (called by the LLM via tool-use) ---

def record_user_details(email, name="Name not provided", notes="not provided"):
    """
    Called when a visitor expresses interest in getting in touch.
    Pushes their contact details to your phone so you can follow up.
    Returns a confirmation dict so the model knows it succeeded.
    """
    push(f"Recording {name} with email {email} and notes {notes}")
    return {"recorded": "ok"}


def record_unknown_question(question):
    """
    Called when the chatbot couldn't answer something.
    Logs the gap in knowledge so you can improve the summary/profile later.
    """
    push(f"Recording {question}")
    return {"recorded": "ok"}


# --- Tool schemas (JSON descriptions that tell the LLM when and how to call each tool) ---

record_user_details_json = {
    "name": "record_user_details",
    "description": "Use this tool to record that a user is interested in being in touch and provided an email address",
    "parameters": {
        "type": "object",
        "properties": {
            "email": {
                "type": "string",
                "description": "The email address of this user"
            },
            "name": {
                "type": "string",
                "description": "The user's name, if they provided it"
            },
            "notes": {
                "type": "string",
                "description": "Any additional information about the conversation that's worth recording to give context"
            }
        },
        "required": ["email"],
        "additionalProperties": False
    }
}

record_unknown_question_json = {
    "name": "record_unknown_question",
    "description": "Always use this tool to record any question that couldn't be answered as you didn't know the answer",
    "parameters": {
        "type": "object",
        "properties": {
            "question": {
                "type": "string",
                "description": "The question that couldn't be answered"
            },
        },
        "required": ["question"],
        "additionalProperties": False
    }
}

# Wrap schemas in the format OpenAI expects
tools = [{"type": "function", "function": record_user_details_json},
         {"type": "function", "function": record_unknown_question_json}]


# --- Main chatbot class ---

class Me:

    def __init__(self):
        self.openai = OpenAI()
        self.name = "Yonathan Galili"

        # Extract all text from your LinkedIn PDF export
        reader = PdfReader("me/linkedin.pdf")
        self.linkedin = ""
        for page in reader.pages:
            text = page.extract_text()
            if text:
                self.linkedin += text

        # Load a hand-written personal summary for richer context
        with open("me/summary.txt", "r", encoding="utf-8") as f:
            self.summary = f.read()

    def handle_tool_call(self, tool_calls):
        """
        Execute every tool the model requested and return the results
        in the 'tool' role format that OpenAI expects.

        Uses globals() to dynamically dispatch to the matching Python function
        by name — so function names must match the JSON schema 'name' fields exactly.
        """
        results = []
        for tool_call in tool_calls:
            tool_name = tool_call.function.name
            arguments = json.loads(tool_call.function.arguments)
            print(f"Tool called: {tool_name}", flush=True)
            tool = globals().get(tool_name)          # look up function by name
            result = tool(**arguments) if tool else {}
            results.append({
                "role": "tool",
                "content": json.dumps(result),
                "tool_call_id": tool_call.id          # links result back to the specific call
            })
        return results

    def system_prompt(self):
        """
        Build the system prompt that puts the model in character as you.
        Injects your summary and LinkedIn text so the model has factual grounding.
        """
        system_prompt = (
            f"You are acting as {self.name}. You are answering questions on {self.name}'s website, "
            f"particularly questions related to {self.name}'s career, background, skills and experience. "
            f"Your responsibility is to represent {self.name} for interactions on the website as faithfully as possible. "
            f"You are given a summary of {self.name}'s background and LinkedIn profile which you can use to answer questions. "
            f"Be professional and engaging, as if talking to a potential client or future employer who came across the website. "
            f"If you don't know the answer to any question, use your record_unknown_question tool to record the question that you couldn't answer, even if it's about something trivial or unrelated to career. "
            f"If the user is engaging in discussion, try to steer them towards getting in touch via email; ask for their email and record it using your record_user_details tool. "
        )
        system_prompt += f"\n\n## Summary:\n{self.summary}\n\n## LinkedIn Profile:\n{self.linkedin}\n\n"
        system_prompt += f"With this context, please chat with the user, always staying in character as {self.name}."
        return system_prompt

    def chat(self, message, history):
        """
        Main agentic loop — called by Gradio on each user message.

        Flow:
          1. Build messages list: system prompt + chat history + new user message
          2. Send to GPT-4o-mini
          3. If the model wants to call tools → execute them, append results, loop back
          4. If the model returns a plain text reply → return it to the UI
        """
        messages = [{"role": "system", "content": self.system_prompt()}] + history + [{"role": "user", "content": message}]
        done = False
        while not done:
            response = self.openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                tools=tools
            )
            if response.choices[0].finish_reason == "tool_calls":
                # Model requested tool calls — execute them and feed results back
                message = response.choices[0].message
                tool_calls = message.tool_calls
                results = self.handle_tool_call(tool_calls)
                messages.append(message)       # model's tool-call message
                messages.extend(results)       # our tool results
            else:
                # Model produced a final text response — exit the loop
                done = True
        return response.choices[0].message.content


if __name__ == "__main__":
    me = Me()
    # Launch a Gradio chat UI backed by the Me.chat method
    gr.ChatInterface(me.chat, type="messages").launch()
