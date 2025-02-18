import os
import subprocess
from pathlib import Path
import logging
from tqdm import tqdm

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DirectInliner:
    def __init__(self):
        self.input_dir = Path("/home/user/llvm_optimization_project/ir_files")  # Changed to original IR files
        self.output_dir = Path("/home/user/llvm_optimization_project/direct_inlined_files")
        self.opt_path = Path("/home/user/llvm_optimization_project/llvm_build/bin/opt")

    def process_file(self, input_file: Path, output_file: Path):
        try:
            cmd = [
                str(self.opt_path),
                "-passes=scc-oz-module-inliner",
                str(input_file),
                "-o",
                str(output_file)
            ]
            
            logger.debug(f"Running command: {' '.join(map(str, cmd))}")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                logger.error(f"Error processing {input_file}")
                logger.error(f"Error message: {result.stderr}")
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"Exception while processing {input_file}: {str(e)}")
            return False

    def process_files(self):
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        ir_files = list(self.input_dir.glob("*.ll"))
        logger.info(f"Found {len(ir_files)} files to process")
        
        success_count = 0
        failed_files = []
        
        for ir_file in tqdm(ir_files, desc="Applying direct inlining"):
            output_file = self.output_dir / f"{ir_file.stem}_inlined.ll"
            if self.process_file(ir_file, output_file):
                success_count += 1
            else:
                failed_files.append(ir_file.name)

        logger.info(f"\nInlining Summary:")
        logger.info(f"Successfully processed: {success_count}/{len(ir_files)} files")
        if failed_files:
            logger.info("\nFailed files:")
            for file in failed_files:
                logger.info(f"- {file}")

def main():
    try:
        inliner = DirectInliner()
        inliner.process_files()
    except Exception as e:
        logger.error(f"Error during inlining process: {str(e)}")

if __name__ == "__main__":
    main()