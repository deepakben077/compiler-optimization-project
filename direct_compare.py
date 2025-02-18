import os
from pathlib import Path
import logging
from tabulate import tabulate
from tqdm import tqdm

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DirectComparator:
    def __init__(self):
        self.project_dir = Path("/home/user/llvm_optimization_project")
        self.original_dir = self.project_dir / "ir_files"
        self.inlined_dir = self.project_dir / "direct_inlined_files"

    def get_file_size(self, file_path: Path) -> int:
        return file_path.stat().st_size if file_path.exists() else 0

    def format_size(self, size_in_bytes: int) -> str:
        return f"{size_in_bytes/1024:.2f}KB"

    def calculate_percentage_diff(self, original: int, modified: int) -> str:
        if original == 0:
            return "N/A"
        return f"{((modified - original) / original) * 100:.2f}%"

    def analyze_files(self):
        original_files = list(self.original_dir.glob("*.ll"))
        comparisons = []

        for orig_file in tqdm(original_files, desc="Analyzing files"):
            base_name = orig_file.stem
            inlined_file = self.inlined_dir / f"{base_name}_inlined.ll"

            orig_size = self.get_file_size(orig_file)
            inlined_size = self.get_file_size(inlined_file)
            size_diff = self.calculate_percentage_diff(orig_size, inlined_size)

            comparisons.append([
                base_name,
                self.format_size(orig_size),
                self.format_size(inlined_size),
                size_diff
            ])

        # Sort by difference percentage
        comparisons.sort(key=lambda x: float(x[3].rstrip('%')) if x[3] != "N/A" else 0)

        print("\n=== Top 10 Most Reduced Files ===")
        print(tabulate(
            comparisons[:10],
            headers=['File', 'Original', 'Inlined', 'Difference %'],
            tablefmt='pipe'
        ))

        print("\n=== Bottom 10 Least Reduced Files ===")
        print(tabulate(
            comparisons[-10:],
            headers=['File', 'Original', 'Inlined', 'Difference %'],
            tablefmt='pipe'
        ))

        # Calculate average reduction
        valid_diffs = [float(row[3].rstrip('%')) for row in comparisons if row[3] != "N/A"]
        avg_reduction = sum(valid_diffs) / len(valid_diffs) if valid_diffs else 0

        print("\n=== Summary Statistics ===")
        print(f"Average Size Reduction: {avg_reduction:.2f}%")
        print(f"Total Files Processed: {len(comparisons)}")

def main():
    try:
        comparator = DirectComparator()
        comparator.analyze_files()
    except Exception as e:
        logger.error(f"Error during comparison: {str(e)}")

if __name__ == "__main__":
    main()