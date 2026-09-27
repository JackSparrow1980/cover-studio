# Cover Studio

**English** · [Italiano](#italiano)

Cover Studio is a Linux desktop app for printing CD/DVD covers, disc labels and adhesive label sheets, at their real size and ready to cut.

It was born from a practical need: on Linux there was no tool that did exactly this job.

## Features

- **Covers** made of sections (for example back, spine, front), with cut lines and fold lines.
- Images are **fitted automatically**: always shown whole and centered, never cropped.
- **Format editor**: create and edit your own cover, disc and label formats, in millimeters or pixels.
- **Disc labels** with a one-time **centering calibration** for direct printing on discs.
- **Adhesive label sheets** with one or two labels, adjustable position and a mirror lock.
- **Batch print**: print several covers one after another.
- Tooltips on every control and a built-in Help (the **?** button).
- Interface in **Italian and English**; new languages can be added without programming.

## Installation

Cover Studio runs on Debian-based distributions (Zorin OS, Ubuntu, Linux Mint, Debian…).

1. Download `cover-studio_1.0_all.deb` from the [Releases page](https://github.com/JackSparrow1980/cover-studio/releases).
2. Double-click the file and choose **Install**, or install it from a terminal:

   ```
   sudo apt install ./cover-studio_1.0_all.deb
   ```

The app appears in the application menu under **Graphics** and can also be started with the `cover-studio` command. Any missing dependencies (Python 3, GTK 3) are installed automatically.

To uninstall:

```
sudo apt remove cover-studio
```

Your settings, calibration and custom formats are kept in `~/.config/cover-studio/`, so they are still there if you reinstall.

## Printers

It works with any printer recognized by the system. It has been tested with an **Epson ET-8500**, including direct printing on discs. Printing on discs requires a printer that supports it.

## Translations

On first start the app creates `~/.config/cover-studio/lang/` with two template files, `it.json` and `en.json`. To add a language, copy `en.json`, rename it with the language code (for example `fr.json`), change `_lang_name` and translate the texts on the right. Restart the app and pick the new language in **Options → Language**. The built-in Help explains this step by step.

Translations are welcome: you can send them by opening an issue.

## Building the package

From this folder:

```
./build-deb.sh
```

It creates `cover-studio_<version>_all.deb` using only `dpkg-deb`, which is already installed on Debian-based systems. To run the app without installing it: `python3 cover_studio.py`.

## License

Cover Studio is free software, released under the **GNU General Public License v3.0 or later**. See [LICENSE](LICENSE).

## Support

Cover Studio is free and open source. If you find it useful and feel like it, you can [buy me a coffee on PayPal](https://paypal.me/GiuseppeStramandino).

---

## Italiano

Cover Studio è un'applicazione desktop per Linux che stampa copertine per CD/DVD, etichette per dischi e fogli di etichette adesive, alle dimensioni reali e pronte da ritagliare.

È nata da un'esigenza concreta: su Linux non c'era uno strumento che facesse esattamente questo lavoro.

## Funzioni

- **Cover** divise in sezioni (per esempio retro, dorso, fronte), con linee di taglio e di piega.
- Le immagini vengono **adattate automaticamente**: entrano sempre intere e centrate, senza tagli.
- **Editor dei formati**: crei e modifichi i tuoi formati di cover, dischi ed etichette, in millimetri o pixel.
- **Etichette per dischi** con una **taratura della centratura** da fare una sola volta, per la stampa diretta su disco.
- **Fogli di etichette adesive** con una o due etichette, posizione regolabile e blocco speculare.
- **Stampa in serie**: più cover una dopo l'altra.
- Suggerimenti (tooltip) su ogni controllo e una Guida integrata (il pulsante **?**).
- Interfaccia in **italiano e inglese**; altre lingue si aggiungono senza programmare.

## Installazione

Cover Studio funziona sulle distribuzioni basate su Debian (Zorin OS, Ubuntu, Linux Mint, Debian…).

1. Scarica `cover-studio_1.0_all.deb` dalla [pagina Releases](https://github.com/JackSparrow1980/cover-studio/releases).
2. Fai doppio clic sul file e scegli **Installa**, oppure installalo da terminale:

   ```
   sudo apt install ./cover-studio_1.0_all.deb
   ```

L'app compare nel menu applicazioni sotto **Grafica** e si può avviare anche con il comando `cover-studio`. Le dipendenze mancanti (Python 3, GTK 3) vengono installate automaticamente.

Per disinstallarla:

```
sudo apt remove cover-studio
```

Impostazioni, taratura e formati personali restano in `~/.config/cover-studio/`, quindi li ritrovi se reinstalli.

## Stampanti

Funziona con qualunque stampante riconosciuta dal sistema. È stato provato con una **Epson ET-8500**, anche per la stampa diretta su disco. La stampa su disco richiede una stampante che la supporti.

## Traduzioni

Al primo avvio l'app crea `~/.config/cover-studio/lang/` con due file modello, `it.json` e `en.json`. Per aggiungere una lingua copia `en.json`, rinominalo con il codice della lingua (per esempio `fr.json`), cambia `_lang_name` e traduci i testi a destra. Riavvia l'app e scegli la nuova lingua in **Opzioni → Lingua**. La Guida integrata spiega tutto passo passo.

Le traduzioni sono benvenute: puoi inviarle aprendo una segnalazione (issue).

## Costruire il pacchetto

Da questa cartella:

```
./build-deb.sh
```

Crea `cover-studio_<versione>_all.deb` usando solo `dpkg-deb`, già presente sui sistemi basati su Debian. Per avviare l'app senza installarla: `python3 cover_studio.py`.

## Licenza

Cover Studio è software libero, distribuito con licenza **GNU General Public License v3.0 o successiva**. Vedi [LICENSE](LICENSE).

## Sostegno

Cover Studio è gratuito e open source. Se ti è utile e ti va, puoi [offrirmi un caffè su PayPal](https://paypal.me/GiuseppeStramandino).
