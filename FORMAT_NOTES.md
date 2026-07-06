# Granite Docling DocTags Format Notes

Sources inspected before writing converter serialization code:

- Local checkpoint tokenizer/config: `model/ibm-granite/granite-docling-258M/tokenizer_config.json`, `tokenizer.json`, `special_tokens_map.json`, `preprocessor_config.json`, `processor_config.json`, `config.json`.
- Local generated Granite/SmolDocling examples under `dataset/KDoc-OCRBench-V2/**/{*.doctags,*.dt}`.
- Docling-core token source: https://raw.githubusercontent.com/docling-project/docling-core/main/docling_core/types/doc/tokens.py
- Docling-core labels source: https://raw.githubusercontent.com/docling-project/docling-core/main/docling_core/types/doc/labels.py
- OTSL paper: https://arxiv.org/abs/2305.03393
- SmolDocling paper describing DocTags as the page markup target: https://arxiv.org/abs/2503.11576

## Tokens confirmed

- Document wrapper: `<doctag>` and `</doctag>` are added special tokens in the local tokenizer at ids `100327` and `100328`.
- EOS: `special_tokens_map.json` defines EOS as `<|end_of_text|>` at id `100257`. Local generated `.doctags` files usually stop at `</doctag>` because they are decoded inference text; this converter writes the training target with `</doctag><|end_of_text|>`.
- Text elements: `<text>` and `</text>` are added special tokens at ids `100260` and `100317`. AIHub free text boxes are serialized as `<text><loc_x0><loc_y0><loc_x1><loc_y1>TEXT</text>`.
- Tables: `<otsl>` and `</otsl>` are added special tokens at ids `100297` and `100298`; local model outputs serialize tables as `<otsl><loc_x0><loc_y0><loc_x1><loc_y1>...OTSL...</otsl>`.
- OTSL table tags present in the local tokenizer and examples:
  - `<fcel>`: non-empty cell
  - `<ecel>`: empty cell
  - `<lcel>`: continuation from a cell on the left for colspan
  - `<ucel>`: continuation from a cell above for rowspan
  - `<xcel>`: two-dimensional extension cell
  - `<nl>`: row break
  - `<ched>` is also present in examples, but the converter uses `<fcel>` for all content cells because AIHub/Paddle inputs do not reliably label table header semantics.

## Location tokens and coordinate transform

- Docling-core dynamically defines location tokens as `<loc_N>`. Its default page dimension is `(500, 500)`, and `get_location_token` computes `round(rnorm * normalized_value)` clamped into `[0, rnorm - 1]`.
- The local Granite tokenizer does not store `<loc_N>` as added special tokens. It tokenizes them compositionally, for example `<loc_500>` tokenizes as `['<', 'loc', '_', '500', '>']`. This matches the local generated DocTags examples.
- This converter therefore uses a 500 by 500 location grid and clamps every coordinate into `[0, 499]`.
- Normalization uses the original image dimensions from AIHub label JSON (`images[0]["image.width"]`, `images[0]["image.height"]`). The Granite processor config has `do_resize=true`, `size.longest_edge=2048`, `max_image_size.longest_edge=512`, `do_image_splitting=true`, and `do_pad=true`. Because Docling-core location serialization normalizes page-space bboxes rather than post-resize pixel coordinates, the converter maps original image page coordinates directly to the 500-grid:
  - `loc_x = clamp(round(500 * x / image_width), 0, 499)`
  - `loc_y = clamp(round(500 * y / image_height), 0, 499)`

## Ordering rule

Each output line is one image. Elements are merged into a single DocTags sequence in deterministic reading order:

1. Build free AIHub text elements and Paddle table elements.
2. Consume any AIHub text whose center lies inside a Paddle table bbox; consumed text is used only for table cells.
3. Sort remaining free text and table elements by top-left `(y0, x0)`, then by element type (`text` before `table` for identical coordinates), then by stable source id/table index.

## Table structure and cell text policy

- Table structure comes from Paddle's `table_html`, parsed with `lxml.html`.
- Rowspan/colspan are expanded into a rectangular grid. Non-rectangular expansion is a conversion failure for that image.
- Paddle does not provide per-cell bboxes in the saved table metadata, so the converter derives approximate cell bboxes by uniformly partitioning the Paddle table bbox by expanded row/column slots and span extents.
- AIHub text inside a table bbox is matched to these derived cell bboxes by center containment first, then by IoU. AIHub text wins over Paddle cell text wherever a match exists.
- Cells without an AIHub match keep Paddle cell text and receive warning `paddle_text_only`.
- AIHub text inside a table bbox that matches no cell receives warning `unplaced_in_table` and is listed in the audit.
