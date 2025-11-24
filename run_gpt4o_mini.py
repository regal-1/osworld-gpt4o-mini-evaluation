"""
Run OSWorld tasks with GPT-4o-mini agent.

Usage:
    python run_gpt4o_mini.py --example evaluation_examples/examples/os/94d95f96-9699-4208-98ba-3c3119edf9c2.json
    
Or run multiple examples:
    python run_gpt4o_mini.py --example_dir evaluation_examples/examples/os
"""

import argparse
import json
import logging
import os
import sys
import time
import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from desktop_env.desktop_env import DesktopEnv
from osworld_gpt4omini_agent.gpt4o_mini_agent import GPT4oMiniAgent

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global experiment logger (for centralized logging when running individual tasks)
experiment_logger = None


def setup_logger(example, example_result_dir):
    """Setup logger for a specific example."""
    log_file = os.path.join(example_result_dir, "log.txt")
    example_logger = logging.getLogger(f"example_{example.get('id', 'unknown')}")
    example_logger.setLevel(logging.INFO)
    
    if not example_logger.handlers:
        handler = logging.FileHandler(log_file)
        handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        example_logger.addHandler(handler)
    
    return example_logger


def run_single_example(agent, env, example, max_steps, instruction, args, example_result_dir):
    """
    Run a single example with the GPT-4o-mini agent.
    
    Args:
        agent: GPT-4o-mini agent instance
        env: DesktopEnv instance
        example: Example task configuration
        max_steps: Maximum number of steps
        instruction: Task instruction
        args: Command-line arguments
        example_result_dir: Directory to save results
    """
    global experiment_logger
    
    runtime_logger = setup_logger(example, example_result_dir)
    
    # Reset agent and environment
    agent.reset(runtime_logger)
    
    if experiment_logger:
        experiment_logger.info("Resetting environment for task...")
    env.reset(task_config=example)
    
    # Wait for environment to be ready
    logger.info("Waiting for environment to be ready...")
    time.sleep(10)
    
    # Wait before first API call to avoid rate limits
    # NOTE: If you still get rate limit errors, wait 5 minutes and try again
    logger.info("Waiting 15 seconds before first API call to avoid rate limits...")
    logger.info("NOTE: If rate limit errors persist, wait 5 minutes between tasks")
    time.sleep(15)  # 15 second delay before first call
    
    # Get initial observation
    obs = env._get_obs()
    done = False
    step_idx = 0
    
    # Start recording
    env.controller.start_recording()
    
    logger.info(f"Starting task: {instruction}")
    if experiment_logger:
        experiment_logger.info("Starting task execution...")
    
    while not done and step_idx < max_steps:
        # Get prediction from agent
        # Add delay before API call to avoid rate limits (except first call)
        if step_idx > 0:
            logger.info("Waiting 10 seconds before API call to avoid rate limits...")
            time.sleep(10)  # 10 second delay between API calls to avoid rate limits
        
        response, actions = agent.predict(instruction, obs)
        
        logger.info(f"Step {step_idx + 1}: Got {len(actions)} action(s)")
        if experiment_logger:
            experiment_logger.info("Step %d: Got %d action(s)", step_idx + 1, len(actions))
        logger.debug(f"Response: {response.get('response', '')[:200]}...")
        
        # Execute actions
        for action in actions:
            if not action:
                continue
            
            action_timestamp = time.strftime("%Y%m%d@%H%M%S")
            logger.info(f"Executing action: {action[:100]}...")
            
            try:
                # Execute action in environment
                obs, reward, done, info = env.step(action, args.sleep_after_execution)
                
                logger.info(f"Reward: {reward:.2f}, Done: {done}")
                if experiment_logger:
                    experiment_logger.info("Step %d executed. Reward: %.2f, Done: %s", 
                                          step_idx + 1, reward, done)
                
                # Save screenshot
                screenshot_path = os.path.join(
                    example_result_dir,
                    f"step_{step_idx + 1}_{action_timestamp}.png"
                )
                with open(screenshot_path, "wb") as f:
                    f.write(obs['screenshot'])
                
                # Save trajectory
                traj_path = os.path.join(example_result_dir, "traj.jsonl")
                with open(traj_path, "a") as f:
                    traj_entry = {
                        "step_num": step_idx + 1,
                        "action_timestamp": action_timestamp,
                        "action": action,
                        "response": response.get('response', ''),
                        "reward": reward,
                        "done": done,
                        "info": info,
                        "screenshot_file": f"step_{step_idx + 1}_{action_timestamp}.png"
                    }
                    f.write(json.dumps(traj_entry) + "\n")
                
                if done:
                    logger.info("Task completed or terminated.")
                    break
                    
            except Exception as e:
                logger.error(f"Error executing action: {e}")
                done = True
                break
        
        step_idx += 1
        
        # Check for terminal actions
        if actions and actions[0] in ['DONE', 'FAIL']:
            done = True
            logger.info(f"Agent returned terminal action: {actions[0]}")
    
    # Stop recording
    env.controller.end_recording(os.path.join(example_result_dir, "recording.mp4"))
    
    # Evaluate result
    try:
        if experiment_logger:
            experiment_logger.info("Evaluating task...")
            experiment_logger.info("Total steps taken: %d (max: %d)", step_idx, max_steps)
        
        result = env.evaluate()
        logger.info(f"Evaluation result: {result}")
        
        # Save result
        result_path = os.path.join(example_result_dir, "result.txt")
        with open(result_path, "w") as f:
            f.write(f"{result}\n")
        
        if experiment_logger:
            experiment_logger.info("Task completed. Score: %.2f", result)
            
        return result
    except Exception as e:
        logger.error(f"Error during evaluation: {e}")
        if experiment_logger:
            experiment_logger.error("Error during evaluation: %s", str(e))
        return 0.0


