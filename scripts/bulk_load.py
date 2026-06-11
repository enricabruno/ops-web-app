#!/usr/bin/env python3
"""
Script per il caricamento massivo di file RDF in GraphDB.

Uso:
    python bulk_load.py --file path/to/file.rdf --format turtle
    python bulk_load.py --directory data/rdf/ --format rdfxml
"""

import os
import sys
import argparse
from pathlib import Path
from SPARQLWrapper import SPARQLWrapper, POST, DIGEST
from dotenv import load_dotenv
import requests

# Carica variabili d'ambiente
load_dotenv()

GRAPHDB_URL = os.getenv('GRAPHDB_URL', 'http://localhost:7200/repositories')
REPOSITORY_ID = os.getenv('REPOSITORY_ID', 'your_repository_name')


def upload_rdf_file(file_path, rdf_format='turtle'):
    """
    Carica un file RDF in GraphDB.

    Args:
        file_path (str): Percorso del file RDF
        rdf_format (str): Formato RDF (turtle, rdfxml, n3, ntriples, etc.)

    Returns:
        bool: True se il caricamento è riuscito, False altrimenti
    """
    endpoint = f"{GRAPHDB_URL}/{REPOSITORY_ID}/statements"

    # Mapping formati RDF -> MIME types
    format_mapping = {
        'turtle': 'text/turtle',
        'ttl': 'text/turtle',
        'rdfxml': 'application/rdf+xml',
        'rdf': 'application/rdf+xml',
        'n3': 'text/n3',
        'ntriples': 'application/n-triples',
        'nt': 'application/n-triples',
        'jsonld': 'application/ld+json',
    }

    content_type = format_mapping.get(rdf_format.lower(), 'text/turtle')

    try:
        with open(file_path, 'rb') as f:
            data = f.read()

        headers = {
            'Content-Type': content_type
        }

        response = requests.post(endpoint, data=data, headers=headers)

        if response.status_code in [200, 201, 204]:
            print(f"✓ Caricato con successo: {file_path}")
            return True
        else:
            print(f"✗ Errore nel caricamento di {file_path}: {response.status_code}")
            print(f"  Dettagli: {response.text}")
            return False

    except FileNotFoundError:
        print(f"✗ File non trovato: {file_path}")
        return False
    except Exception as e:
        print(f"✗ Errore durante il caricamento di {file_path}: {str(e)}")
        return False


def bulk_load_directory(directory_path, rdf_format='turtle'):
    """
    Carica tutti i file RDF da una directory in GraphDB.

    Args:
        directory_path (str): Percorso della directory
        rdf_format (str): Formato RDF dei file

    Returns:
        tuple: (successi, fallimenti)
    """
    directory = Path(directory_path)

    if not directory.exists() or not directory.is_dir():
        print(f"✗ Directory non valida: {directory_path}")
        return (0, 0)

    # Estensioni comuni per file RDF
    extensions = {
        'turtle': ['.ttl', '.turtle'],
        'rdfxml': ['.rdf', '.owl', '.xml'],
        'n3': ['.n3'],
        'ntriples': ['.nt'],
        'jsonld': ['.jsonld']
    }

    valid_extensions = extensions.get(rdf_format.lower(), ['.ttl', '.rdf'])

    files = [f for f in directory.iterdir()
             if f.is_file() and f.suffix.lower() in valid_extensions]

    if not files:
        print(f"✗ Nessun file RDF trovato in {directory_path}")
        return (0, 0)

    print(f"\nTrovati {len(files)} file da caricare...")
    print(f"Endpoint: {GRAPHDB_URL}/{REPOSITORY_ID}\n")

    success_count = 0
    failure_count = 0

    for file_path in files:
        if upload_rdf_file(file_path, rdf_format):
            success_count += 1
        else:
            failure_count += 1

    return (success_count, failure_count)


def main():
    parser = argparse.ArgumentParser(
        description='Carica file RDF in GraphDB in modalità bulk'
    )

    parser.add_argument(
        '--file',
        type=str,
        help='Percorso del singolo file RDF da caricare'
    )

    parser.add_argument(
        '--directory',
        type=str,
        help='Percorso della directory contenente file RDF'
    )

    parser.add_argument(
        '--format',
        type=str,
        default='turtle',
        choices=['turtle', 'ttl', 'rdfxml', 'rdf', 'n3', 'ntriples', 'nt', 'jsonld'],
        help='Formato dei file RDF (default: turtle)'
    )

    args = parser.parse_args()

    if not args.file and not args.directory:
        parser.error("Specificare almeno --file o --directory")

    print("=" * 60)
    print("GraphDB Bulk Load Script")
    print("=" * 60)
    print(f"Repository: {REPOSITORY_ID}")
    print(f"Endpoint: {GRAPHDB_URL}")
    print(f"Formato: {args.format}")
    print("=" * 60)

    if args.file:
        success = upload_rdf_file(args.file, args.format)
        if success:
            print("\n✓ Caricamento completato con successo")
            sys.exit(0)
        else:
            print("\n✗ Caricamento fallito")
            sys.exit(1)

    elif args.directory:
        success_count, failure_count = bulk_load_directory(args.directory, args.format)

        print("\n" + "=" * 60)
        print("Riepilogo:")
        print(f"  ✓ Successi: {success_count}")
        print(f"  ✗ Fallimenti: {failure_count}")
        print("=" * 60)

        if failure_count > 0:
            sys.exit(1)
        else:
            print("\n✓ Tutti i file sono stati caricati con successo")
            sys.exit(0)


if __name__ == '__main__':
    main()
