from pathlib import Path
from src.hb_hbm_cross_section import draw_hb_hbm_detail_from_json


def main():
    base_dir = Path(__file__).resolve().parent
    json_path = base_dir / "data" / "3d_hybrid_bonding_tsv.json"
    output_path = base_dir / "outputs" / "figures" / "hb_hbm_detail.png"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    draw_hb_hbm_detail_from_json(json_path, output_path)

    print(f"Generated: {output_path}")


if __name__ == "__main__":
    main()