def main():
    parser = argparse.ArgumentParser(description="Run OSWorld tasks with GPT-4o-mini agent")
    
    # Agent arguments
    parser.add_argument("--model", type=str, default="gpt-4o-mini", help="OpenAI model name")
    parser.add_argument("--max_tokens", type=int, default=1000, help="Max tokens in response (reduced to save tokens)")
    parser.add_argument("--temperature", type=float, default=0.5, help="Temperature for sampling")
    parser.add_argument("--top_p", type=float, default=0.9, help="Top-p for sampling")
    parser.add_argument("--max_trajectory_length", type=int, default=1, help="Max conversation history (reduced to minimize tokens)")
    parser.add_argument("--observation_type", type=str, default="screenshot",
                       choices=["screenshot", "a11y_tree", "screenshot_a11y_tree"],
                       help="Observation type (default: screenshot to minimize tokens)")
    
    # Environment arguments
    parser.add_argument("--example", type=str, help="Path to example JSON file")
    parser.add_argument("--example_dir", type=str, help="Directory containing example JSON files")
    parser.add_argument("--max_steps", type=int, default=30, help="Maximum number of steps")
    parser.add_argument("--sleep_after_execution", type=float, default=0.5, help="Sleep after action execution")
    parser.add_argument("--platform", type=str, default="ubuntu", help="Platform")
    parser.add_argument("--password", type=str, default="password", help="VM password")
    parser.add_argument("--action_space", type=str, default="pyautogui", help="Action space")
    
    # Output arguments
    parser.add_argument("--output_dir", type=str, default="./results", help="Output directory")
    parser.add_argument("--experiment_log_file", type=str, default=None, 
                       help="Optional path to experiment-level log file (creates in logs/ if not specified)")
    
    args = parser.parse_args()
    
    # Setup experiment-level logger (always enabled for centralized logging)
    global experiment_logger
    # Create logs directory
    logs_dir = os.path.abspath(os.path.join(os.getcwd(), "logs"))
    os.makedirs(logs_dir, exist_ok=True)
    
    # Generate log filename if not provided or empty
    if not args.experiment_log_file or args.experiment_log_file.strip() == "":
        datetime_str = datetime.datetime.now().strftime("%Y%m%d@%H%M%S")
        log_file = os.path.join(logs_dir, f"gpt4o_mini_evaluation_{datetime_str}.log")
    else:
        # Normalize and validate the log file path
        log_file_path = args.experiment_log_file.strip()
        
        # If it's already absolute, use it as-is
        if os.path.isabs(log_file_path):
            log_file = log_file_path
        else:
            # Relative path - make it absolute from current directory
            log_file = os.path.abspath(log_file_path)
        
        # Validate that it's not the current directory
        if log_file == os.getcwd() or os.path.isdir(log_file):
            logger.warning(f"Log file path resolves to directory: {log_file}. Using default log file instead.")
            datetime_str = datetime.datetime.now().strftime("%Y%m%d@%H%M%S")
            log_file = os.path.join(logs_dir, f"gpt4o_mini_evaluation_{datetime_str}.log")
        else:
            # Ensure parent directory exists
            log_dir = os.path.dirname(log_file)
            if log_dir:
                os.makedirs(log_dir, exist_ok=True)
    
    # Setup experiment logger
    experiment_logger = logging.getLogger("desktopenv.experiment")
    experiment_logger.setLevel(logging.INFO)
    
    # Remove any existing handlers
    experiment_logger.handlers = []
    
    # Add file handler
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.INFO)
    formatter = logging.Formatter(
        fmt="[%(asctime)s] %(levelname)s %(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(formatter)
    experiment_logger.addHandler(file_handler)
    
    # Also add console handler for experiment logger
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    experiment_logger.addHandler(console_handler)
    
    logger.info(f"Experiment log will be written to: {log_file}")
    experiment_logger.info("Experiment logger initialized. Log file: %s", log_file)
    
    # Check for OpenAI API key
    if not os.environ.get("OPENAI_API_KEY"):
        logger.error("OPENAI_API_KEY environment variable not set!")
        logger.error("Please set it with: export OPENAI_API_KEY='your-api-key'")
        return
    
    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Log to experiment logger if available
    if experiment_logger:
        experiment_logger.info("Using observation type: %s", args.observation_type)
        experiment_logger.info("Model: %s, Temperature: %.1f, Max steps: %d", 
                              args.model, args.temperature, args.max_steps)
    
    # Initialize agent
    logger.info("Initializing GPT-4o-mini agent...")
    if experiment_logger:
        experiment_logger.info("Initialized GPT4oMiniAgent with observation_type=%s", args.observation_type)
    
    agent = GPT4oMiniAgent(
        platform=args.platform,
        model=args.model,
        max_tokens=args.max_tokens,
        temperature=args.temperature,
        top_p=args.top_p,
        action_space=args.action_space,
        observation_type=args.observation_type,
        max_trajectory_length=args.max_trajectory_length,
        client_password=args.password,
    )
    
    # Initialize environment
    logger.info("Initializing DesktopEnv...")
    env = DesktopEnv(
        provider_name="vmware",
        action_space=args.action_space,
        headless=False,  # Set to True for headless mode
    )
    
    # Load example(s)
    examples = []
    if args.example:
        with open(args.example, 'r') as f:
            examples.append(json.load(f))
    elif args.example_dir:
        example_dir = Path(args.example_dir)
        for json_file in example_dir.glob("*.json"):
            with open(json_file, 'r') as f:
                examples.append(json.load(f))
    else:
        logger.error("Either --example or --example_dir must be provided!")
        return
    
    logger.info(f"Found {len(examples)} example(s)")
    if experiment_logger:
        experiment_logger.info("Found %d example(s)", len(examples))
    
    # Run examples
    results = []
    for i, example in enumerate(examples):
        logger.info(f"\n{'='*60}")
        logger.info(f"Running example {i+1}/{len(examples)}: {example.get('id', 'unknown')}")
        logger.info(f"{'='*60}")
        
        instruction = example.get("instruction", "")
        example_id = example.get("id", f"example_{i}")
        
        # Extract domain from example file path
        domain = "unknown"
        if args.example:
            # Extract domain from path like: evaluation_examples/examples/os/xxx.json
            path_parts = Path(args.example).parts
            if "examples" in path_parts:
                idx = path_parts.index("examples")
                if idx + 1 < len(path_parts):
                    domain = path_parts[idx + 1]
        elif args.example_dir:
            domain = Path(args.example_dir).name
        
        # Log to experiment logger
        if experiment_logger:
            experiment_logger.info("")
            experiment_logger.info("=" * 80)
            experiment_logger.info("Running task: %s", example_id)
            experiment_logger.info("Domain: %s", domain)
            experiment_logger.info("Task ID: %s", example_id)
            experiment_logger.info("Instruction: %s", instruction)
            experiment_logger.info("=" * 80)
        
        # Create result directory for this example
        example_result_dir = os.path.join(args.output_dir, example_id)
        os.makedirs(example_result_dir, exist_ok=True)
        
        # Save example config
        with open(os.path.join(example_result_dir, "config.json"), "w") as f:
            json.dump(example, f, indent=2)
        
        # Run the example
        try:
            result = run_single_example(
                agent=agent,
                env=env,
                example=example,
                max_steps=args.max_steps,
                instruction=instruction,
                args=args,
                example_result_dir=example_result_dir,
            )
            results.append(result)
            
            # Log result to experiment logger
            if experiment_logger:
                experiment_logger.info("Evaluation result: %.2f", result)
        except Exception as e:
            logger.error(f"Error running example {example_id}: {e}")
            results.append(0.0)
            if experiment_logger:
                experiment_logger.error("Error running task %s: %s", example_id, str(e))
                experiment_logger.info("Evaluation result: 0.0")
    
    # Summary
    logger.info(f"\n{'='*60}")
    logger.info("Summary")
    logger.info(f"{'='*60}")
    logger.info(f"Total examples: {len(examples)}")
    avg_result = sum(results) / len(results) if results else 0.0
    logger.info(f"Average result: {avg_result:.2f}")
    logger.info(f"Results: {results}")
    
    # Log summary to experiment logger
    if experiment_logger:
        experiment_logger.info("")
        experiment_logger.info("=" * 80)
        experiment_logger.info("SUMMARY")
        experiment_logger.info("=" * 80)
        experiment_logger.info("Total examples: %d", len(examples))
        experiment_logger.info("Average result: %.2f", avg_result)
        if results:
            success_count = sum(1 for r in results if r > 0)
            success_rate = success_count / len(results) * 100
            experiment_logger.info("Success rate: %.1f%%", success_rate)
        experiment_logger.info("Results: %s", results)
    
    # Close environment
    env.close()
    logger.info("Environment closed.")


if __name__ == "__main__":
    main()
