import os
import re
import pandas as pd
from collections import defaultdict

# Update to use absolute path
ir_files_path = "/home/user/llvm_optimization_project/o3_optimized_files"

class IRFeatureExtractor:
    def __init__(self, ir_file_path):
        with open(ir_file_path, 'r') as f:
            self.ir_content = f.read()
        self.functions = self._split_into_functions()
        
    def _split_into_functions(self):
        """Split IR file into functions."""
        # Split on 'define' keyword which starts function definitions
        function_pattern = r'define.*{.*?}(?=\n\s*(?:define|\Z))'
        functions = re.finditer(function_pattern, self.ir_content, re.DOTALL)
        return {self._get_function_name(f.group(0)): f.group(0) for f in functions}
    
    def _get_function_name(self, function_text):
        """Extract function name from function definition."""
        match = re.search(r'@([\w.]+)', function_text)
        return match.group(1) if match else "unknown"
    
    def _get_basic_blocks(self, function_text):
        """Split function into basic blocks."""
        blocks = re.split(r'\n\s*[\w.]+:', function_text)[1:]
        return [block.strip() for block in blocks if block.strip()]

    def get_instruction_per_block(self, function_text):
        """Feature 1: Calculate average instructions per block."""
        blocks = self._get_basic_blocks(function_text)
        if not blocks:
            return 0
        
        total_instructions = sum(len(re.findall(r'\n\s+[^;}]', block)) for block in blocks)
        return total_instructions / len(blocks)
    
    def get_successor_per_block(self, function_text):
        """Feature 2: Calculate average successors per block."""
        blocks = self._get_basic_blocks(function_text)
        if not blocks:
            return 0
            
        total_successors = sum(len(re.findall(r'br\s+(?:label|i1)', block)) for block in blocks)
        return total_successors / len(blocks)

    def get_loop_features(self, function_text):
        """Extract loop-related features."""
        # Find all loops using the 'loop:' metadata in LLVM IR
        loop_headers = re.findall(r'loop:.*\n', function_text)
        if not loop_headers:
            return {
                'avg_nested_loop_level': 0,
                'instr_per_loop': 0,
                'block_with_multiple_succ_per_loop': 0,
                'max_loop_depth': 0,
                'num_callsite_in_loop': 0
            }
        
        # Extract loop depths and instructions
        loop_depths = []
        total_instructions = 0
        multiple_succ_blocks = 0
        callsites_in_loop = 0
        
        for loop in loop_headers:
            # Get loop depth from metadata
            depth = len(re.findall(r'loop:', loop))
            loop_depths.append(depth)
            
            # Count instructions in loop body
            loop_body = self._get_loop_body(loop, function_text)
            total_instructions += len(re.findall(r'\n\s+[^;}]', loop_body))
            
            # Count blocks with multiple successors in loop
            multiple_succ_blocks += len(re.findall(r'br\s+i1', loop_body))
            
            # Count call instructions in loop
            callsites_in_loop += len(re.findall(r'\bcall\b', loop_body))
        
        return {
            'avg_nested_loop_level': sum(loop_depths) / len(loop_depths) if loop_depths else 0,
            'instr_per_loop': total_instructions / len(loop_headers) if loop_headers else 0,
            'block_with_multiple_succ_per_loop': multiple_succ_blocks / len(loop_headers) if loop_headers else 0,
            'max_loop_depth': max(loop_depths) if loop_depths else 0,
            'num_callsite_in_loop': callsites_in_loop
        }

    def _get_loop_body(self, loop_header, function_text):
        """Helper method to extract loop body"""
        try:
            start_idx = function_text.find(loop_header)
            if start_idx == -1:
                return ""
            
            # Find matching closing brace
            brace_count = 1
            end_idx = start_idx
            while brace_count > 0 and end_idx < len(function_text) - 1:
                end_idx += 1
                if function_text[end_idx] == '{':
                    brace_count += 1
                elif function_text[end_idx] == '}':
                    brace_count -= 1
            
            return function_text[start_idx:end_idx + 1]
        except Exception as e:
            print(f"Error in _get_loop_body: {str(e)}")
            return ""

    def get_call_graph_features(self, function_text):
        """Extract call graph-related features."""
        try:
            # Get all call instructions
            calls = re.findall(r'call\s+.*@([\w.]+)', function_text)
            
            # Check recursion
            function_name = self._get_function_name(function_text)
            is_recursive = function_name in calls
            
            # Get call usage (number of times function is called)
            call_usage = len(calls)
            
            # Get entry block frequency from metadata
            entry_freq = 0
            entry_block_match = re.search(r'!prof ![\d]+.*![\d]+', function_text)
            if entry_block_match:
                freq_match = re.search(r'count:(\d+)', entry_block_match.group(0))
                if freq_match:
                    entry_freq = int(freq_match.group(1))
            
            # Get max callsite block frequency
            block_freqs = []
            for block in self._get_basic_blocks(function_text):
                freq_match = re.search(r'!prof ![\d]+.*count:(\d+)', block)
                if freq_match:
                    block_freqs.append(int(freq_match.group(1)))
            
            max_callsite_freq = max(block_freqs) if block_freqs else 0
            
            # Calculate caller height
            caller_height = self._calculate_caller_height(function_text)
            
            return {
                'caller_height': caller_height,
                'call_usage': call_usage,
                'is_recursive': 1 if is_recursive else 0,
                'entry_block_freq': entry_freq,
                'max_callsite_block_freq': max_callsite_freq
            }
        except Exception as e:
            print(f"Error in get_call_graph_features: {str(e)}")
            return {
                'caller_height': 0,
                'call_usage': 0,
                'is_recursive': 0,
                'entry_block_freq': 0,
                'max_callsite_block_freq': 0
            }

    def _calculate_caller_height(self, function_text):
        """Calculate the depth of function in call graph"""
        try:
            height = 0
            current_func = function_text
            visited = set()  # Prevent infinite loops
            
            while True:
                caller = self._find_caller(current_func)
                if not caller or self._get_function_name(caller) in visited:
                    break
                height += 1
                visited.add(self._get_function_name(current_func))
                current_func = caller
                
            return height
        except Exception as e:
            print(f"Error in _calculate_caller_height: {str(e)}")
            return 0

    def _find_caller(self, function_text):
        """Find the caller of current function"""
        try:
            function_name = self._get_function_name(function_text)
            for func in self.functions.values():
                if re.search(f'call.*@{function_name}', func):
                    return func
            return None
        except Exception as e:
            print(f"Error in _find_caller: {str(e)}")
            return None

    def get_calls_no(self, function_text):
        """Feature 6: Count number of call instructions."""
        return len(re.findall(r'\bcall\b', function_text))
    
    def is_local(self, function_text):
        """Feature 7: Check if function is local."""
        return 1 if 'internal' in function_text.split('\n')[0] else 0
    
    def count_specific_instructions(self, function_text, instruction):
        """Count specific instruction types (Features 16-20)."""
        return len(re.findall(fr'\b{instruction}\b', function_text))

    def extract_all_features(self):
        """Extract all features for all functions."""
        features = []
        
        for func_name, func_text in self.functions.items():
            # Basic features
            feature_dict = {
                'function_name': func_name,
                'instruction_per_block': self.get_instruction_per_block(func_text),
                'successor_per_block': self.get_successor_per_block(func_text),
                'calls_no': self.get_calls_no(func_text),
                'is_local': self.is_local(func_text),
                'ret_count': self.count_specific_instructions(func_text, 'ret'),
                'fmul_count': self.count_specific_instructions(func_text, 'fmul'),
                'fdiv_count': self.count_specific_instructions(func_text, 'fdiv'),
                'fadd_count': self.count_specific_instructions(func_text, 'fadd'),
                'fsub_count': self.count_specific_instructions(func_text, 'fsub')
            }
            
            # Add loop features
            loop_features = self.get_loop_features(func_text)
            feature_dict.update(loop_features)
            
            # Add call graph features
            call_features = self.get_call_graph_features(func_text)
            feature_dict.update(call_features)
            
            features.append(feature_dict)
        
        return pd.DataFrame(features)

