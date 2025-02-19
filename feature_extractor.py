import os
import llvmlite.binding as llvm
import pandas as pd
from collections import defaultdict

# Initialize LLVM
llvm.initialize()
llvm.initialize_native_target()
llvm.initialize_native_asmprinter()

# Update to use absolute path
ir_files_path = "/home/user/llvm_optimization_project/o3_optimized_files"

class IRFeatureExtractor:
    def __init__(self, ir_file_path):
        # Parse IR file
        with open(ir_file_path, 'r') as f:
            ir_content = f.read()
        
        # Initialize LLVM module
        self.module = llvm.parse_assembly(ir_content)
        self.module.verify()  # Verify module is valid
        
    def get_instruction_per_block(self, function):
        """Calculate average instructions per block."""
        total_instructions = 0
        num_blocks = 0
        
        for block in function.blocks:
            total_instructions += len(list(block.instructions))
            num_blocks += 1
            
        return total_instructions / num_blocks if num_blocks > 0 else 0
    
    def get_successor_per_block(self, function):
        """Calculate average successors per block."""
        total_successors = 0
        num_blocks = 0
        
        for block in function.blocks:
            for instr in block.instructions:
                if instr.opcode == 'br':
                    # Check instruction text for number of successors
                    instr_str = str(instr)
                    total_successors += 2 if 'i1' in instr_str else 1
            num_blocks += 1
            
        return total_successors / num_blocks if num_blocks > 0 else 0
    
    def get_loop_info(self, function):
        """Extract loop-related information."""
        nested_level = 0
        instr_in_loops = 0
        multi_succ_blocks = 0
        max_depth = 0
        callsites_in_loop = 0
        
        # Look for loop metadata in function
        for block in function.blocks:
            for instr in block.instructions:
                if 'loop' in str(instr):
                    nested_level += 1
                    instr_in_loops += len(list(block.instructions))
                    
                    # Check for multiple successors in loop blocks
                    if instr.opcode == 'br' and 'i1' in str(instr):
                        multi_succ_blocks += 1
                        
                    # Check for calls in loop blocks
                    if instr.opcode == 'call':
                        callsites_in_loop += 1
        
        max_depth = nested_level  # Simplified for now
        
        return {
            'AvgNestedLoopLevel': nested_level,
            'InstrPerLoop': instr_in_loops,
            'BlockWithMultipleSuccecorsPerLoop': multi_succ_blocks,
            'MaxLoopDepth': max_depth,
            'NumCallsiteInLoop': callsites_in_loop
        }
    
    def get_call_info(self, function):
        """Extract call-related information."""
        calls_no = 0
        is_recursive = 0
        call_usage = 0
        
        function_name = function.name
        for block in function.blocks:
            for instr in block.instructions:
                if instr.opcode == 'call':
                    calls_no += 1
                    called_func = str(instr).split('@')[-1].split()[0]
                    if called_func == function_name:
                        is_recursive = 1
                    call_usage += 1
        
        return {
            'CallsNo': calls_no,
            'IsRecursive': is_recursive,
            'CallUsage': call_usage
        }
    
    def get_memory_operations(self, function):
        """Count memory operations."""
        load_count = 0
        store_count = 0
        alloca_count = 0
        
        for block in function.blocks:
            for instr in block.instructions:
                if instr.opcode == 'load':
                    load_count += 1
                elif instr.opcode == 'store':
                    store_count += 1
                elif instr.opcode == 'alloca':
                    alloca_count += 1
        
        return {
            'load_count': load_count,
            'store_count': store_count,
            'alloca_count': alloca_count
        }
    
    def get_branch_info(self, function):
        """Count branch instructions."""
        conditional = 0
        unconditional = 0
        
        for block in function.blocks:
            for instr in block.instructions:
                if instr.opcode == 'br':
                    if 'i1' in str(instr):
                        conditional += 1
                    else:
                        unconditional += 1
        
        return {
            'conditional_branch_count': conditional,
            'unconditional_branch_count': unconditional
        }
    
    def count_floating_point_ops(self, function):
        """Count floating point operations."""
        counts = {
            'NoOfFadd': 0,
            'NoOfFsub': 0,
            'NoOfFmul': 0,
            'NoOfFdiv': 0
        }
        
        for block in function.blocks:
            for instr in block.instructions:
                if instr.opcode in ['fadd', 'fsub', 'fmul', 'fdiv']:
                    counts[f'NoOf{instr.opcode.capitalize()}'] += 1
        
        return counts
    
    def extract_file_features(self):
        """Extract features at file level."""
        # Initialize feature dictionary
        features = {
            'InstructionPerBlock': 0,
            'SuccessorPerBlock': 0,
            'AvgNestedLoopLevel': 0,
            'InstrPerLoop': 0,
            'BlockWithMultipleSuccecorsPerLoop': 0,
            'CallsNo': 0,
            'IsLocal': 0,
            'MaxLoopDepth': 0,
            'MaxDomTreeLevel': 0,
            'CallerHeight': 0,
            'CallUsage': 0,
            'IsRecursive': 0,
            'NumCallsiteInLoop': 0,
            'EntryBlockFreq': 0,
            'MaxCallsiteBlockFreq': 0,
            'NoOfRet': 0,
            'NoOfFmul': 0,
            'NoOfFdiv': 0,
            'NoOfFadd': 0,
            'NoOfFsub': 0,
            'load_count': 0,
            'store_count': 0,
            'alloca_count': 0,
            'conditional_branch_count': 0,
            'unconditional_branch_count': 0
        }
        
        # Count functions for averaging
        function_count = 0
        
        # Process each function
        for function in self.module.functions:
            if not function.blocks:  # Skip declarations
                continue
                
            function_count += 1
            
            # Basic block features
            features['InstructionPerBlock'] += self.get_instruction_per_block(function)
            features['SuccessorPerBlock'] += self.get_successor_per_block(function)
            
            # Loop features
            loop_info = self.get_loop_info(function)
            for key, value in loop_info.items():
                features[key] += value
            
            # Call features
            call_info = self.get_call_info(function)
            for key, value in call_info.items():
                features[key] += value
            
            # Memory operations
            mem_ops = self.get_memory_operations(function)
            for key, value in mem_ops.items():
                features[key] += value
            
            # Branch information
            branch_info = self.get_branch_info(function)
            for key, value in branch_info.items():
                features[key] += value
            
            # Floating point operations
            fp_ops = self.count_floating_point_ops(function)
            for key, value in fp_ops.items():
                features[key] += value
        
        # Calculate averages for per-function metrics
        if function_count > 0:
            for key in ['InstructionPerBlock', 'SuccessorPerBlock', 'AvgNestedLoopLevel']:
                features[key] /= function_count
        
        return features

