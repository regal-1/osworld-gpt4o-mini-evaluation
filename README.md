# GPT-4o-mini Agent for OSWorld

An agentic implementation for OSWorld that uses OpenAI's GPT-4o-mini vision-language model to perform desktop computer tasks through screenshot-based observations and pyautogui actions.

## Overview

This agent implements the OSWorld agent interface to interact with desktop environments. It uses GPT-4o-mini to:
- Analyze screenshots of the desktop environment
- Generate Python code using `pyautogui` to perform actions (clicks, typing, keyboard shortcuts)
- Support both screenshot-only and screenshot-with-accessibility-tree observation modes
- Handle task execution with retry logic and rate limit management to stay within openai api limits.

## Installation

### Prerequisites

1. **OSWorld Environment**: This agent is designed to work with the OSWorld framework. Ensure you have OSWorld set up according to the [OSWorld documentation](https://github.com/xlang-ai/OSWorld).

2. **Python Dependencies**: Install required packages:
   ```bash
   pip install openai pyautogui requests
   ```

3. **OpenAI API Key**: Set your OpenAI API key as an environment variable:
   ```bash
   export OPENAI_API_KEY='your-api-key-here'
   ```

### Setup

1. Clone or navigate to the [OSWorld repository](https://github.com/xlang-ai/OSWorld):
   ```bash
   cd /path/to/OSWorld
   ```
2. Make sure your OSWorld environment is properly configured (VM setup, OSWorld server running, etc.)
   
3. Clone this osworld-gpt4o-mini-evaluation repository into a directory:
    ```bash
     git clone https://github.com/regal-1/osworld-gpt4o-mini-evaluation.git osworld_gpt4omini_agent
     ```
     
4. Navigate to the directory and ensure the following files exist:
   ``` bash
   cd /path/to/osworld_gpt4omini_agent
   ```
   - `gpt4o_mini_agent.py` - Main agent implementation
   - `run_gpt4o_mini.py` - Script to run evaluations
   - `__init__.py` - Package initialization


## Running Evaluation

### Single Task Evaluation

Run a single task example:

```bash
python osworld_gpt4omini_agent/run_gpt4o_mini.py \
    --example evaluation_examples/examples/os/94d95f96-9699-4208-98ba-3c3119edf9c2.json \
    --output_dir ./results/task1_spotify \
    --max_steps 15 \
    --observation_type screenshot
```

### Multiple Tasks

Run all examples in a directory:

```bash
python osworld_gpt4omini_agent/run_gpt4o_mini.py \
    --example_dir evaluation_examples/examples/os \
    --output_dir ./results/batch_run \
    --max_steps 15 \
    --observation_type screenshot
```

### Command-Line Arguments

- `--example`: Path to a single task JSON file
- `--example_dir`: Directory containing task JSON files
- `--output_dir`: Directory to save results (screenshots, trajectories, videos)
- `--max_steps`: Maximum number of steps per task (default: 15)
- `--observation_type`: Observation mode - `screenshot` or `screenshot_a11y_tree` (default: `screenshot`)
- `--max_trajectory_length`: Number of previous steps to include in context (default: 1)
- `--max_tokens`: Maximum tokens for API response (default: 1000)
- `--temperature`: Model temperature (default: 0.5)
- `--experiment_log_file`: Path to experiment-level log file (optional)

### Example with Accessibility Tree Mode

To use accessibility tree observations (provides UI element coordinates):

```bash
python osworld_gpt4omini_agent/run_gpt4o_mini.py \
    --example evaluation_examples/examples/os/5ea617a3-0e86-4ba6-aab2-dac9aa2e8d57.json \
    --output_dir ./results/task2_a11y \
    --max_steps 15 \
    --observation_type screenshot_a11y_tree
```

## Configuration

Default agent configuration:
- **Model**: GPT-4o-mini
- **Observation Type**: screenshot (or screenshot_a11y_tree)
- **Max Trajectory Length**: 1
- **Max Tokens**: 1000
- **Max Steps per Task**: 15
- **Temperature**: 0.5
- **Action Space**: pyautogui
- **Image Detail**: low (to minimize token usage)

## Results

Results are saved in the specified `--output_dir` directory. Each task execution creates:
- `result.txt`: Success (1.0) or failure (0.0) score
- `traj.jsonl`: Step-by-step trajectory with actions and observations
- `recording.mp4`: Video recording of the execution
- `step_X_*.png`: Screenshots at each step
- `log.txt`: Execution log

## Evaluation Report

For detailed evaluation results, analysis of failure modes, and recommendations, see **[REPORT.md](./REPORT.md)**.

The comprehensive evaluation report documents the agent's performance on 10 diverse OSWorld tasks spanning file management, web browser configuration, document editing, and code editing. The report includes:

- **Overall Results Summary**: Success rate statistics, step counts, and performance metrics across all tasks
- **Task-by-Task Analysis**: For each of the 10 tasks, detailed breakdowns including:
  - Task ID and category
  - Whether the task was solved by OSWorld evaluator
  - Number of steps taken
  - Notable failure cases and action sequences
  - Comparison between baseline (screenshot-only) and accessibility tree modes
- **Failure Mode Analysis**: Common patterns identified across failures, including:
  - Action loops and repetitive behavior
  - Hardcoded coordinate usage and coordinate imprecision
  - Premature task abandonment
  - UI element recognition challenges
- **Accessibility Tree Comparison**: Detailed analysis comparing screenshot-only mode with accessibility tree overlay mode, examining whether additional UI element information improves performance
- **Recommendations**: Discussion of potential improvements including prompt engineering, better tool integration, and UI hints utilization

**Read the full evaluation report:** See [REPORT.md](./REPORT.md) for complete details.

## Troubleshooting

**Rate Limit Errors**: If you encounter OpenAI API rate limit errors (HTTP 429), add billing information to your OpenAI account, increase delays between API calls, or wait 5 minutes between task runs. Free tier accounts have strict limits (3-5 requests per minute).

**Connection Errors**: If you see "No route to host" or connection errors to the OSWorld server, ensure the VM is powered on, verify the OSWorld server is running (`sudo systemctl status osworld_server` in the VM), and check that port 5000 is accessible. If port 5000 is in use, stop the service (`sudo systemctl stop osworld_server`) and restart it.

**X11 Authorization Errors**: If you see X11 display connection errors, run `xhost +local:` in the VM to allow local X11 connections.

**Missing Dependencies**: If you encounter import errors for `gymnasium` or `wrapt_timeout_decorator`, activate your conda environment (`conda activate osworld`) and install the missing packages: `pip install gymnasium wrapt_timeout_decorator`. Ensure you're running from the OSWorld root directory and all dependencies are installed.

## License

This agent implementation follows the OSWorld framework license. See the main OSWorld repository for license details.

## Contact

For questions about OSWorld, see the [OSWorld repository](https://github.com/xlang-ai/OSWorld).