def process_directory(directory_path):
    """Process all IR files in a directory."""
    all_features = []
    files = [f for f in os.listdir(directory_path) if f.endswith('.ll')]
    print(f"Found {len(files)} .ll files")
    
    for filename in files:
        file_path = os.path.join(directory_path, filename)
        print(f"\nProcessing file: {filename}")
        try:
            extractor = IRFeatureExtractor(file_path)
            features_df = extractor.extract_all_features()
            features_df['source_file'] = filename
            all_features.append(features_df)
            print(f"Successfully processed {filename}")
        except Exception as e:
            print(f"Error processing {filename}: {str(e)}")
    
    if not all_features:
        raise Exception("No files were successfully processed")
        
    return pd.concat(all_features, ignore_index=True)

if __name__ == "__main__":
    print(f"Looking for files in: {ir_files_path}")
    
    if os.path.exists(ir_files_path):
        print("\nFound directory. Checking for .ll files...")
        ll_files = [f for f in os.listdir(ir_files_path) if f.endswith('.ll')]
        print(f"Found {len(ll_files)} .ll files:")
        for file in ll_files:
            print(f"- {file}")
        
        try:
            # Process files
            results = process_directory(ir_files_path)
            
            # Save results
            output_file = "mlgoperf_features.csv"
            results.to_csv(output_file, index=False)
            print(f"\nFeatures extracted and saved to {output_file}")
            print(f"Total functions processed: {len(results)}")
            
            # Show sample of results
            print("\nSample of extracted features:")
            print(results.head())
            
        except Exception as e:
            print(f"Error during processing: {str(e)}")
    else:
        print(f"Error: Directory {ir_files_path} not found. Please check the path.")