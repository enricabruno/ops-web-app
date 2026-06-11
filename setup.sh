#!/bin/bash

# Script di setup automatico per Linked Data Interface

echo "======================================"
echo "Setup Linked Data Interface - GraphDB"
echo "======================================"
echo ""

# Verifica presenza Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 non trovato. Installare Python 3 prima di continuare."
    exit 1
fi

echo "✓ Python 3 trovato: $(python3 --version)"
echo ""

# Crea virtual environment
echo "📦 Creazione virtual environment..."
python3 -m venv venv

if [ $? -ne 0 ]; then
    echo "❌ Errore nella creazione del virtual environment"
    exit 1
fi

echo "✓ Virtual environment creato"
echo ""

# Attiva virtual environment
echo "🔌 Attivazione virtual environment..."
source venv/bin/activate

if [ $? -ne 0 ]; then
    echo "❌ Errore nell'attivazione del virtual environment"
    exit 1
fi

echo "✓ Virtual environment attivato"
echo ""

# Installa dipendenze
echo "📥 Installazione dipendenze..."
pip install --upgrade pip
pip install -r requirements.txt

if [ $? -ne 0 ]; then
    echo "❌ Errore nell'installazione delle dipendenze"
    exit 1
fi

echo "✓ Dipendenze installate con successo"
echo ""

# Verifica file .env
echo "⚙️  Configurazione..."
if [ ! -f ".env" ]; then
    echo "❌ File .env non trovato!"
    exit 1
fi

echo "✓ File .env presente"
echo ""

# Rendi eseguibile lo script di bulk load
chmod +x scripts/bulk_load.py

echo "======================================"
echo "✅ Setup completato con successo!"
echo "======================================"
echo ""
echo "Prossimi passi:"
echo ""
echo "1. Modifica il file .env con i tuoi parametri GraphDB:"
echo "   - GRAPHDB_URL (default: http://localhost:7200/repositories)"
echo "   - REPOSITORY_ID (nome del repository)"
echo ""
echo "2. Avvia l'applicazione:"
echo "   python app.py"
echo ""
echo "3. Apri il browser su:"
echo "   http://localhost:5000"
echo ""
echo "Per disattivare il virtual environment:"
echo "   deactivate"
echo ""
