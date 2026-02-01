import argparse
import sys
import os
from pathlib import Path
from dotenv import load_dotenv
from src.utils.logger import log_experiment, ActionType
from src.orchestrator.graph import create_refactoring_graph
from src.utils.code_validator import SANDBOX_DIR
import time

# Load environment variables
load_dotenv()
api_key = os.getenv('GOOGLE_API_KEY')
if api_key:
    print(f"✅ API Key loaded: {api_key[:20]}...")
else:
    print("❌ ERROR: GOOGLE_API_KEY not found in environment!")
    sys.exit(1)


def process_file(file_path: str, max_iterations: int = 3) -> bool:
    """
    Process a single Python file through the refactoring workflow
    
    Args:
        file_path: Path to the Python file to fix
        max_iterations: Maximum number of fix attempts (default: 3)
    
    Returns:
        True if file was fixed successfully, False otherwise
    """
    print(f"\n{'='*60}")
    print(f"📄 Processing: {file_path}")
    print(f"{'='*60}")
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            buggy_code = f.read()
    except Exception as e:
        print(f"❌ Error reading file: {e}")
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
    
    # Initialize state with all required fields
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
    
    # Create and run the graph
    graph = create_refactoring_graph()
    
    try:
        # Add delay before starting to avoid rate limits
        print("⏳ Waiting 2 seconds before processing...")
        time.sleep(2)
        
        final_state = graph.invoke(
            initial_state,
            config={"recursion_limit": 50}
        )
        
        # Check if successful
        if final_state.get('is_fixed', False):
            base_name = os.path.basename(file_path)
            name_without_ext = os.path.splitext(base_name)[0]
            output_filename = f"{name_without_ext}_fixed.py"
            output_path = os.path.join(SANDBOX_DIR, output_filename)
            
            # The file is already saved by judge_agent, just verify
            if os.path.exists(output_path):
                print(f"\n✅ SUCCESS! Fixed code saved to: {output_path}")
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
                        "input_prompt": f"Processing file: {file_path}",
                        "output_response": f"Fixed in {final_state.get('iteration_count', 0)} iterations"
                    },
                    status="SUCCESS"
                )
                
                return True
            else:
                print(f"\n⚠️ Code was fixed but file not found at: {output_path}")
                # Try to save it manually
                try:
                    os.makedirs(SANDBOX_DIR, exist_ok=True)
                    with open(output_path, 'w', encoding='utf-8') as f:
                        fixed_code = final_state.get('refactored_code', final_state.get('fixed_code', final_state['code']))
                        f.write(fixed_code)
                    print(f"   ✅ Manually saved to: {output_path}")
                    
                    log_experiment(
                        agent_name="System",
                        model_used="N/A",
                        action=ActionType.GENERATION,
                        details={
                            "event": "FILE_SAVED_MANUALLY",
                            "file": file_path,
                            "output_file": output_path,
                            "input_prompt": f"Manual save: {file_path}",
                            "output_response": f"Saved to {output_path}"
                        },
                        status="SUCCESS"
                    )
                    
                    return True
                except Exception as e:
                    print(f"   ❌ Failed to save: {e}")
                    
                    log_experiment(
                        agent_name="System",
                        model_used="N/A",
                        action=ActionType.GENERATION,
                        details={
                            "event": "FILE_SAVE_ERROR",
                            "file": file_path,
                            "error": str(e),
                            "input_prompt": f"Saving fixed code: {file_path}",
                            "output_response": f"ERROR: {str(e)}"
                        },
                        status="FAILURE"
                    )
                    
                    return False
                
        else:
            print(f"\n⚠️ Could not fix file after {final_state.get('iteration_count', 0)} iterations")
            messages = final_state.get('messages', [])
            if messages:
                last_message = messages[-1].get('content', 'Unknown')
                print(f"   Last status: {last_message[:100]}")
            
            # Show pytest report if available
            pytest_report = final_state.get('pytest_report', '')
            if pytest_report:
                print(f"\n   📋 Last pytest output:")
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
        print(f"\n❌ Error processing file: {e}")
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
        default=3,
        help="Maximum fix attempts per file (default: 3)"
    )
    args = parser.parse_args()

    # Validate target directory
    if not os.path.exists(args.target_dir):
        print(f"❌ Directory not found: {args.target_dir}")
        sys.exit(1)

    print(f"\n{'='*60}")
    print(f"🚀 REFACTORING SWARM STARTING")
    print(f"{'='*60}")
    print(f"📂 Target Directory: {args.target_dir}")
    print(f"🔄 Max Iterations: {args.max_iterations}")
    print(f"🤖 Using Model: gemini-flash-latest")
    print(f"💾 Output Directory: {SANDBOX_DIR}")
    print(f"{'='*60}\n")
    
    # Create sandbox directory
    os.makedirs(SANDBOX_DIR, exist_ok=True)
    print(f"✅ Sandbox directory ready: {SANDBOX_DIR}\n")
    
    # Log startup
    log_experiment(
        agent_name="System",
        model_used="N/A",
        action=ActionType.ANALYSIS,
        details={
            "event": "STARTUP",
            "target_directory": args.target_dir,
            "output_directory": SANDBOX_DIR,
            "max_iterations": args.max_iterations,
            "input_prompt": f"Starting refactoring workflow on directory: {args.target_dir}",
            "output_response": "System initialized successfully"
        },
        status="SUCCESS"
    )
    
    # Find all Python files in target directory
    target_path = Path(args.target_dir)
    python_files = list(target_path.rglob("*.py"))
    
    # ✅ FILTER LOGIC:
    # The workflow tests CODE using doctests (via pytest --doctest-modules)
    # We filter out:
    # 1. Previously generated _fixed.py files
    # 2. System __init__.py files
    # 3. External test_*.py files (NOT part of the code to fix)
    #
    # ⚠️ IMPORTANT: This system VALIDATES code using doctests embedded in the code,
    # NOT by running external test_*.py files. The pytest tool in tools.py runs
    # "pytest --doctest-modules" which tests:
    #   - Doctests in docstrings
    #   - Basic Python assertions
    #   - Syntax validity
    python_files = [
        f for f in python_files 
        if not str(f).endswith("_fixed.py") 
        and not str(f).endswith("__init__.py")
        and not os.path.basename(str(f)).startswith("test_")
    ]

    if not python_files:
        print(f"⚠️ No Python files found in {args.target_dir}")
        log_experiment(
            agent_name="System",
            model_used="N/A",
            action=ActionType.ANALYSIS,
            details={
                "event": "NO_FILES",
                "directory": args.target_dir,
                "input_prompt": f"Searching for Python files in: {args.target_dir}",
                "output_response": "No Python files found to process"
            },
            status="SUCCESS"
        )
        print("\n✅ MISSION COMPLETE (No files to process)")
        sys.exit(0)
    
    print(f"📦 Found {len(python_files)} Python file(s) to process:")
    for i, py_file in enumerate(python_files, 1):
        print(f"   {i}. {py_file.name}")
    print(f"{'='*60}\n")
    
    # Process each file
    fixed_count = 0
    failed_files = []
    
    for i, py_file in enumerate(python_files, 1):
        print(f"\n{'='*60}")
        print(f"📝 File {i}/{len(python_files)}")
        print(f"{'='*60}")
        
        try:
            if process_file(str(py_file), args.max_iterations):
                fixed_count += 1
            else:
                failed_files.append(str(py_file))
        except KeyboardInterrupt:
            print("\n\n⚠️ Process interrupted by user")
            print(f"Processed {i}/{len(python_files)} files before interruption")
            break
        except Exception as e:
            print(f"\n❌ Unexpected error processing {py_file}: {e}")
            failed_files.append(str(py_file))
            
            log_experiment(
                agent_name="System",
                model_used="N/A",
                action=ActionType.ANALYSIS,
                details={
                    "event": "UNEXPECTED_ERROR",
                    "file": str(py_file),
                    "error": str(e),
                    "input_prompt": f"Processing file {i}/{len(python_files)}",
                    "output_response": f"ERROR: {str(e)}"
                },
                status="FAILURE"
            )
        
        # Add delay between files to avoid API rate limits
        if i < len(python_files):
            print("\n⏳ Waiting 5 seconds before next file...")
            time.sleep(5)
    
    # Summary
    print(f"\n{'='*60}")
    print("📊 FINAL SUMMARY")
    print(f"{'='*60}")
    print(f"Total files processed: {len(python_files)}")
    print(f"✅ Successfully fixed: {fixed_count}")
    print(f"❌ Failed to fix: {len(failed_files)}")
    print(f"💾 Fixed files saved to: {SANDBOX_DIR}")
    
    if failed_files:
        print(f"\n⚠️ Failed files:")
        for failed in failed_files:
            print(f"   - {failed}")
    
    print(f"{'='*60}\n")
    
    # Log completion
    log_experiment(
        agent_name="System",
        model_used="N/A",
        action=ActionType.GENERATION,
        details={
            "event": "COMPLETION",
            "total_files": len(python_files),
            "fixed_count": fixed_count,
            "failed_count": len(failed_files),
            "failed_files": failed_files,
            "output_directory": SANDBOX_DIR,
            "success_rate": f"{(fixed_count/len(python_files)*100):.1f}%" if python_files else "N/A",
            "input_prompt": f"Processing {len(python_files)} files",
            "output_response": f"Fixed {fixed_count}/{len(python_files)} files"
        },
        status="SUCCESS"
    )
    
    print("✅ MISSION COMPLETE")
    print(f"📋 Logs saved to: logs/experiment_data.json")
    print(f"📁 Fixed files in: {SANDBOX_DIR}\n")


if __name__ == "__main__":
    main()