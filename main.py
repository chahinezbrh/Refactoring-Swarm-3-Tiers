import argparse
import sys
import os
from pathlib import Path
from dotenv import load_dotenv
from src.utils.logger import log_experiment, ActionType
from src.orchestrator.graph import create_refactoring_graph
from src.utils.code_validator import SANDBOX_DIR
import time

# Import write_file from tools
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tools import write_file

# Load environment variables
load_dotenv()
api_key = os.getenv('GOOGLE_API_KEY')
if api_key:
    print(f"✅ API Key loaded: {api_key[:20]}...")
else:
    print("❌ ERROR: GOOGLE_API_KEY not found in environment!")
    sys.exit(1)


def process_file (file_path: str, max_iterations: int = 30) -> bool:
    """
    Process a single Python file through the refactoring workflow
    
    Args:
        file_path: Path to the Python file to fix
        max_iterations: Maximum number of fix attempts (default: 10, max: 10)
    
    Returns:
        True if file was fixed successfully, False otherwise
    """
    # Clamp max_iterations here too, not just in main()'s argparse validation —
    # process_file can be called directly (tests, future API), bypassing main().
    if max_iterations > 1:
        print(f" Invalid max_iterations ({max_iterations}), defaulting to 1")
        max_iterations = 1
    elif max_iterations > 10:
        print(f" max_iterations capped at 10 (got {max_iterations}, default parameter is 25 — flagging the mismatch)")
        max_iterations = 10

    print(f"\n{'='*60}")
    print(f" Processing: {file_path}")
    print(f"{'='*60}")
    
    # ========================================================================
    # STEP 1: READ INPUT FILE
    # ========================================================================
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            buggy_code = f.read()

    except Exception as e:
        print(f" Error reading file: {e}")
        log_experiment(
            agent_name="System",
            model_used="N/A",
            action=ActionType.ANALYSIS,
            details={
                "event": "FILE_READ_ERROR",
                "file": file_path,
                "error": str(e),
                "input_prompt": f"Reading file: {file_path}",
                "output_response": f"ERROR: {str(e)}"
            },
            status="FAILURE"
        )
        return False
    
    # ========================================================================
    # STEP 2: INITIALIZE STATE
    # ========================================================================
    initial_state = {
        "code": buggy_code,
        "file_name": file_path,
        "analysis_result": "",
        "debug_info": "",
        "fixed_code": buggy_code,
        "refactored_code": buggy_code,
        "refactoring_plan": "",
        "is_fixed": False,
        "iteration_count": 0,
        "max_iterations": max_iterations,
        "messages": [],
        "pylint_report": "",
        "pytest_report": "",
        "specific_test_failures": "",
        "pattern_detection": ""
    }
    
    # ========================================================================
    # STEP 3: RUN WORKFLOW
    # ========================================================================
    graph = create_refactoring_graph()
    
    try:
        # Add delay before starting to avoid rate limits
        print(" Waiting 2 seconds before processing...")
        time.sleep(2)
        
        final_state = graph.invoke(
            initial_state,
            config={"recursion_limit": 50}
        )
        
        # ====================================================================
        # STEP 4: CHECK IF SUCCESSFUL
        # ====================================================================
        if final_state.get('is_fixed', False):
            # ================================================================
            # STEP 5: WRITE FINAL OUTPUT USING write_file()
            # write_file() automatically adds "_fixed" to filename
            # ================================================================
            try:
                # Get final code from state
                final_code = final_state.get('refactored_code', final_state.get('fixed_code', final_state['code']))
                
                # Get just the filename (not full path) for write_file
                base_filename = os.path.basename(file_path)
                
                # Write using write_file() - it will add "_fixed" automatically
                result = write_file(base_filename, final_code)
                
                # Check if write was successful
                if "SUCCESS" in result:
                    # Build the output path (write_file adds _fixed automatically)
                    name_without_ext = os.path.splitext(base_filename)[0]
                    output_filename = f"{name_without_ext}_fixed.py"
                    output_path = os.path.join(SANDBOX_DIR, output_filename)
                    
                    print(f"\n SUCCESS! Fixed code saved to: {output_path}")
                    print(f"   Original: {file_path}")
                    print(f"   Fixed: {output_path}")
                    print(f"   Iterations used: {final_state.get('iteration_count', 0)}/{max_iterations}")
                    
                    # Log success
                    log_experiment(
                        agent_name="System",
                        model_used="N/A",
                        action=ActionType.GENERATION,
                        details={
                            "event": "FILE_FIXED_SUCCESS",
                            "file": file_path,
                            "output_file": output_path,
                            "iterations": final_state.get('iteration_count', 0),
                            "max_iterations": max_iterations,
                            "write_result": result,
                            "input_prompt": f"Processing file: {file_path}",
                            "output_response": f"Fixed in {final_state.get('iteration_count', 0)} iterations"
                        },
                        status="SUCCESS"
                    )
                    
                    return True
                else:
                    # Write failed (security or syntax error)
                    print(f"\n Failed to save fixed code: {result}")
                    
                    log_experiment(
                        agent_name="System",
                        model_used="N/A",
                        action=ActionType.GENERATION,
                        details={
                            "event": "FILE_SAVE_ERROR",
                            "file": file_path,
                            "error": result,
                            "input_prompt": f"Saving fixed code: {file_path}",
                            "output_response": result
                        },
                        status="FAILURE"
                    )
                    
                    return False
                
            except Exception as e:
                print(f"     Failed to save fixed code: {e}")
                
                log_experiment(
                    agent_name="System",
                    model_used="N/A",
                    action=ActionType.GENERATION,
                    details={
                        "event": "FILE_SAVE_EXCEPTION",
                        "file": file_path,
                        "error": str(e),
                        "input_prompt": f"Saving fixed code: {file_path}",
                        "output_response": f"ERROR: {str(e)}"
                    },
                    status="FAILURE"
                )
                
                return False
                
        else:
            # ================================================================
            # FAILURE: Could not fix after max iterations
            # ================================================================
            print(f"\n Could not fix file after {final_state.get('iteration_count', 0)} iterations")
            messages = final_state.get('messages', [])
            if messages:
                last_message = messages[-1].get('content', 'Unknown')
                print(f"   Last status: {last_message[:100]}")
            
            # Show pytest report if available
            pytest_report = final_state.get('pytest_report', '')
            if pytest_report:
                print(f"\n    Last pytest output:")
                print(f"   {'-'*50}")
                for line in pytest_report.split('\n')[:15]:
                    if line.strip():
                        print(f"   {line}")
                print(f"   {'-'*50}")
            
            # Log partial success/failure
            log_experiment(
                agent_name="System",
                model_used="N/A",
                action=ActionType.GENERATION,
                details={
                    "event": "FILE_FIX_INCOMPLETE",
                    "file": file_path,
                    "iterations_used": final_state.get('iteration_count', 0),
                    "max_iterations": max_iterations,
                    "last_message": messages[-1].get('content', 'Unknown') if messages else 'No messages',
                    "input_prompt": f"Processing file: {file_path}",
                    "output_response": f"Failed after {final_state.get('iteration_count', 0)} iterations"
                },
                status="PARTIAL"
            )
            
            return False
            
    except Exception as e:
        print(f"\n Error processing file: {e}")
        import traceback
        traceback.print_exc()
        
        log_experiment(
            agent_name="System",
            model_used="N/A",
            action=ActionType.ANALYSIS,
            details={
                "event": "FILE_PROCESSING_ERROR",
                "file": file_path,
                "error": str(e),
                "traceback": traceback.format_exc(),
                "input_prompt": f"Processing file: {file_path}",
                "output_response": f"ERROR: {str(e)}"
            },
            status="FAILURE"
        )
        return False


