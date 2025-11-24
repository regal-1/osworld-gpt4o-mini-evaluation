"""
GPT-4o-mini Computer-Use Agent for OSWorld

This agent uses OpenAI's GPT-4o-mini model to perform desktop computer tasks.
It follows the OSWorld agent interface pattern.
"""

import base64
import json
import logging
import os
import re
import time
from typing import Dict, List, Tuple, Optional

import requests
from openai import OpenAI
from openai import APIError, RateLimitError, BadRequestError, InternalServerError

from mm_agents.agent import (
    encode_image,
    linearize_accessibility_tree,
    trim_accessibility_tree,
)

logger = logging.getLogger("desktopenv.agent")


def parse_code_from_string(input_string: str) -> List[str]:
    """
    Parse pyautogui code from model response.
    
    The model should return code in a ```python code block or special commands:
    - ```WAIT``` for waiting
    - ```DONE``` for task completion
    - ```FAIL``` for task failure
    """
    input_string = input_string.strip()
    
    # Check for special commands (plain text or in backticks)
    # Pattern: ```WAIT```, ```DONE```, ```FAIL``` (with or without whitespace)
    special_pattern = r'```\s*(WAIT|DONE|FAIL)\s*```'
    special_match = re.search(special_pattern, input_string, re.IGNORECASE)
    if special_match:
        return [special_match.group(1).upper()]
    
    # Check for plain special commands
    if input_string.upper() in ['WAIT', 'DONE', 'FAIL']:
        return [input_string.upper()]
    
    # Try to extract Python code from markdown code blocks
    # Pattern 1: ```python ... ``` (with optional whitespace)
    python_pattern = r'```python\s*(.*?)\s*```'
    matches = re.findall(python_pattern, input_string, re.DOTALL)
    
    if matches:
        # Return the first match (should be one code block)
        code = matches[0].strip()
        # Check if code block ends with special command
        if code.upper().endswith('WAIT'):
            return ["WAIT"]
        if code.upper().endswith('DONE'):
            return ["DONE"]
        if code.upper().endswith('FAIL'):
            return ["FAIL"]
        return [code] if code else ["FAIL"]
    
    # Pattern 2: ``` ... ``` (generic code block with optional whitespace)
    generic_pattern = r'```\s*(.*?)\s*```'
    matches = re.findall(generic_pattern, input_string, re.DOTALL)
    
    if matches:
        code = matches[0].strip()
        # Check for special commands
        if code.upper() in ['WAIT', 'DONE', 'FAIL']:
            return [code.upper()]
        # Remove 'python' if it's the first line
        if code.lower().startswith('python'):
            code = '\n'.join(code.split('\n')[1:]).strip()
        # Check if code block ends with special command
        if code.upper().endswith('WAIT'):
            return ["WAIT"]
        if code.upper().endswith('DONE'):
            return ["DONE"]
        if code.upper().endswith('FAIL'):
            return ["FAIL"]
        return [code] if code else ["FAIL"]
    
    # If no code block found, check if it's raw code
    if 'pyautogui' in input_string.lower():
        return [input_string]
    
    # If nothing matches, return FAIL
    logger.warning(f"Could not parse code from response: {input_string[:200]}")
    return ["FAIL"]


