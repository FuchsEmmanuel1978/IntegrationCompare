from pathlib import Path

from src.visualization import draw_all_packaging


def main():
    base_dir = Path(__file__).resolve().parent
    data_dir = base_dir / "data"
    output_dir = base_dir / "outputs" / "figures"

    files = draw_all_packaging(data_dir=data_dir, output_dir=output_dir)

    print("Packaging figures generated:")
    for file in files:
        print(f" - {file}")


if __name__ == "__main__":
    main()