def main():
    # Set up the CLI argument parser for the refactoring swarm
    parser = argparse.ArgumentParser(
        description="Refactoring Swarm - Multi-Agent Code Fixer with Pylint & Pytest"
    )
    parser.add_argument(
        "--target_dir", 
        type=str, 
        required=True,
        help="Directory containing Python files to fix"
    )
    parser.add_argument(
        "--max_iterations", 
        type=int, 
        default=10,
        help="Maximum fix attempts per file (default: 10, max: 10)"
    )
    args = parser.parse_args()

    # ========================================================================
    # VALIDATE PARAMETERS
    # ========================================================================

    # max_iterations must be at least 1 — anything below that is nonsensical
    match args.max_iterations:
        case n if n < 1:
            print(f" ERROR: max_iterations must be at least 1 (got {n})")
            sys.exit(1)
        case n if n > 10:
            print(f" WARNING: max_iterations cannot exceed 10 (got {n})")
            print(f"   Clamping max_iterations down to 10")
            args.max_iterations = 10

    # Validate target directory: must exist AND actually be a directory,
    # not just any existing path — passing a file here would previously
    # slip past this check and fail unpredictably inside rglob() below.
    target_path = Path(args.target_dir)

    if not target_path.exists():
        print(f" Directory not found: {args.target_dir}")
        sys.exit(1)

    if not target_path.is_dir():
        print(f" Path exists but is not a directory: {args.target_dir}")
        sys.exit(1)

if __name__ == "__main__":
    main()