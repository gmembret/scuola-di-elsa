# Scuola di Elsa

App per il telefono che si collega all'Eltern-Portal del Käthe-Kollwitz-Gymnasium (kkgymuc.eltern-portal.org) e:

- mostra le **comunicazioni nuove**, divise per categoria (Lettere ai genitori, Sondaggi, Messaggi dal coordinatore di classe, Messaggi dai professori, Bacheca) e con un argomento (gite, verifiche, eventi, pagamenti, orari…);
- **traduce** tutto in italiano o in inglese (con il testo tedesco originale sempre a un tocco);
- permette di **segnare le lettere come ricevute** ("Empfang bestätigen") direttamente sul portale;
- permette di **rispondere ai sondaggi** (Umfragen/Abfragen);
- tiene **sempre in alto il calendario dei compiti in classe** (Schulaufgaben e verifiche brevi, da Service → Schulaufgaben / Weitere Termine), con l'opzione di aggiungerli al calendario del telefono.

## Come funziona

```
Telefono (app)  ──►  Connettore sul cloud (gratis, Render)  ──►  Eltern-Portal della scuola
                     login, lettura, traduzione, azioni
```

Il connettore gira su un server gratuito, non sul telefono: per questo funziona anche quando il telefono è spento o l'app è chiusa. Le credenziali del portale restano solo sul server (variabili d'ambiente cifrate di Render), mai nel telefono né nel codice. L'app si apre con un codice (PIN) che scegli tu.

## Installazione (circa 15 minuti, tutto gratuito)

### 1. Metti il codice su GitHub
1. Crea un account gratuito su https://github.com (se non lo hai).
2. Crea un nuovo repository **privato** chiamato `scuola-di-elsa`.
3. Carica tutti i file di questa cartella (pulsante "Add file → Upload files", trascina la cartella intera).

### 2. Crea il connettore su Render
1. Crea un account gratuito su https://render.com (accedi con GitHub; non serve la carta di credito).
2. Clicca **New → Blueprint** e scegli il repository `scuola-di-elsa`. Render legge il file `render.yaml`.
3. Ti chiederà di compilare:
   | Variabile | Cosa scrivere |
   |---|---|
   | `PORTAL_USER` | l'email con cui accedi all'Eltern-Portal |
   | `PORTAL_PASSWORD` | la password dell'Eltern-Portal |
   | `APP_PIN` | un codice a tua scelta per aprire l'app (almeno 6 cifre) |
   | `DEEPL_API_KEY` | facoltativa, vedi sotto; lascia vuoto se non ce l'hai |
4. Clicca **Apply**. Dopo qualche minuto ottieni un indirizzo tipo `https://scuola-di-elsa.onrender.com`.

### 3. Installa l'app sul telefono
1. Apri quell'indirizzo sul telefono.
2. **iPhone (Safari):** tasto Condividi → "Aggiungi alla schermata Home".
   **Android (Chrome):** menu ⋮ → "Installa app" o "Aggiungi a schermata Home".
3. Apri l'icona "Scuola di Elsa" e inserisci il codice scelto. Il telefono lo ricorda per 6 mesi.

## Traduzioni

- **Senza configurare nulla** l'app usa il servizio pubblico di Google Translate.
- **Qualità migliore (consigliato):** crea una chiave gratuita "DeepL API Free" su https://www.deepl.com/pro-api (500.000 caratteri al mese gratis, molto più del necessario) e mettila in `DEEPL_API_KEY` su Render (Environment → Add). Se DeepL non risponde, l'app ripiega automaticamente su Google.

Il pulsante **IT / EN / DE** in alto cambia lingua; **DE** mostra i testi originali.

## Cosa significa "nuova"

- **Lettere ai genitori:** nuove finché la ricevuta non è confermata sul portale (lo stesso stato che vede la scuola).
- **Sondaggi:** nuovi finché sono aperti e non hai risposto.
- **Bacheca e messaggi:** il portale non tiene uno stato di lettura, quindi l'app li considera nuovi se sono degli ultimi 21 giorni e non li hai ancora aperti su quel telefono.

## Cose da sapere

- **Primo avvio lento:** il piano gratuito di Render mette il server in pausa dopo 15 minuti senza uso; la prima apertura successiva richiede circa un minuto. Poi è veloce. L'ultima copia dei dati resta comunque visibile sul telefono.
- **Ore gratuite:** Render dà 750 ore al mese gratis, sufficienti per un servizio che resta acceso tutto il mese.
- **Sondaggi:** l'app ricostruisce il modulo del portale e lo rinvia con le tue scelte. Prima dell'invio chiede conferma, perché di solito il portale non permette di cambiare risposta.
- **Allegati (PDF):** si aprono tramite il connettore. Attenzione: sul portale, aprire il PDF di una lettera vale già come conferma di ricevuta.
- **Se la scuola cambia il portale:** l'app legge le pagine HTML dell'Eltern-Portal, come fanno le librerie open source [pyelternportal](https://github.com/michull/pyelternportal) ed [elternportal-api](https://github.com/philippdormann/elternportal-api). Se il fornitore cambia struttura, una sezione può smettere di caricarsi: l'app lo segnala in alto e le altre sezioni continuano a funzionare.

## Provarla senza credenziali

```bash
pip install -r requirements.txt
PORTAL_SCHOOL=demo APP_PIN=1234 uvicorn app.server:app --port 8000
# apri http://localhost:8000 e usa il codice 1234
```

La modalità `demo` usa pagine finte con la stessa struttura del portale. I test dei parser: `python -m pytest -q`.

## Struttura

```
app/portal.py     login, lettura delle pagine, conferma ricevuta, invio sondaggi
app/translate.py  traduzione DeepL / Google con cache
app/topics.py     argomento di ogni comunicazione
app/server.py     API e accesso con PIN
app/static/       l'app per il telefono (PWA)
app/demo.py       portale finto per le prove
```
