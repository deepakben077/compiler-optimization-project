import os
import subprocess
import sys
import json
from pathlib import Path

def get_available_passes():
   """Get list of available optimization passes in LLVM 14."""
   try:
       # Changed from opt-14 to opt
       cmd = ['opt', '--print-passes']
       result = subprocess.run(cmd, capture_output=True, text=True)
       
       # Parse the output to get passes
       passes = []
       for line in result.stdout.split('\n'):
           if line.strip() and not line.startswith(' '):
               passes.append(line.strip())
       
       return passes
   except Exception as e:
       print(f"Error getting passes: {str(e)}")
       return []

def generate_ir(source_file, output_dir):
   """Generate LLVM IR from source file."""
   try:
       output_file = Path(output_dir) / f"{Path(source_file).stem}.ll"
       
       cmd = [
           'clang',  # Changed from clang-14 to clang
           '-S',
           '-emit-llvm',
           '-O0',  # No optimizations initially
           str(source_file),
           '-o',
           str(output_file)
       ]
       
       print(f"Generating IR for: {source_file}")
       result = subprocess.run(cmd, capture_output=True, text=True)
       
       if result.returncode == 0:
           print(f"Successfully generated IR: {output_file}")
           return output_file
       else:
           print(f"Error generating IR for {source_file}")
           print(f"Error: {result.stderr}")
           return None
           
   except Exception as e:
       print(f"Exception processing {source_file}: {str(e)}")
       return None

def save_pass_info(passes, output_dir):
   """Save pass information to a file."""
   pass_info = {
       'available_passes': passes,
       'total_passes': len(passes)
   }
   
   output_file = Path(output_dir) / 'available_passes.json'
   with open(output_file, 'w') as f:
       json.dump(pass_info, f, indent=2)
   
   print(f"Saved pass information to: {output_file}")

def main():
   # Setup paths
   project_dirs = {
       'ir': Path("../ir_files"),
       'passes': Path("../pass_orders"),
       'deps': Path("../pass_dependencies"),
       'metrics': Path("../metrics"),
       'results': Path("../results")
   }
   
   # Create all directories
   for dir_path in project_dirs.values():
       dir_path.mkdir(exist_ok=True)
   
   # Get available passes
   print("Getting available optimization passes...")
   passes = get_available_passes()
   if passes:
       save_pass_info(passes, project_dirs['passes'])
   
   # NEW CODE: Using absolute path from home directory
   home_dir = Path.home()  # Gets your home directory
   benchmark_dir = home_dir / "llvm-test-suite/SingleSource/Benchmarks"
   print(f"\nLooking for benchmarks in: {benchmark_dir}")
   
   if not benchmark_dir.exists():
       print(f"Error: Benchmark directory not found at {benchmark_dir}")
       return
       
   # Collect all source files with detailed logging
   source_files = []
   print("\nSearching for source files...")
   for ext in ['.c', '.cpp']:
       found_files = list(benchmark_dir.rglob(f'*{ext}'))
       source_files.extend(found_files)
       print(f"Found {len(found_files)} {ext} files")
   
   if not source_files:
       print("No source files found! Please verify the benchmark directory structure.")
       return
   
   print(f"\nTotal source files found: {len(source_files)}")
   print("\nFirst few files found:")
   for file in source_files[:5]:
       print(f"  - {file}")
   
   # Process each file
   successful = 0
   failed = 0
   
   for source_file in source_files:
       if generate_ir(source_file, project_dirs['ir']):
           successful += 1
       else:
           failed += 1
   
   print(f"\nSummary:")
   print(f"Successfully processed: {successful}")
   print(f"Failed: {failed}")
   print(f"Total files: {successful + failed}")
   print(f"Available passes: {len(passes)}")

if __name__ == "__main__":
   main()