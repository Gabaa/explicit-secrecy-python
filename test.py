"""Run each example compare the actual output to the expected output."""

from pathlib import Path
import analysis


def compare_output_to_expected(output: str, expected_file: Path, i: int):
    with open(expected_file, 'r') as f:
        expected = f.read()

    if output == expected:
        print(f'✅ examples/example{i}.py')
    else:
        print(f'❌ examples/example{i}.py')


def run_all_examples():
    i = 1
    while True:
        example_path = Path('examples', f'example{i}.py')
        if not example_path.exists():
            break

        expected_output_path = Path('expected-outputs', f'example{i}.txt')

        output = ''
        for s in analysis.run_analysis(str(example_path), False):
            output += s + '\n'

        compare_output_to_expected(output, expected_output_path, i)

        i += 1


if __name__ == '__main__':
    run_all_examples()