def process_directory(directory_path):
    """Process all IR files in directory."""
    all_features = []
    files = [f for f in os.listdir(directory_path) if f.endswith('.ll')]
    print(f"Found {len(files)} .ll files")
    
    for filename in files:
        file_path = os.path.join(directory_path, filename)
        print(f"\nProcessing file: {filename}")
        try:
            extractor = IRFeatureExtractor(file_path)
            features = extractor.extract_file_features()
            features['source_file'] = filename
            all_features.append(features)
            print(f"Successfully processed {filename}")
        except Exception as e:
            print(f"Error processing {filename}: {str(e)}")
    
    return pd.DataFrame(all_features)

if __name__ == "__main__":
    print(f"Looking for files in: {ir_files_path}")
    
    if os.path.exists(ir_files_path):
        try:
            # Process files
            results = process_directory(ir_files_path)
            
            # Save results
            output_file = "mlgoperf_features.csv"
            results.to_csv(output_file, index=False)
            print(f"\nFeatures extracted and saved to {output_file}")
            print(f"Total files processed: {len(results)}")
            
            # Show sample of results
            print("\nSample of extracted features:")
            print(results.head())
            
        except Exception as e:
            print(f"Error during processing: {str(e)}")
    else:
        print(f"Error: Directory {ir_files_path} not found. Please check the path.")