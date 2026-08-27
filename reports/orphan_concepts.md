# Radici isolate di `desmos:FormalConstraintScheme`

78 concetti dello schema non hanno `skos:broader` **e** non sono `skos:broader`
di nessun altro concetto: non appartengono a nessuna gerarchia. Sono distinti
dai 12 concetti dichiarati `skos:hasTopConcept` (Task 2), che sono anch'essi
privi di `skos:broader` ma **hanno** figli — radici di alberi reali, non nodi
isolati.

Qui sotto sono raggruppati per prefisso lessicale ricorrente della
`skos:prefLabel@it` (prima parola dell'etichetta). È un **indice per la
lettura**, non una proposta di tassonomia: **nessun concetto di
raggruppamento è stato creato e nessun arco `skos:broader` è stato
aggiunto** — collocare questi 78 concetti in una gerarchia (se e come farlo)
è una decisione del curatore, fuori dallo scopo di questo task.

## Cluster candidati (prefisso condiviso da 2+ concetti)

### Rima* (6)
- Rima alternata — `desmos:alternating_rhyme`
- Rima incrociata — `desmos:enclosed_rhyme`
- Rima invertita — `desmos:inverted_rhyme`
- Rima non ripetuta — `desmos:non_repeating_rhyme`
- Rima sdrucciola — `desmos:sdrucciola_rhyme`
- Rima tronca — `desmos:truncated_rhyme`

### Endecasillabo* (3)
- Endecasillabo — `desmos:hendecasyllable`
- Endecasillabo giambico — `desmos:iambic_hendecasyllable`
- Endecasillabo sdrucciolo — `desmos:sdrucciola_hendecasyllable`

### Lunghezza* (3)
- Lunghezza del testo fissa — `desmos:fixed_text_length`
- Lunghezza del titolo fissa — `desmos:fixed_title_length`
- Lunghezza di parola indicizzata alla data — `desmos:date_indexed_word_length`

### Testo* (3)
- Testo autodescrittivo numerico — `desmos:enumerating_text`
- Testo locuzionale semiautomatico — `desmos:semi_automatic_locutionary_text`
- Testo perimetrato in figura — `desmos:figure_bounded_text`

### Vincolo* (2)
- Vincolo quantitativo di supporto — `desmos:page_format`
- Vincolo sul set sillabico — `desmos:syllabic_set_constraint`

*(`Lessico *` — citato come esempio nella spec — non compare qui: quei
concetti hanno già un genitore, `desmos:lexicographic_marker_constraint`, uno
dei 12 top concept del Task 2, quindi non sono fra le radici isolate.)*

## Nessun prefisso ricorrente (61)

- Acrobistico — `desmos:acrobistic`
- Acronimo — `desmos:acronym`
- Alfabeto raffigurato — `desmos:figured_alphabet`
- Allitterazione — `desmos:alliteration`
- Anafora visiva — `desmos:visual_anaphora`
- Anagrafia — `desmos:anagraphy`
- Anagramma — `desmos:anagram`
- Bisenso — `desmos:bisenso`
- Boule de neige — `desmos:boule_de_neige`
- Calcolo dei numeri incorporati — `desmos:embedded_numeral_calculus`
- Calligramma — `desmos:calligram`
- Catena di combinazioni enigmistiche — `desmos:enigmatic_transformation_chain`
- Centone — `desmos:cento`
- Corona di sonetti — `desmos:crown_of_sonnets`
- Distico — `desmos:distich`
- Espansioni sillabiche — `desmos:syllable_expansion`
- Eterogramma — `desmos:heterogram`
- Frammentazione — `desmos:fragmentation`
- Frase obbligata — `desmos:mandatory_sentence`
- Gruppo letterale triripetuto — `desmos:triple_letter_cluster`
- Isovocalismo — `desmos:isovocalism`
- Lacuna lessicale — `desmos:lexical_gap`
- Lettere rubate — `desmos:stolen_letters`
- Liposillabismo metrico — `desmos:metric_liposyllabism`
- Lottomatica combinatoria — `desmos:combinatorial_lottery`
- Metagramma — `desmos:metagram`
- Mitografemi — `desmos:mythographic_units`
- Monorima — `desmos:monorhyme`
- Morale elementare — `desmos:morale_elementaire`
- Norme tipografiche — `desmos:typographic_constraints`
- Numero ricavato dalla figura — `desmos:figure_derived_count`
- Omofonia — `desmos:homophony`
- Omonimia — `desmos:homonymy`
- Oscillazione della lunghezza delle parole — `desmos:word_length_oscillation`
- Ottava — `desmos:octave`
- Palindromo — `desmos:palindrome`
- Panvocalismo — `desmos:panvocalism`
- Parola contenuta — `desmos:buried_word`
- Paronomasia — `desmos:paronomasia`
- Pentamini — `desmos:pentomino_segmentation`
- Permutazione — `desmos:permutation`
- Proverbio incastonato — `desmos:embedded_proverb`
- Quartina — `desmos:quatrain`
- Realizzazione autografa — `desmos:handwritten_realization`
- Rebus — `desmos:rebus`
- Recensione preventiva — `desmos:preventive_review`
- Rigrafia — `desmos:regraphing`
- Riscrittura antonimica — `desmos:antonymic_rewriting`
- Scrittura eterolessicale — `desmos:heterolexical_writing`
- Serie di parole terminali — `desmos:terminal_word_series`
- Sestina — `desmos:sestina`
- Settenario — `desmos:septenary`
- Slittamento proverbiale — `desmos:proverbial_shift`
- Solfeix — `desmos:solfeix`
- Sonetto classico — `desmos:classical_sonnet`
- Tanka — `desmos:tanka`
- Tautogramma — `desmos:tautogram`
- Tempo obbligato — `desmos:temporal_constraint`
- Terzina — `desmos:tercet`
- Traduzione omografica — `desmos:homographic_translation`
- Verso condizionato — `desmos:prescribed_line_frame`

## Totale

17 concetti in 5 cluster candidati + 61 senza prefisso ricorrente = **78**.
