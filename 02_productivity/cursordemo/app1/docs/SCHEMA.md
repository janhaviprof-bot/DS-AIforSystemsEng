# Table schema

The dashboard displays a **flat character table** derived from SWAPI People resources. Array fields (films, species, vehicles, starships) are not shown in the table; only scalar and single-reference fields are included.

## Columns

| Column       | Type    | Source       | Description |
|-------------|---------|--------------|-------------|
| `name`      | string  | `name`       | Character name. |
| `height`    | numeric | `height`     | Height in cm. Parsed from string; invalid → `NA`. |
| `mass`      | numeric | `mass`       | Mass in kg. Parsed from string; invalid → `NA`. |
| `hair_color`| string  | `hair_color` | Hair color; `"unknown"` if missing/n/a. |
| `skin_color`| string  | `skin_color` | Skin color; `"unknown"` if missing/n/a. |
| `eye_color` | string  | `eye_color`  | Eye color; `"unknown"` if missing/n/a. |
| `birth_year`| string  | `birth_year` | In-universe year (e.g. `19BBY`, `unknown`). |
| `gender`    | string  | `gender`     | Gender; `"unknown"` if missing/n/a. |
| `homeworld` | string  | `homeworld`  | Planet resource URL. |
| `url`       | string  | `url`        | This person’s SWAPI resource URL. |

## Display names (in DT)

The DataTable shows user-friendly headers, e.g. **Name**, **Height_cm**, **Mass_kg**, **Hair color**, **Skin color**, **Eye color**, **Birth year**, **Gender**, **Homeworld**, **URL**.

## Trait frequency plot

The plot aggregates one **trait** at a time (same field names as above: `gender`, `eye_color`, `hair_color`, `skin_color`, `birth_year`). Each distinct value is counted; missing/n/a are coalesced to `"unknown"` before counting.
