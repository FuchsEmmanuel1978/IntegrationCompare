# Integration Compare

Petit projet Python pour comparer des scénarios d'intégration avancée :

- 2.0D organique / SiP
- 2.5D interposeur silicium TSV
- 3D hybrid bonding + TSV

Le but est de comparer rapidement :

- coût brut
- coût corrigé du yield
- CO2e brut
- CO2e corrigé du yield
- énergie process
- bande passante
- énergie par bit
- score performance relatif

## Lancer le calcul

Depuis le dossier du projet :

```bash
python run_compare.py
```

Le script écrit aussi :

```text
outputs/results.csv
```

## Structure

```text
integration_compare/
├── data/
│   ├── constants.json
│   ├── 2_0d_organic.json
│   ├── 2_5d_tsv_interposer.json
│   └── 3d_hybrid_bonding_tsv.json
├── src/
│   ├── loader.py
│   ├── cost_model.py
│   ├── lca_model.py
│   ├── performance_model.py
│   ├── yield_model.py
│   └── compare.py
├── outputs/
├── notebooks/
└── run_compare.py
```

## Important

Les chiffres fournis sont des hypothèses de travail pour structurer le modèle.
Ils doivent être remplacés par tes données internes, fournisseurs, publications ou hypothèses validées.

Pour un usage professionnel, garde toujours dans le JSON :

- la source de chaque hypothèse
- la date
- le niveau de confiance
- le propriétaire de l'hypothèse

Une évolution naturelle serait d'ajouter un champ `assumptions` ou `sources` à chaque étape process.


## Generate packaging cross-section images

This project also includes a Matplotlib-based visualization script:

```bash
python generate_packaging_views.py
```

Generated images are written to:

```text
outputs/figures/
├── packaging_2d_sip.png
├── packaging_25d_tsv_interposer.png
└── packaging_3d_hybrid_bonding_tsv.png
```

The drawings are generated from the JSON fields:

- `integration_type`
- `geometry.package_area_mm2`
- `geometry.rdl_layers`
- `geometry.interconnect_pitch_um`
- `geometry.tsv_count`
- `performance_model.bandwidth_tb_s`
- `performance_model.energy_pj_per_bit`
- `performance_model.thermal_resistance_k_per_w`

You can tune the JSON values and regenerate the images.
