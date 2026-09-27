#!/bin/sh
# Copyright (C) 2026 Giuseppe Stramandino
# Licenza: GPL-3.0 o successiva (vedi il file LICENSE).
#
# Costruisce il pacchetto .deb di Cover Studio partendo dai file di questa
# cartella. Uso:   ./build-deb.sh
# Risultato:       cover-studio_<versione>_all.deb nella cartella corrente.
#
# Serve solo "dpkg-deb", gia' presente su Zorin/Ubuntu/Debian.

set -e   # si ferma al primo errore

# Cartella in cui si trova questo script (il repository)
SRC="$(cd "$(dirname "$0")" && pwd)"
cd "$SRC"

# La versione si legge dall'app stessa (voce "help_version"), cosi' esiste
# in un solo punto: per una nuova versione basta cambiarla in cover_studio.py
# e aggiungere una voce in packaging/changelog.
VERSION=$(grep -m1 '"help_version"' cover_studio.py | sed 's/.*: *"\([^"]*\)".*/\1/')
if [ -z "$VERSION" ]; then
    echo "Errore: versione non trovata in cover_studio.py" >&2
    exit 1
fi

BUILD="$SRC/build/cover-studio"
OUT="$SRC/cover-studio_${VERSION}_all.deb"

echo "Costruisco Cover Studio $VERSION ..."

# Parto da una cartella di lavoro pulita
rm -rf "$SRC/build"
mkdir -p "$BUILD/DEBIAN" \
         "$BUILD/usr/lib/cover-studio" \
         "$BUILD/usr/bin" \
         "$BUILD/usr/share/applications" \
         "$BUILD/usr/share/doc/cover-studio" \
         "$BUILD/usr/share/man/man1" \
         "$BUILD/usr/share/icons/hicolor/scalable/apps"

# Programma
cp cover_studio.py cover_render.py formats.py "$BUILD/usr/lib/cover-studio/"

# Comando di avvio "cover-studio"
cat > "$BUILD/usr/bin/cover-studio" <<'EOF'
#!/bin/sh
# Avvia Cover Studio
exec python3 /usr/lib/cover-studio/cover_studio.py "$@"
EOF

# Voce nel menu applicazioni
cp packaging/cover-studio.desktop "$BUILD/usr/share/applications/"

# Icone: vettoriale + PNG alle misure standard
cp icons/cover-studio.svg "$BUILD/usr/share/icons/hicolor/scalable/apps/cover-studio.svg"
for s in 16 24 32 48 64 128 256; do
    mkdir -p "$BUILD/usr/share/icons/hicolor/${s}x${s}/apps"
    cp "icons/cover-studio-$s.png" \
       "$BUILD/usr/share/icons/hicolor/${s}x${s}/apps/cover-studio.png"
done

# Documentazione: licenza (formato Debian), registro modifiche, manuale
cp packaging/copyright "$BUILD/usr/share/doc/cover-studio/copyright"
gzip -9n -c packaging/changelog > "$BUILD/usr/share/doc/cover-studio/changelog.gz"
sed "s/@VERSION@/$VERSION/" packaging/cover-studio.1 | gzip -9n \
    > "$BUILD/usr/share/man/man1/cover-studio.1.gz"

# Script eseguiti dopo installazione e rimozione (icone e menu)
cp packaging/postinst packaging/postrm "$BUILD/DEBIAN/"

# Permessi: file leggibili da tutti, eseguibili solo dove serve
find "$BUILD" -type d -exec chmod 755 {} \;
find "$BUILD/usr" -type f -exec chmod 644 {} \;
chmod 755 "$BUILD/usr/bin/cover-studio" "$BUILD/DEBIAN/postinst" "$BUILD/DEBIAN/postrm"

# Descrizione del pacchetto, con versione e spazio occupato
SIZE=$(du -sk "$BUILD/usr" | cut -f1)
sed -e "s/@VERSION@/$VERSION/" -e "s/@SIZE@/$SIZE/" packaging/control.in \
    > "$BUILD/DEBIAN/control"
chmod 644 "$BUILD/DEBIAN/control"

# Costruzione del pacchetto (i file risultano di proprieta' di root)
dpkg-deb --build --root-owner-group "$BUILD" "$OUT"

# Pulizia della cartella di lavoro
rm -rf "$SRC/build"

echo "Fatto: $OUT"
