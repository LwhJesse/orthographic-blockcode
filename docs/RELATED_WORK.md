# Related Work and Distinctions

This project touches several existing areas but is not identical to any of them.

## Text-entry research

Text-entry research studies how humans produce text with devices and interfaces. Common metrics include WPM, error rate, correction cost, and keystrokes per character. Orthographic BlockCode fits this broad area because the final question is whether a code table can reduce real input effort.

## Keyboard layout optimization

Keyboard layout optimization changes where characters are placed on physical keys. Orthographic BlockCode does not primarily move letters across keys. It maps orthographic units such as `tion`, `ee`, or `ing` to input codes.

## Autocomplete and prediction

Autocomplete predicts likely continuations from context. Orthographic BlockCode uses deterministic mappings and fixed candidate order. It can be evaluated without a language model.

## Text expansion

Text expansion maps memorized abbreviations to longer strings. Orthographic BlockCode works inside words by compressing recurring orthographic blocks.

## Stenography

Stenography and Plover use chorded input. Orthographic BlockCode uses ordinary sequential key events.

## Compression and coding theory

The project is related to coding theory because frequent units should receive shorter codes. It differs from ordinary compression because the code table must be typed by humans and decoded through candidate ranks, delimiters, and fallback paths.

## Shape-code input methods

Chinese shape-code input methods show that structural code tables can support blind typing. Orthographic BlockCode explores a different writing system and a different unit structure: Latin orthographic blocks rather than Chinese character components.
