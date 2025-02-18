import os
import subprocess

# Paths
ir_dir = "/home/user/llvm_optimization_project/ir_files"
output_dir = "/home/user/llvm_optimization_project/o3_optimized_files"

# Ensure output directory exists
os.makedirs(output_dir, exist_ok=True)

# Get all LLVM IR files
ir_files = [f for f in os.listdir(ir_dir) if f.endswith(".ll")]

# Apply O3 optimization
for ir_file in ir_files:
    input_path = os.path.join(ir_dir, ir_file)
    output_path = os.path.join(output_dir, ir_file)

    # Run opt with O3 optimization
    cmd = ["opt", "-O3", "-S", input_path, "-o", output_path]
    subprocess.run(cmd, check=True)

print(f"Optimization complete. Optimized files are in {output_dir}")
