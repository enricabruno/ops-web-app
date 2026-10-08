#!/bin/sh
# Ad ogni avvio ricrea da zero il repository "desmos" con i file RDF montati
# in /data, poi avvia GraphDB. Così i dati riflettono sempre il contenuto
# attuale della cartella data/ del repository.
set -e

GRAPHDB_HOME=/opt/graphdb/home
CONFIG=/opt/graphdb/import/desmos-repo-config.ttl

FILES=$(find /data -type f \( -name '*.ttl' -o -name '*.owl' -o -name '*.rdf' -o -name '*.nt' -o -name '*.nq' -o -name '*.trig' -o -name '*.jsonld' \) | sort)
if [ -z "$FILES" ]; then
    echo "Nessun file RDF trovato in /data" >&2
    exit 1
fi

echo "Importo in 'desmos':"
echo "$FILES"

# "load" (a differenza di "preload") calcola anche l'inferenza RDFS-Plus.
# --force sovrascrive il repository se esiste già; -s si ferma su file corrotti.
# shellcheck disable=SC2086
GDB_JAVA_OPTS="$GDB_JAVA_OPTS -Dgraphdb.home=$GRAPHDB_HOME" \
    importrdf load --force --stop-on-error -c "$CONFIG" $FILES

exec /opt/graphdb/dist/bin/graphdb -Dgraphdb.home="$GRAPHDB_HOME" -Dgraphdb.distribution=docker "$@"