class GPT4oMiniAgent:
    """
    GPT-4o-mini Computer-Use Agent for OSWorld.
    
    This agent uses OpenAI's GPT-4o-mini vision model to:
    1. Observe screenshots and accessibility trees
    2. Generate pyautogui commands to complete tasks
    3. Maintain conversation history for context
    """
    
    def __init__(
        self,
        platform: str = "ubuntu",
        model: str = "gpt-4o-mini",
        max_tokens: int = 1000,  # Reduced from 1500 to save tokens
        top_p: float = 0.9,
        temperature: float = 0.5,
        action_space: str = "pyautogui",
        observation_type: str = "screenshot",  # Changed to screenshot-only to reduce tokens
        max_trajectory_length: int = 1,  # Reduced to 1 to minimize token usage
        a11y_tree_max_tokens: int = 10000,
        client_password: str = "password",
        api_key: Optional[str] = None,
    ):
        """
        Initialize the GPT-4o-mini agent.
        
        Args:
            platform: Operating system platform (default: "ubuntu")
            model: OpenAI model name (default: "gpt-4o-mini")
            max_tokens: Maximum tokens in response
            top_p: Top-p sampling parameter
            temperature: Temperature for sampling
            action_space: Action space type (default: "pyautogui")
            observation_type: Observation type (default: "screenshot_a11y_tree")
            max_trajectory_length: Max number of previous observations to keep
            a11y_tree_max_tokens: Max tokens for accessibility tree
            client_password: Password for sudo operations
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
        """
        self.platform = platform
        self.model = model
        self.max_tokens = max_tokens
        self.top_p = top_p
        self.temperature = temperature
        self.action_space = action_space
        self.observation_type = observation_type
        self.max_trajectory_length = max_trajectory_length
        self.a11y_tree_max_tokens = a11y_tree_max_tokens
        self.client_password = client_password
        
        # Initialize OpenAI client
        api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "OpenAI API key not provided. Set OPENAI_API_KEY environment variable "
                "or pass api_key parameter."
            )
        self.client = OpenAI(api_key=api_key)
        
        # Initialize conversation history
        self.thoughts = []
        self.actions = []
        self.observations = []
        
        # System prompt for pyautogui actions
        self.system_message = self._build_system_prompt()
        
        logger.info(f"Initialized GPT-4o-mini agent with model: {self.model}")
    
    def _build_system_prompt(self) -> str:
        """Build the system prompt based on observation and action space."""
        # Different prompts for different observation types
        if self.observation_type == "screenshot_a11y_tree":
            prompt = """You are an agent that follows instructions and performs desktop computer tasks.

You have good knowledge of computer operations and internet connectivity. Your code will run on a computer to control the mouse and keyboard.

For each step, you will receive:
1. A screenshot of the computer screen
2. An accessibility tree in table format with columns: tag, name, text, class, description, position (top-left x&y), size (w&h)

CRITICAL INSTRUCTIONS FOR USING ACCESSIBILITY TREE:
- The accessibility tree is a TABLE with coordinates in the "position (top-left x&y)" column
- Format: "position (top-left x&y)" contains coordinates like "x,y" (e.g., "100,200" means x=100, y=200)
- ALWAYS extract coordinates from the tree table - DO NOT guess coordinates from the screenshot
- Look for interactive elements (buttons, links, text fields) in the tree and use their exact coordinates
- The tree shows element names, roles, and states - use this to identify the correct element
- Example: If tree shows "button\tTrash\t\t\t100,784\t50x50", use pyautogui.click(100, 784) NOT guessed coordinates

REQUIREMENTS:
- Use `pyautogui` to perform actions based on your observations
- DO NOT use `pyautogui.locateCenterOnScreen()` - we don't have template images
- DO NOT use `pyautogui.screenshot()` - you already have the screenshot
- MANDATORY: Extract coordinates from accessibility tree "position (top-left x&y)" column - parse the "x,y" format
- DO NOT guess coordinates - always use tree coordinates
- Return complete, executable Python code each time
- When predicting multiple lines of code, add small delays like `time.sleep(0.5)` between actions
- Each code prediction must be complete and standalone (no shared variables from history)

Return format:
- Wrap your Python code in a ```python code block
- If you need to wait, return ```WAIT```
- If the task is complete, return ```DONE```
- If the task cannot be completed, return ```FAIL``` (but try your best first!)

The computer's password is '{CLIENT_PASSWORD}' - use it when sudo access is needed.

WORKFLOW:
1. Read the accessibility tree table and identify the target element (by name, role, or description)
2. Extract coordinates from the "position (top-left x&y)" column (format: "x,y")
3. Use those exact coordinates in pyautogui.click(x, y)
4. First, briefly reflect on which element from the tree you're targeting and its coordinates. Then return ONLY the code or special command requested. NEVER return anything else.""".format(
                CLIENT_PASSWORD=self.client_password
            )
        else:
            prompt = """You are an agent that follows instructions and performs desktop computer tasks.

You have good knowledge of computer operations and internet connectivity. Your code will run on a computer to control the mouse and keyboard.

For each step, you will receive a screenshot of the computer screen, and you will predict the next action to take.

Requirements:
- Use `pyautogui` to perform actions based on your observations
- DO NOT use `pyautogui.locateCenterOnScreen()` - we don't have template images
- DO NOT use `pyautogui.screenshot()` - you already have the screenshot
- Return complete, executable Python code each time
- Use coordinates based on your observation of the current screenshot
- When predicting multiple lines of code, add small delays like `time.sleep(0.5)` between actions
- Each code prediction must be complete and standalone (no shared variables from history)

Return format:
- Wrap your Python code in a ```python code block
- If you need to wait, return ```WAIT```
- If the task is complete, return ```DONE```
- If the task cannot be completed, return ```FAIL``` (but try your best first!)

The computer's password is '{CLIENT_PASSWORD}' - use it when sudo access is needed.

First, briefly reflect on the current screenshot and previous actions. Then return ONLY the code or special command requested. NEVER return anything else.""".format(
                CLIENT_PASSWORD=self.client_password
            )
        return prompt
    
    def reset(self, _logger=None, vm_ip=None):
        """Reset agent state for a new task.
        
        Args:
            _logger: Optional logger instance
            vm_ip: Optional VM IP address (for compatibility with lib_run_single.py, not used)
        """
        global logger
        if _logger is not None:
            logger = _logger
        
        self.thoughts = []
        self.actions = []
        self.observations = []
        logger.info("Agent state reset")
    
    def predict(
        self, instruction: str, obs: Dict
    ) -> Tuple[Dict, List[str]]:
        """
        Predict the next action(s) based on the current observation.
        
        Args:
            instruction: The task instruction
            obs: Observation dictionary with keys like:
                 - "screenshot": bytes (required)
                 - "accessibility_tree": dict (optional, depending on observation_type)
        
        Returns:
            Tuple of (info_dict, actions_list):
            - info_dict: Dictionary with metadata (response, model usage, etc.)
            - actions_list: List of action strings (pyautogui code)
        """
        # Build the conversation messages
        messages = []
        
        # Add system message with task instruction
        system_content = f"{self.system_message}\n\nYou are asked to complete the following task: {instruction}"
        messages.append({
            "role": "system",
            "content": system_content
        })
        
        # Add conversation history (limited by max_trajectory_length)
        history_obs = self.observations[-self.max_trajectory_length:] if len(self.observations) > self.max_trajectory_length else self.observations
        history_actions = self.actions[-self.max_trajectory_length:] if len(self.actions) > self.max_trajectory_length else self.actions
        history_thoughts = self.thoughts[-self.max_trajectory_length:] if len(self.thoughts) > self.max_trajectory_length else self.thoughts
        
        # Add previous observations, actions, and thoughts
        for prev_obs, prev_action, prev_thought in zip(history_obs, history_actions, history_thoughts):
            # Build user message with previous observation
            user_content = []
            
            if self.observation_type == "screenshot_a11y_tree" and prev_obs.get("accessibility_tree"):
                tree_text = prev_obs["accessibility_tree"]
                user_content.append({
                    "type": "text",
                    "text": f"Previous screenshot and accessibility tree:\n{tree_text}\nWhat's the next step?"
                })
                if prev_obs.get("screenshot"):
                    user_content.append({
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{prev_obs['screenshot']}",
                            "detail": "low"
                        }
                    })
            elif self.observation_type == "screenshot" and prev_obs.get("screenshot"):
                user_content.append({
                    "type": "text",
                    "text": "Previous screenshot. What's the next step?"
                })
                user_content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{prev_obs['screenshot']}",
                        "detail": "low"
                    }
                })
            
            if user_content:
                messages.append({
                    "role": "user",
                    "content": user_content
                })
            
            # Add assistant response (previous action/thought)
            if prev_thought:
                messages.append({
                    "role": "assistant",
                    "content": prev_thought
                })
        
        # Add current observation
        current_user_content = []
        
        # Process current observation based on type
        if self.observation_type == "screenshot_a11y_tree":
            # Encode screenshot
            screenshot_base64 = encode_image(obs["screenshot"])
            
            # Linearize accessibility tree
            a11y_tree_text = ""
            if obs.get("accessibility_tree"):
                a11y_tree_text = linearize_accessibility_tree(
                    accessibility_tree=obs["accessibility_tree"],
                    platform=self.platform
                )
                a11y_tree_text = trim_accessibility_tree(
                    a11y_tree_text,
                    self.a11y_tree_max_tokens
                )
            
            # Store observation
            self.observations.append({
                "screenshot": screenshot_base64,
                "accessibility_tree": a11y_tree_text
            })
            
            # Build user message
            current_user_content.append({
                "type": "text",
                "text": f"Current screenshot and accessibility tree:\n{a11y_tree_text}\nWhat's the next step to help with the task?"
            })
            current_user_content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{screenshot_base64}",
                    "detail": "low"
                }
            })
            
        elif self.observation_type == "screenshot":
            screenshot_base64 = encode_image(obs["screenshot"])
            
            self.observations.append({
                "screenshot": screenshot_base64,
                "accessibility_tree": None
            })
            
            current_user_content.append({
                "type": "text",
                "text": "Current screenshot. What's the next step to help with the task?"
            })
            current_user_content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{screenshot_base64}",
                    "detail": "low"
                }
            })
        else:
            raise ValueError(f"Unsupported observation_type: {self.observation_type}")
        
        messages.append({
            "role": "user",
            "content": current_user_content
        })
        
        # Call OpenAI API
        try:
            response = self._call_openai_api(messages)
        except Exception as e:
            logger.error(f"Failed to call OpenAI API: {e}")
            response = "FAIL"
        
        # Parse actions from response
        try:
            actions = parse_code_from_string(response)
            self.thoughts.append(response)
            self.actions.append(actions)
        except Exception as e:
            logger.error(f"Failed to parse actions: {e}")
            actions = ["FAIL"]
            self.thoughts.append("")
            self.actions.append(actions)
        
        # Build info dictionary
        info = {
            "response": response,
            "model": self.model,
        }
        
        return info, actions
    
    def _call_openai_api(self, messages: List[Dict]) -> str:
        """
        Call OpenAI API with retry logic and rate limiting protection.
        
        Args:
            messages: List of message dictionaries for the API
        
        Returns:
            Response text from the model
        """
        max_retries = 3  # Fixed 3 retries like working code
        retry_count = 0
        response_text = ""
        
        while retry_count < max_retries:
            try:
                logger.debug(f"Calling OpenAI API (attempt {retry_count + 1}/{max_retries})")
                
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    max_tokens=self.max_tokens,
                    temperature=self.temperature,
                    top_p=self.top_p,
                )
                
                content = response.choices[0].message.content
                logger.info(f"API response received: {content[:200]}...")
                return content
                
            except Exception as e:
                error_str = str(e)
                if "rate_limit" in error_str.lower() or "429" in error_str or isinstance(e, RateLimitError):
                    retry_count += 1
                    if retry_count < max_retries:
                        wait_time = 60  # Fixed 60-second wait like the working code
                        logger.warning(f"Rate limit hit, waiting {wait_time}s before retry {retry_count}/{max_retries}")
                        time.sleep(wait_time)
                    else:
                        logger.error(f"Failed to call {self.model} after {max_retries} retries: {error_str}")
                        response_text = "WAIT"
                        break
                else:
                    logger.error(f"Failed to call {self.model}, Error: {error_str}")
                    response_text = "WAIT"
                    break
        
        return response_text if response_text else "WAIT"
