"""Run each example compare the actual output to the expected output."""

import traceback
from pathlib import Path

import analysis


def compare_output_to_expected(output: str, expected_file: Path, example_path: Path) -> int:
    if not expected_file.exists():
        print(f"🟡 {example_path}: File {expected_file} does not exist")
        return False

    with open(expected_file, 'r') as f:
        expected = f.read()

    if output == expected:
        print(f'🟢 {example_path}')
        return True
    else:
        print(f'🔴 {example_path}:\n')
        print(f'Expected:\n{expected}')
        print(f'Actual:\n{output}')
        return False


def run_all_examples():
    accepted = 0

    i = 1
    while True:
        example_path = Path('examples', f'example{i}.py')
        if not example_path.exists():
            break

        expected_output_path = Path('expected-outputs', f'example{i}.txt')

        try:
            analysis_output = analysis.run_analysis(str(example_path), False)
            output = ''
            for s in analysis_output:
                output += s + '\n'
            result = compare_output_to_expected(
                output, expected_output_path, example_path)
            if result:
                accepted += 1
        except:
            print(f"🟡 {example_path}: Could not run analysis:\n")
            traceback.print_exc()
            print()

        i += 1

    print(f'Accepted: [{accepted}/{i - 1}]')


if __name__ == '__main__':
    run_all_examples()
